"""Slide model rows -> spec -> scene. Handles new composed slides and converts older saved slides (bullets,
cards, kpis, process_steps...) into blocks so every deck renders through the same engine."""
import re

from .blocks import normalize_blocks
from .solver import build_scene

SECTION_LAYOUTS = {"section_header", "section_divider", "section_divider_monument"}


def legacy_blocks(content: dict) -> list[dict]:
    blocks = []
    kpis = [k for k in (content.get("kpis") or []) if isinstance(k, dict)]
    if len(kpis) >= 2:
        blocks.append({"type": "stat_row", "items": [{"value": k.get("value"), "label": k.get("label"), "note": k.get("description") or k.get("delta")}
                                                    for k in kpis]})
    steps = content.get("process_steps") or []
    if len(steps) >= 2:
        blocks.append({"type": "steps", "items": [{"title": s.get("title"), "body": s.get("description")} for s in steps if isinstance(s, dict)]})
    cards = content.get("cards") or []
    if len(cards) >= 2:
        blocks.append({"type": "cards", "items": [{"title": c.get("title"), "body": c.get("body"), "tag": c.get("badge")} for c in cards if isinstance(c, dict)]})
    tbl = content.get("table")
    if isinstance(tbl, dict) and tbl.get("headers") and tbl.get("rows"):
        blocks.append({"type": "comparison_table", "headers": tbl["headers"], "rows": tbl["rows"]})
    ch = content.get("chart")
    if isinstance(ch, dict) and ch.get("labels") and ch.get("values"):
        blocks.append({"type": "chart", "kind": ch.get("type", "bar"), "labels": ch["labels"], "series": [{"name": "", "values": ch["values"]}],
                       "title": ch.get("title", "")})
    bl = [b["text"] if isinstance(b, dict) else str(b) for b in (content.get("bullets") or [])]
    if bl and not blocks:
        blocks.append({"type": "bullets", "items": bl})
    elif bl and len(blocks) == 1 and blocks[0]["type"] in ("chart",):
        blocks.append({"type": "bullets", "items": bl[:3]})
    return blocks


def slide_spec(slide, idx: int, total: int) -> dict:
    content = slide.content or {}
    spec = content.get("spec")
    img = content.get("image") if isinstance(content.get("image"), dict) and content["image"].get("url") else None
    if isinstance(spec, dict) and spec.get("blocks") is not None or (isinstance(spec, dict) and spec.get("kind") in ("title", "section")):
        out = dict(spec)
    else:
        layout = content.get("layout", "")
        kind = "title" if idx == 0 else ("section" if layout in SECTION_LAYOUTS else "content")
        out = {"kind": kind, "blocks": legacy_blocks(content), "tagline": content.get("tagline", "")}
    out["title"] = slide.title or out.get("title") or ""
    out["image"] = img if out.get("visual_plan", "photo" if img else "none") == "photo" or img else None
    out["notes"] = slide.speaker_notes or ""
    # `purpose` is an internal planning note: it is never rendered.
    out.pop("purpose", None)
    return out


def build_scenes(presentation) -> list[dict]:
    theme = (presentation.settings or {}).get("theme", "swiss_minimal")
    slides = sorted(presentation.slides, key=lambda s: s.position)
    return [build_scene(slide_spec(s, i, len(slides)), theme, i, len(slides), presentation.title or "") for i, s in enumerate(slides)]


def plain_bullets(spec: dict) -> list[str]:
    """Flat text lines of a spec's blocks, for the audit, Google Slides publishing and search."""
    out = []
    for b in normalize_blocks(spec.get("blocks")):
        t = b["type"]
        if t in ("cards", "steps"):
            out += [f"{i['title']}: {i['body']}" if i.get("body") else i["title"] for i in b["items"]]
        elif t == "bullets":
            out += b["items"]
        elif t == "stat_row":
            out += [f"{i['value']} {i['label']}" for i in b["items"]]
        elif t == "timeline":
            out += [f"{i['when']} {i['title']}".strip() for i in b["items"]]
        elif t == "diagram":
            out += [n["label"] + (f": {n['detail']}" if n["detail"] else "") for n in b["nodes"]]
        elif t == "comparison_table":
            out += [" | ".join(r) for r in b["rows"]]
        elif t in ("callout", "quote", "headline"):
            out.append(b["text"])
        elif t == "chart":
            out.append((b["title"] or "Chart") + ": " + ", ".join(f"{l} {v:g}" for l, v in zip(b["labels"], b["series"][0]["values"])))
        elif t == "matrix_2x2":
            out += [q["title"] for q in b["quadrants"]]
    return [re.sub(r"\s+", " ", x).strip() for x in out if x]
