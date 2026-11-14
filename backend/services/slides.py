"""Google Slides + Drive wrapper (official APIs, batchUpdate).

Request building is done by pure functions so it can be unit-tested without network access.
All API calls go through `_execute`, which retries transient errors and converts failures
into SlidesError / GoogleAuthExpired with safe, user-presentable messages.
"""
import logging
import time
import uuid
from dataclasses import dataclass

from services.google_auth import GoogleAuthExpired

log = logging.getLogger(__name__)

PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
EXPORT_MIMES = {"pptx": PPTX_MIME, "pdf": "application/pdf"}

# name -> (background rgb, title rgb, body rgb, font)
THEME_STYLES = {
    # Legacy themes (preserved with exact RGB values for backward compatibility)
    "modern_light": ((1.0, 1.0, 1.0), (0.10, 0.11, 0.20), (0.22, 0.24, 0.30), "Roboto"),
    "modern_dark": ((0.07, 0.08, 0.12), (0.97, 0.97, 1.0), (0.82, 0.84, 0.90), "Roboto"),
    "dark_blue": ((0.05, 0.12, 0.28), (1.0, 1.0, 1.0), (0.84, 0.90, 1.0), "Arial"),
    "minimal": ((0.98, 0.98, 0.97), (0.05, 0.05, 0.05), (0.25, 0.25, 0.25), "Georgia"),
    "corporate": ((1.0, 1.0, 1.0), (0.05, 0.20, 0.42), (0.20, 0.22, 0.26), "Arial"),
    "vibrant": ((0.36, 0.30, 0.90), (1.0, 1.0, 1.0), (0.93, 0.92, 1.0), "Montserrat"),
    # Next-Gen 2026 Premium Design Systems
    "swiss_minimal": ((0.98, 0.98, 0.98), (0.06, 0.06, 0.07), (0.25, 0.25, 0.28), "Inter"),
    "apple_keynote": ((0.05, 0.05, 0.07), (0.98, 0.98, 1.0), (0.75, 0.77, 0.82), "Inter"),
    "startup_pitch": ((0.97, 0.98, 1.0), (0.08, 0.08, 0.18), (0.28, 0.30, 0.40), "Inter"),
    "dark_technology": ((0.06, 0.08, 0.12), (0.95, 0.97, 1.0), (0.68, 0.73, 0.82), "Inter"),
    "editorial_magazine": ((0.97, 0.96, 0.94), (0.10, 0.08, 0.08), (0.28, 0.25, 0.24), "Georgia"),
    "corporate_premium": ((1.0, 1.0, 1.0), (0.06, 0.14, 0.28), (0.22, 0.27, 0.35), "Arial"),
    "education_modern": ((0.98, 0.99, 0.98), (0.08, 0.18, 0.14), (0.22, 0.31, 0.27), "Inter"),
    "data_storytelling": ((0.96, 0.97, 0.98), (0.07, 0.10, 0.16), (0.24, 0.29, 0.38), "Inter"),
    "creative_agency": ((0.98, 0.96, 0.99), (0.14, 0.06, 0.18), (0.33, 0.23, 0.38), "Inter"),
    "futuristic_ai": ((0.04, 0.04, 0.08), (0.97, 0.97, 1.0), (0.72, 0.74, 0.84), "Inter"),
    # 9 Studio Design Systems (2026 Modern Aesthetic)
    "linear_dark": ((0.035, 0.035, 0.043), (0.96, 0.96, 0.96), (0.63, 0.63, 0.67), "Inter"),
    "editorial_monocle": ((0.98, 0.97, 0.95), (0.11, 0.10, 0.09), (0.34, 0.33, 0.31), "Georgia"),
    "brutalist_raw": ((1.0, 1.0, 1.0), (0.0, 0.0, 0.0), (0.15, 0.15, 0.16), "Arial"),
    "stripe_scale": ((0.97, 0.98, 0.99), (0.06, 0.09, 0.16), (0.20, 0.25, 0.33), "Inter"),
    "cyber_terminal": ((0.02, 0.04, 0.03), (0.94, 0.99, 0.96), (0.53, 0.94, 0.67), "Consolas"),
    "swiss_bauhaus": ((0.96, 0.95, 0.94), (0.04, 0.04, 0.04), (0.15, 0.15, 0.16), "Inter"),
    "pitch_venture": ((0.04, 0.04, 0.05), (0.98, 0.98, 0.98), (0.61, 0.64, 0.69), "Inter"),
    "luxury_maison": ((0.05, 0.05, 0.05), (0.96, 0.96, 0.97), (0.83, 0.83, 0.85), "Georgia"),
    "nordic_frost": ((0.95, 0.96, 0.98), (0.04, 0.10, 0.18), (0.28, 0.33, 0.41), "Inter"),
    "tokyo_neon": ((0.03, 0.03, 0.07), (0.97, 0.98, 0.99), (0.80, 0.84, 0.88), "Inter"),
    "california_warmth": ((0.98, 0.97, 0.95), (0.15, 0.11, 0.08), (0.36, 0.30, 0.25), "Inter"),
    "monochrome_monument": ((0.02, 0.02, 0.02), (0.98, 0.98, 0.98), (0.64, 0.64, 0.64), "Inter"),
    # Catalog themes
    "brutalist": ((0.96, 0.96, 0.94), (0.0, 0.0, 0.0), (0.10, 0.10, 0.10), "Arial"),
    "cybersecurity": ((0.03, 0.05, 0.08), (0.0, 0.94, 1.0), (0.60, 0.75, 0.85), "Consolas"),
    "luxury_brand": ((0.05, 0.04, 0.04), (0.96, 0.96, 0.96), (0.75, 0.73, 0.70), "Georgia"),
    "japanese_minimalism": ((0.97, 0.96, 0.95), (0.14, 0.14, 0.14), (0.35, 0.35, 0.35), "Georgia"),
    "financial_analyst": ((0.97, 0.98, 0.99), (0.06, 0.09, 0.16), (0.28, 0.32, 0.40), "Inter"),
    "academic_research": ((1.0, 1.0, 1.0), (0.12, 0.14, 0.18), (0.28, 0.31, 0.38), "Georgia"),
    "architecture_portfolio": ((0.07, 0.07, 0.08), (0.95, 0.95, 0.96), (0.60, 0.60, 0.64), "Inter"),
    "documentary_storytelling": ((0.05, 0.05, 0.06), (0.95, 0.96, 0.98), (0.72, 0.74, 0.80), "Georgia"),
}


