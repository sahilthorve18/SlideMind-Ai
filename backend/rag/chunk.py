"""Paragraph-aware chunking that keeps page and heading metadata."""
import re
from dataclasses import dataclass

from rag.extract import Segment

TARGET = 1000   # characters per chunk
OVERLAP = 150


@dataclass
class Chunk:
    text: str
    page: int | None
    heading: str | None


def _split_long(text: str, size: int):
    """Split an oversized paragraph on sentence boundaries, then hard-split."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out, cur = [], ""
    for s in sentences:
        while len(s) > size:
            if cur:
                out.append(cur)
                cur = ""
            out.append(s[:size])
            s = s[size:]
        if len(cur) + len(s) + 1 > size and cur:
            out.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        out.append(cur)
    return out


def chunk_segments(segments: list[Segment], target: int = TARGET, overlap: int = OVERLAP) -> list[Chunk]:
    chunks: list[Chunk] = []
    for seg in segments:
        paras = [p.strip() for p in re.split(r"\n{2,}|\n", seg.text) if p.strip()]
        pieces = []
        for p in paras:
            pieces.extend(_split_long(p, target) if len(p) > target else [p])
        cur = ""
        for piece in pieces:
            if cur and len(cur) + len(piece) + 1 > target:
                chunks.append(Chunk(cur, seg.page, seg.heading))
                tail = cur[-overlap:] if overlap else ""
                cur = f"{tail} {piece}".strip()
            else:
                cur = f"{cur}\n{piece}".strip() if cur else piece
        if cur:
            chunks.append(Chunk(cur, seg.page, seg.heading))
    return chunks
