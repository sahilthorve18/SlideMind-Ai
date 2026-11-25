"""Text extraction with page numbers and section headings.

Each extractor yields Segment(text, page, heading). `page` is the PDF page or PPTX
slide number; DOCX has no fixed pages so it is None.
"""
import io
import statistics
import zipfile
from dataclasses import dataclass

ALLOWED_TYPES = {"pdf", "docx", "pptx", "txt"}
MAX_ZIP_UNCOMPRESSED_BYTES = 50 * 1024 * 1024  # 50 MB decompressed ceiling against ZIP bombs
MAX_ZIP_ENTRIES = 2000
MAX_PDF_PAGES = 200
MAX_EXTRACTED_CHARS = 500_000


class ExtractionError(Exception):
    pass


@dataclass
class Segment:
    text: str
    page: int | None
    heading: str | None


def detect_type(filename: str, data: bytes) -> str:
    """Validate extension AND content signature; never trust the extension alone."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_TYPES:
        raise ExtractionError("Unsupported file type. Upload a PDF, DOCX, PPTX or TXT file.")
    if not data:
        raise ExtractionError("The file is empty.")
    if ext == "pdf" and not data.startswith(b"%PDF"):
        raise ExtractionError("This file is not a valid PDF.")
    if ext in ("docx", "pptx"):
        if not data.startswith(b"PK"):
            raise ExtractionError(f"This file is not a valid {ext.upper()}.")
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                infos = zf.infolist()
                if len(infos) > MAX_ZIP_ENTRIES:
                    raise ExtractionError("Archive contains too many entries.")
                total_uncompressed = 0
                for zi in infos:
                    if zi.flag_bits & 0x1:
                        raise ExtractionError("Encrypted archives are not supported.")
                    total_uncompressed += zi.file_size
                    if total_uncompressed > MAX_ZIP_UNCOMPRESSED_BYTES:
                        raise ExtractionError("Archive exceeds safe uncompressed size limit.")
                names = [zi.filename for zi in infos]
        except zipfile.BadZipFile:
            raise ExtractionError(f"This file is not a valid {ext.upper()}.")
        marker = "word/document.xml" if ext == "docx" else "ppt/presentation.xml"
        if marker not in names:
            raise ExtractionError(f"This file is not a valid {ext.upper()}.")
    if ext == "txt":
        if b"\x00" in data:
            raise ExtractionError("This file does not look like plain text.")
        sample = data[:8192]
        non_text = sum(1 for b in sample if b < 9 or (13 < b < 32 and b != 27))
        if sample and (non_text / len(sample)) > 0.15:
            raise ExtractionError("This file does not look like plain text.")
    return ext


def _pdf(data: bytes):
    import pymupdf

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception:
        raise ExtractionError("Could not read this PDF.")
    if doc.needs_pass:
        raise ExtractionError("Password-protected PDFs are not supported.")
    if len(doc) > MAX_PDF_PAGES:
        raise ExtractionError(f"PDF has {len(doc)} pages; maximum supported is {MAX_PDF_PAGES} pages.")
    segments, heading, total_chars = [], None, 0
    for pno, page in enumerate(doc, start=1):
        sizes = []
        lines = []
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                spans = [s for s in line["spans"] if s["text"].strip()]
                if not spans:
                    continue
                text = "".join(s["text"] for s in spans).strip()
                size = max(s["size"] for s in spans)
                sizes.append(size)
                lines.append((text, size))
                total_chars += len(text)
                if total_chars > MAX_EXTRACTED_CHARS:
                    raise ExtractionError("PDF contains too much extracted text to process safely.")
        body = statistics.median(sizes) if sizes else 0
        buf = []
        for text, size in lines:
            if body and size >= body * 1.25 and len(text) <= 120:
                if buf:
                    segments.append(Segment("\n".join(buf), pno, heading))
                    buf = []
                heading = text
            else:
                buf.append(text)
        if buf:
            segments.append(Segment("\n".join(buf), pno, heading))
    return segments, len(doc)


def _docx(data: bytes):
    import docx

    try:
        d = docx.Document(io.BytesIO(data))
    except Exception:
        raise ExtractionError("Could not read this DOCX.")
    segments, heading = [], None
    for p in d.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        if (p.style.name or "").lower().startswith(("heading", "title")):
            heading = text
            continue
        segments.append(Segment(text, None, heading))
    for t in d.tables:
        rows = [" | ".join(c.text.strip() for c in r.cells) for r in t.rows]
        if rows:
            segments.append(Segment("\n".join(rows), None, heading))
    return segments, None


def _pptx(data: bytes):
    from pptx import Presentation

    try:
        prs = Presentation(io.BytesIO(data))
    except Exception:
        raise ExtractionError("Could not read this PPTX.")
    segments = []
    for n, slide in enumerate(prs.slides, start=1):
        title = slide.shapes.title.text.strip() if slide.shapes.title is not None and slide.shapes.title.has_text_frame else None
        parts = []
        for shape in slide.shapes:
            if shape.has_text_frame and shape != slide.shapes.title:
                t = shape.text_frame.text.strip()
                if t:
                    parts.append(t)
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                parts.append("Notes: " + notes)
        if parts or title:
            segments.append(Segment("\n".join(parts) or title, n, title))
    return segments, len(prs.slides)


def _txt(data: bytes):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("latin-1")
    return [Segment(text, None, None)], None


def extract(filename: str, data: bytes):
    """Returns (file_type, segments, page_count)."""
    ftype = detect_type(filename, data)
    fn = {"pdf": _pdf, "docx": _docx, "pptx": _pptx, "txt": _txt}[ftype]
    segments, pages = fn(data)
    segments = [s for s in segments if s.text.strip()]
    if not segments:
        raise ExtractionError("No readable text found (scanned or image-only files are not supported yet).")
    return ftype, segments, pages