class SlidesError(Exception):
    pass


@dataclass
class Services:
    slides: object  # googleapiclient Resource for slides v1
    drive: object   # googleapiclient Resource for drive v3


def build_services(credentials) -> Services:
    from googleapiclient.discovery import build

    return Services(slides=build("slides", "v1", credentials=credentials, cache_discovery=False),
                    drive=build("drive", "v3", credentials=credentials, cache_discovery=False))


def _execute(request, attempts: int = 3):
    from google.auth.exceptions import RefreshError
    from googleapiclient.errors import HttpError

    for i in range(attempts):
        try:
            return request.execute()
        except RefreshError as e:
            raise GoogleAuthExpired("Google access was revoked or expired.") from e
        except HttpError as e:
            status = getattr(e.resp, "status", 0)
            if status in (429, 500, 502, 503, 504) and i < attempts - 1:
                time.sleep(2 ** i)
                continue
            log.warning("Google API HttpError %s", status)
            if status == 401:
                raise GoogleAuthExpired("Google access was revoked or expired.") from e
            if status == 403:
                raise SlidesError("Google refused the request (403). Check that the Slides and Drive APIs are enabled "
                                  "for the project and that access was granted.") from e
            if status == 429:
                raise SlidesError("Google's rate limit was hit. Try again in a minute.") from e
            raise SlidesError(f"Google returned an error ({status}).") from e


# ---------------------------------------------------------------------------
# Pure request builders
# ---------------------------------------------------------------------------

def _rgb(t):
    return {"rgbColor": {"red": t[0], "green": t[1], "blue": t[2]}}


def object_id(prefix: str = "sm") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"  # 5-50 chars, starts with a letter


def theme_requests(slide_oid: str, text_targets: list[tuple[str, str]], theme: str) -> list[dict]:
    """Background + text colours/fonts. text_targets: [(object_id, 'title'|'body')]."""
    if theme in THEME_STYLES:
        bg, title_c, body_c, font = THEME_STYLES[theme]
    else:
        try:
            from services.design_systems import get_design_system
            ds = get_design_system(theme)
            bg, title_c, body_c, font = ds.background_rgb, ds.title_rgb, ds.body_rgb, ds.font_title.split(",")[0].strip()
        except Exception:
            bg, title_c, body_c, font = THEME_STYLES.get(theme, THEME_STYLES["modern_light"])
    reqs = [{"updatePageProperties": {
        "objectId": slide_oid,
        "pageProperties": {"pageBackgroundFill": {"solidFill": {"color": _rgb(bg)}}},
        "fields": "pageBackgroundFill.solidFill.color"}}]
    for oid, kind in text_targets:
        style = {"foregroundColor": {"opaqueColor": _rgb(title_c if kind == "title" else body_c)}, "fontFamily": font}
        fields = "foregroundColor,fontFamily"
        if kind == "title":
            style["bold"] = True
            fields += ",bold"
        reqs.append({"updateTextStyle": {"objectId": oid, "style": style, "textRange": {"type": "ALL"}, "fields": fields}})
    return reqs


def slide_requests(index: int, slide: dict, theme: str) -> tuple[list[dict], dict, list[dict]]:
    """Requests to create one slide with its text.
    slide: {title, bullets: [str], layout}. Returns (requests, ids, not_rendered)."""
    sid, tid, bid = object_id("sl"), object_id("ti"), object_id("bo")
    title, bullets = (slide.get("title") or "").strip(), [b for b in slide.get("bullets", []) if b.strip()]
    layout = slide.get("layout") or "title_bullets"
    not_rendered = []

    if index == 0:
        pre, maps = "TITLE_SLIDE", [("CENTERED_TITLE", tid)] + ([("SUBTITLE", bid)] if bullets else [])
        body_text = "\n".join(bullets[:2])
    elif bullets:
        pre, maps, body_text = "TITLE_AND_BODY", [("TITLE", tid), ("BODY", bid)], "\n".join(bullets)
    else:
        pre, maps, body_text = "TITLE_ONLY", [("TITLE", tid)], ""
    if layout == "chart":
        not_rendered.append({"what": "chart", "reason": "chart rendering is not implemented yet"})
    elif layout == "diagram":
        not_rendered.append({"what": "diagram", "reason": "diagram rendering is not implemented yet"})

    reqs = [{"createSlide": {
        "objectId": sid, "insertionIndex": index,
        "slideLayoutReference": {"predefinedLayout": pre},
        "placeholderIdMappings": [{"layoutPlaceholder": {"type": t, "index": 0}, "objectId": o} for t, o in maps]}}]
    targets = [(tid, "title")]
    if title:
        reqs.append({"insertText": {"objectId": tid, "text": title[:400], "insertionIndex": 0}})
    if body_text and any(o == bid for _, o in maps):
        reqs.append({"insertText": {"objectId": bid, "text": body_text, "insertionIndex": 0}})
        targets.append((bid, "body"))
    reqs += theme_requests(sid, targets, theme)

    # Insert image if present in slide specification
    image_meta = slide.get("image") or (slide.get("content") or {}).get("image")
    if image_meta and isinstance(image_meta, dict) and image_meta.get("url"):
        img_url = image_meta["url"]
        EMU = 914400
        # Prevent image from covering text: constrain body/title placeholder to left half
        if index == 0:
            reqs.append({
                "updatePageElementTransform": {
                    "objectId": tid,
                    "transform": {"scaleX": 0.52, "scaleY": 1.0, "translateX": int(0.8 * EMU), "translateY": int(1.6 * EMU), "unit": "EMU"},
                    "applyMode": "ABSOLUTE"
                }
            })
            if any(o == bid for _, o in maps):
                reqs.append({
                    "updatePageElementTransform": {
                        "objectId": bid,
                        "transform": {"scaleX": 0.52, "scaleY": 1.0, "translateX": int(0.8 * EMU), "translateY": int(3.8 * EMU), "unit": "EMU"},
                        "applyMode": "ABSOLUTE"
                    }
                })
        elif any(o == bid for _, o in maps):
            reqs.append({
                "updatePageElementTransform": {
                    "objectId": bid,
                    "transform": {"scaleX": 0.48, "scaleY": 1.0, "translateX": int(0.8 * EMU), "translateY": int(1.5 * EMU), "unit": "EMU"},
                    "applyMode": "ABSOLUTE"
                }
            })

        if layout in ("split_screen", "image_gallery"):
            reqs += image_requests(sid, img_url, left_inch=6.8, top_inch=1.5, width_inch=5.5, height_inch=4.5)
        elif layout == "full_bleed_hero" or index == 0:
            reqs += image_requests(sid, img_url, left_inch=7.2, top_inch=1.2, width_inch=5.2, height_inch=4.8)
        else:
            reqs += image_requests(sid, img_url, left_inch=7.0, top_inch=1.5, width_inch=5.2, height_inch=4.2)

    # Insert native Google Slides table if table data is present
    c_data = slide.get("content") or {}
    t_rows = slide.get("table_rows") or c_data.get("table_rows")
    t_headers = slide.get("table_headers") or c_data.get("table_headers")
    if t_rows and isinstance(t_rows, list) and len(t_rows) > 0:
        all_rows = ([t_headers] if t_headers else []) + t_rows
        try:
            reqs += table_requests(sid, all_rows)
        except Exception as e:
            log.warning("Google Slides table generation fallback: %s", e)

    return reqs, {"slide": sid, "title": tid, "body": bid}, [{"slide": index + 1, **n} for n in not_rendered]


def notes_text(slide: dict) -> str:
    parts = []
    if (slide.get("notes") or "").strip():
        parts.append(slide["notes"].strip())
    if slide.get("sources"):
        lines = []
        for s in slide["sources"]:
            where = s.get("filename") or s.get("url") or "source"
            if s.get("page_number"):
                where += f", p.{s['page_number']}"
            if s.get("url") and s.get("filename") != s.get("url"):
                where += f" ({s['url']})"
            lines.append("- " + where)
        parts.append("Sources:\n" + "\n".join(lines))
    return "\n\n".join(parts)


def table_requests(slide_oid: str, rows: list[list[str]], table_oid: str | None = None) -> list[dict]:
    """A native Slides table with text in each cell (for comparison slides)."""
    if not rows or not rows[0]:
        raise SlidesError("A table needs at least one row and column.")
    n_cols = len(rows[0])
    if any(len(r) != n_cols for r in rows):
        raise SlidesError("All table rows must have the same number of columns.")
    tid = table_oid or object_id("tb")
    reqs = [{"createTable": {"objectId": tid, "elementProperties": {"pageObjectId": slide_oid},
                             "rows": len(rows), "columns": n_cols}}]
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            if text.strip():
                reqs.append({"insertText": {"objectId": tid, "cellLocation": {"rowIndex": r, "columnIndex": c},
                                            "text": text[:200], "insertionIndex": 0}})
    return reqs


def image_requests(slide_oid: str, image_url: str, left_inch: float = 6.8, top_inch: float = 1.5,
                   width_inch: float = 5.5, height_inch: float = 4.2, image_oid: str | None = None) -> list[dict]:
    """Generates an createImage request for Google Slides API."""
    iid = image_oid or object_id("im")
    EMU = 914400  # 1 inch = 914400 EMUs
    return [{
        "createImage": {
            "objectId": iid,
            "url": image_url,
            "elementProperties": {
                "pageObjectId": slide_oid,
                "size": {"width": {"magnitude": int(width_inch * EMU), "unit": "EMU"},
                         "height": {"magnitude": int(height_inch * EMU), "unit": "EMU"}},
                "transform": {"scaleX": 1, "scaleY": 1,
                              "translateX": int(left_inch * EMU), "translateY": int(top_inch * EMU),
                              "unit": "EMU"}
            }
        }
    }]


def shape_card_requests(slide_oid: str, left_inch: float, top_inch: float, width_inch: float, height_inch: float,
                        bg_rgb: tuple, border_rgb: tuple, shape_oid: str | None = None) -> tuple[list[dict], str]:
    """Generates a rounded rectangle card container for Google Slides."""
    sid = shape_oid or object_id("sh")
    EMU = 914400
    reqs = [
        {"createShape": {
            "objectId": sid,
            "shapeType": "ROUNDED_RECTANGLE",
            "elementProperties": {
                "pageObjectId": slide_oid,
                "size": {"width": {"magnitude": int(width_inch * EMU), "unit": "EMU"},
                         "height": {"magnitude": int(height_inch * EMU), "unit": "EMU"}},
                "transform": {"scaleX": 1, "scaleY": 1,
                              "translateX": int(left_inch * EMU), "translateY": int(top_inch * EMU),
                              "unit": "EMU"}
            }
        }},
        {"updateShapeProperties": {
            "objectId": sid,
            "shapeProperties": {
                "shapeBackgroundFill": {"solidFill": {"color": _rgb(bg_rgb)}},
                "outline": {"outlineFill": {"solidFill": {"color": _rgb(border_rgb)}},
                            "weight": {"magnitude": 1, "unit": "PT"}}
            },
            "fields": "shapeBackgroundFill.solidFill.color,outline.outlineFill.solidFill.color,outline.weight"
        }}
    ]
    return reqs, sid


# ---------------------------------------------------------------------------
# API operations
# ---------------------------------------------------------------------------

def presentation_url(pid: str) -> str:
    return f"https://docs.google.com/presentation/d/{pid}/edit"


def publish_draft(svc: Services, draft: dict) -> dict:
    """Create a Google Slides file from a draft.
    draft: {title, theme, slides: [{title, bullets, layout, notes, sources}]}
    Returns {presentation_id, url, slide_object_ids, not_rendered}."""
    created = _execute(svc.slides.presentations().create(body={"title": (draft["title"] or "Untitled")[:200]}))
    pid = created["presentationId"]
    default_ids = [s["objectId"] for s in created.get("slides", [])]

    reqs, ids, not_rendered = [], [], []
    for i, slide in enumerate(draft["slides"]):
        r, oid, nr = slide_requests(i, slide, draft.get("theme", "modern_light"))
        reqs += r
        ids.append(oid)
        not_rendered += nr
    reqs += [{"deleteObject": {"objectId": d}} for d in default_ids]  # drop the blank starter slide last
    _execute(svc.slides.presentations().batchUpdate(presentationId=pid, body={"requests": reqs}))

    # Speaker notes live on a separate notes page whose object id is only known after creation.
    notes_by_slide = {ids[i]["slide"]: notes_text(s) for i, s in enumerate(draft["slides"]) if notes_text(s)}
    if notes_by_slide:
        got = _execute(svc.slides.presentations().get(
            presentationId=pid,
            fields="slides(objectId,slideProperties/notesPage/notesProperties/speakerNotesObjectId)"))
        note_reqs = []
        for s in got.get("slides", []):
            nid = (((s.get("slideProperties") or {}).get("notesPage") or {}).get("notesProperties") or {}).get("speakerNotesObjectId")
            if nid and s["objectId"] in notes_by_slide:
                note_reqs.append({"insertText": {"objectId": nid, "text": notes_by_slide[s["objectId"]], "insertionIndex": 0}})
        if note_reqs:
            _execute(svc.slides.presentations().batchUpdate(presentationId=pid, body={"requests": note_reqs}))
        notes_written = len(note_reqs)
    else:
        notes_written = 0
    return {"presentation_id": pid, "url": presentation_url(pid), "slide_object_ids": [o["slide"] for o in ids],
            "not_rendered": not_rendered, "notes_written": notes_written}


def sync_presentation(svc: Services, pid: str, draft: dict) -> dict:
    """Sync an existing Google Slides file with the updated draft.
    Inserts updated slides, deletes old slides, and rewrites speaker notes."""
    existing = _execute(svc.slides.presentations().get(presentationId=pid, fields="slides(objectId)"))
    old_ids = [s["objectId"] for s in existing.get("slides", [])]

    reqs, ids, not_rendered = [], [], []
    for i, slide in enumerate(draft["slides"]):
        r, oid, nr = slide_requests(i, slide, draft.get("theme", "modern_light"))
        reqs += r
        ids.append(oid)
        not_rendered += nr
    if old_ids:
        reqs += [{"deleteObject": {"objectId": oid}} for oid in old_ids]

    _execute(svc.slides.presentations().batchUpdate(presentationId=pid, body={"requests": reqs}))

    notes_by_slide = {ids[i]["slide"]: notes_text(s) for i, s in enumerate(draft["slides"]) if notes_text(s)}
    notes_written = 0
    if notes_by_slide:
        got = _execute(svc.slides.presentations().get(
            presentationId=pid,
            fields="slides(objectId,slideProperties/notesPage/notesProperties/speakerNotesObjectId)"))
        note_reqs = []
        for s in got.get("slides", []):
            nid = (((s.get("slideProperties") or {}).get("notesPage") or {}).get("notesProperties") or {}).get("speakerNotesObjectId")
            if nid and s["objectId"] in notes_by_slide:
                note_reqs.append({"insertText": {"objectId": nid, "text": notes_by_slide[s["objectId"]], "insertionIndex": 0}})
        if note_reqs:
            _execute(svc.slides.presentations().batchUpdate(presentationId=pid, body={"requests": note_reqs}))
        notes_written = len(note_reqs)

    return {
        "presentation_id": pid,
        "url": presentation_url(pid),
        "slide_object_ids": [o["slide"] for o in ids],
        "not_rendered": not_rendered,
        "notes_written": notes_written,
    }



def delete_slide(svc: Services, pid: str, slide_object_id: str):
    _execute(svc.slides.presentations().batchUpdate(presentationId=pid, body={"requests": [{"deleteObject": {"objectId": slide_object_id}}]}))


def add_table(svc: Services, pid: str, slide_object_id: str, rows: list[list[str]]):
    _execute(svc.slides.presentations().batchUpdate(presentationId=pid, body={"requests": table_requests(slide_object_id, rows)}))


def export_file(svc: Services, pid: str, fmt: str) -> bytes:
    if fmt not in EXPORT_MIMES:
        raise SlidesError("Export format must be pptx or pdf.")
    data = _execute(svc.drive.files().export_media(fileId=pid, mimeType=EXPORT_MIMES[fmt]))
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise SlidesError("Google returned an empty export.")
    return bytes(data)
