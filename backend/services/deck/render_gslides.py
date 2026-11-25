"""Scene -> Google Slides API batchUpdate requests.

Translates the same 13.333" x 7.5" scene primitives used by PPTX, PDF, and the React preview
into positioned Google Slides shapes, text boxes, lines, images, and vector charts on Google's
standard 10" x 5.625" (16:9) canvas.
"""
import uuid

EMU = 914400
SCALE = 10.0 / 13.333  # 0.75: maps 13.333" x 7.5" scene exactly to 10" x 5.625" Google Slides

FONT_MAP = {
    "Calibri": "Inter",
    "Consolas": "Roboto Mono",
    "Georgia": "Georgia",
    "Inter": "Inter",
    "Arial": "Arial",
    "Roboto": "Roboto",
}
ALIGN_MAP = {"l": "START", "c": "CENTER", "r": "END"}
VALIGN_MAP = {"t": "TOP", "m": "MIDDLE", "b": "BOTTOM"}


def _oid(prefix: str = "sm") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:18]}"


def _emu(inches: float) -> int:
    return int(round(float(inches) * SCALE * EMU))


def _pos_emu(inches: float) -> int:
    return max(12700, _emu(inches))  # >= 1pt so Google Slides API never rejects 0-size geometry


def _rgb(hex_color: str) -> dict:
    h = str(hex_color or "000000").lstrip("#").strip()
    if len(h) != 6:
        h = "000000"
    return {
        "rgbColor": {
            "red": round(int(h[0:2], 16) / 255.0, 4),
            "green": round(int(h[2:4], 16) / 255.0, 4),
            "blue": round(int(h[4:6], 16) / 255.0, 4),
        }
    }


def _elem_props(slide_oid: str, x: float, y: float, w: float, h: float,
                scale_x: float = 1.0, scale_y: float = 1.0) -> dict:
    return {
        "pageObjectId": slide_oid,
        "size": {
            "width": {"magnitude": _pos_emu(abs(w)), "unit": "EMU"},
            "height": {"magnitude": _pos_emu(abs(h)), "unit": "EMU"},
        },
        "transform": {
            "scaleX": scale_x,
            "scaleY": scale_y,
            "translateX": _emu(x),
            "translateY": _emu(y),
            "unit": "EMU",
        },
    }


def _shape_reqs(slide_oid: str, shape_type: str, x: float, y: float, w: float, h: float,
                fill: str | None = None, line: str | None = None, lw: float = 1.0, alpha: float = 1.0) -> tuple[list[dict], str]:
    sid = _oid("sh")
    reqs = [{
        "createShape": {
            "objectId": sid,
            "shapeType": shape_type,
            "elementProperties": _elem_props(slide_oid, x, y, w, h),
        }
    }]
    props = {}
    if fill:
        props["shapeBackgroundFill"] = {"solidFill": {"color": _rgb(fill), "alpha": max(0.0, min(1.0, float(alpha)))}}
    else:
        props["shapeBackgroundFill"] = {"propertyState": "NOT_RENDERED"}
    if line:
        props["outline"] = {
            "outlineFill": {"solidFill": {"color": _rgb(line)}},
            "weight": {"magnitude": max(0.5, round(float(lw) * SCALE, 2)), "unit": "PT"},
        }
    else:
        props["outline"] = {"propertyState": "NOT_RENDERED"}
    reqs.append({
        "updateShapeProperties": {
            "objectId": sid,
            "shapeProperties": props,
            "fields": "shapeBackgroundFill,outline",
        }
    })
    return reqs, sid


def _line_reqs(slide_oid: str, x1: float, y1: float, x2: float, y2: float,
               color: str, lw: float = 1.5, dash: bool = False, arrow: bool = False) -> list[dict]:
    lid = _oid("ln")
    dx = float(x2) - float(x1)
    dy = float(y2) - float(y1)
    reqs = [{
        "createLine": {
            "objectId": lid,
            "lineCategory": "STRAIGHT",
            "elementProperties": _elem_props(
                slide_oid,
                x1,
                y1,
                max(abs(dx), 0.015),
                max(abs(dy), 0.015),
                scale_x=1.0 if dx >= 0 else -1.0,
                scale_y=1.0 if dy >= 0 else -1.0,
            ),
        }
    }]
    lprops = {
        "lineFill": {"solidFill": {"color": _rgb(color)}},
        "weight": {"magnitude": max(0.75, round(float(lw) * SCALE, 2)), "unit": "PT"},
    }
    fields = ["lineFill.solidFill.color", "weight"]
    if dash:
        lprops["dashStyle"] = "DASH"
        fields.append("dashStyle")
    if arrow:
        lprops["endArrow"] = "FILL_ARROW"
        fields.append("endArrow")
    reqs.append({
        "updateLineProperties": {
            "objectId": lid,
            "lineProperties": lprops,
            "fields": ",".join(fields),
        }
    })
    return reqs


def _text_reqs(slide_oid: str, x: float, y: float, w: float, h: float, text: str, size: float, color: str,
               bold: bool = False, italic: bool = False, align: str = "l", valign: str = "t",
               font: str | None = None, lh: float = 1.15) -> list[dict]:
    txt = str(text or "").rstrip()
    if not txt:
        return []
    tid = _oid("tb")
    gfont = FONT_MAP.get(font or "", font or "Inter")
    reqs = [
        {
            "createShape": {
                "objectId": tid,
                "shapeType": "TEXT_BOX",
                "elementProperties": _elem_props(slide_oid, x, y, w, h),
            }
        },
        {
            "updateShapeProperties": {
                "objectId": tid,
                "shapeProperties": {"contentAlignment": VALIGN_MAP.get(valign, "TOP")},
                "fields": "contentAlignment",
            }
        },
        {"insertText": {"objectId": tid, "text": txt[:2500], "insertionIndex": 0}},
        {
            "updateTextStyle": {
                "objectId": tid,
                "style": {
                    "foregroundColor": {"opaqueColor": _rgb(color)},
                    "fontFamily": gfont,
                    "fontSize": {"magnitude": max(8.0, round(float(size) * SCALE, 1)), "unit": "PT"},
                    "bold": bool(bold),
                    "italic": bool(italic),
                },
                "textRange": {"type": "ALL"},
                "fields": "foregroundColor,fontFamily,fontSize,bold,italic",
            }
        },
        {
            "updateParagraphStyle": {
                "objectId": tid,
                "style": {
                    "alignment": ALIGN_MAP.get(align, "START"),
                    "lineSpacing": max(90.0, round(float(lh or 1.15) * 100.0, 1)),
                },
                "textRange": {"type": "ALL"},
                "fields": "alignment,lineSpacing",
            }
        },
    ]
    return reqs


def _resolve_image_url(src, backend_url: str = "") -> str | None:
    url = src.get("url") or src.get("image_url") if isinstance(src, dict) else (src if isinstance(src, str) else "")
    if not url or not isinstance(url, str):
        return None
    u = url.strip()
    if u.startswith("/api/assets/"):
        base = (backend_url or "").strip().rstrip("/")
        if base.startswith("https://") or (base.startswith("http://") and "localhost" not in base and "127.0.0.1" not in base):
            return f"{base}{u}"
        return None
    from services.prompt_safety import is_safe_visual_url
    if (u.startswith("https://") or u.startswith("http://")) and is_safe_visual_url(u):
        return u
    return None


def _chart_reqs(slide_oid: str, p: dict) -> list[dict]:
    """Render a native vector chart in Google Slides matching the PDF/PPTX scene layout."""
    reqs = []
    x, y, w, h = float(p["x"]), float(p["y"]), float(p["w"]), float(p["h"])
    labels = p.get("labels") or []
    series = p.get("series") or []
    cols = p.get("colors") or ["2563eb", "0ea5e9", "10b981", "f59e0b"]
    fg = p.get("fg") or "1e293b"
    grid = p.get("grid") or "cbd5e1"
    font = p.get("font")
    n = len(labels)
    if not n or not series:
        return reqs

    if p.get("kind") in ("pie", "donut"):
        vals = series[0].get("values") or []
        tot = sum(abs(v) for v in vals) or 1.0
        row_h = min(0.55, (h - 0.2) / max(n, 1))
        bar_max_w = max(w * 0.52, 1.0)
        for i, lbl in enumerate(labels):
            v = vals[i] if i < len(vals) else 0
            pct = abs(v) / tot
            ry = y + 0.1 + i * row_h
            col = cols[i % len(cols)]
            reqs += _text_reqs(slide_oid, x, ry, w * 0.32, row_h * 0.85, str(lbl)[:22], 13, fg, bold=True, align="l", valign="m", font=font)
            reqs += _shape_reqs(slide_oid, "RECTANGLE", x + w * 0.34, ry + row_h * 0.18, bar_max_w, row_h * 0.52, fill=grid, alpha=0.35)[0]
            reqs += _shape_reqs(slide_oid, "RECTANGLE", x + w * 0.34, ry + row_h * 0.18, max(bar_max_w * pct, 0.08), row_h * 0.52, fill=col)[0]
            reqs += _text_reqs(slide_oid, x + w * 0.34 + bar_max_w + 0.1, ry, w * 0.16, row_h * 0.85, f"{v:g} ({pct * 100:.0f}%)", 12, fg, valign="m", font=font)
        return reqs

    allv = [v for s in series for v in (s.get("values") or [])]
    vmax, vmin = max(allv + [0]), min(allv + [0])
    span = (vmax - vmin) or 1.0
    left, top, cw, ch = x + 0.55, y + 0.12, max(w - 0.65, 1.0), max(h - 0.52, 0.8)

    for g in range(5):
        gy = top + ch * (1.0 - g / 4.0)
        reqs += _line_reqs(slide_oid, left, gy, left + cw, gy, grid, lw=0.75)
        reqs += _text_reqs(slide_oid, x, gy - 0.14, 0.5, 0.28, f"{vmin + span * g / 4.0:g}", 10, fg, align="r", valign="m", font=font)

    slot = cw / n
    for si, s in enumerate(series):
        col = cols[si % len(cols)]
        vals = s.get("values") or []
        if p.get("kind") == "line":
            pts = [(left + slot * (i + 0.5), top + ch * (1.0 - (v - vmin) / span)) for i, v in enumerate(vals)]
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                reqs += _line_reqs(slide_oid, x1, y1, x2, y2, col, lw=2.5)
            for px, py in pts:
                reqs += _shape_reqs(slide_oid, "ELLIPSE", px - 0.07, py - 0.07, 0.14, 0.14, fill=col)[0]
        else:
            bw = (slot * 0.68) / max(len(series), 1)
            for i, v in enumerate(vals):
                bx = left + slot * i + slot * 0.16 + bw * si
                top_val_y = top + ch * (1.0 - (max(v, 0) - vmin) / span)
                bh = max(ch * abs(v) / span, 0.04)
                reqs += _shape_reqs(slide_oid, "RECTANGLE", bx, top_val_y, bw, bh, fill=col)[0]
                if len(series) == 1:
                    reqs += _text_reqs(slide_oid, bx - 0.1, max(y, top_val_y - 0.28), bw + 0.2, 0.26, f"{v:g}", 11, fg, bold=True, align="c", font=font)

    for i, lbl in enumerate(labels):
        reqs += _text_reqs(slide_oid, left + slot * i, top + ch + 0.06, slot, 0.3, str(lbl)[:14], 11, fg, align="c", font=font)
    return reqs


def scene_requests(index: int, scene: dict, backend_url: str = "") -> tuple[list[dict], dict, list[dict]]:
    """Build Google Slides API batchUpdate requests for one composed scene dict."""
    sid = _oid("sl")
    reqs = [
        {"createSlide": {"objectId": sid, "insertionIndex": index, "slideLayoutReference": {"predefinedLayout": "BLANK"}}},
        {
            "updatePageProperties": {
                "objectId": sid,
                "pageProperties": {"pageBackgroundFill": {"solidFill": {"color": _rgb(scene.get("bg", "ffffff"))}}},
                "fields": "pageBackgroundFill.solidFill.color",
            }
        },
    ]
    not_rendered = []

    for item in scene.get("items") or []:
        k = item.get("k")
        if k in ("rect", "ellipse"):
            shape_type = "ELLIPSE" if k == "ellipse" else ("ROUND_RECTANGLE" if item.get("r", 0) > 0.001 else "RECTANGLE")
            r, _ = _shape_reqs(
                sid, shape_type, item["x"], item["y"], item["w"], item["h"],
                fill=item.get("fill"), line=item.get("line"), lw=item.get("lw", 1.0), alpha=item.get("alpha", 1.0),
            )
            reqs += r
        elif k == "line":
            reqs += _line_reqs(
                sid, item["x1"], item["y1"], item["x2"], item["y2"],
                item.get("color", "64748b"), lw=item.get("lw", 1.5),
                dash=bool(item.get("dash")), arrow=bool(item.get("arrow")),
            )
        elif k == "text":
            reqs += _text_reqs(
                sid, item["x"], item["y"], item["w"], item["h"], item.get("text", ""),
                item.get("size", 14), item.get("color", "0f172a"),
                bold=bool(item.get("bold")), italic=bool(item.get("italic")),
                align=item.get("align", "l"), valign=item.get("valign", "t"),
                font=item.get("font"), lh=item.get("lh", 1.15),
            )
        elif k == "image":
            img_url = _resolve_image_url(item.get("src"), backend_url=backend_url)
            if img_url:
                reqs.append({
                    "createImage": {
                        "objectId": _oid("im"),
                        "url": img_url,
                        "elementProperties": _elem_props(sid, item["x"], item["y"], item["w"], item["h"]),
                    }
                })
            elif item.get("src"):
                not_rendered.append({"slide": index + 1, "what": "image", "reason": "local asset needs a public BACKEND_URL"})
        elif k == "chart":
            reqs += _chart_reqs(sid, item)

    return reqs, {"slide": sid}, not_rendered


def deck_requests(scenes: list[dict], backend_url: str = "") -> tuple[list[dict], list[dict], list[dict]]:
    """Build Google Slides API requests for all scenes in a presentation."""
    reqs, ids, not_rendered = [], [], []
    for idx, sc in enumerate(scenes):
        r, oid, nr = scene_requests(idx, sc, backend_url=backend_url)
        reqs += r
        ids.append(oid)
        not_rendered += nr
    return reqs, ids, not_rendered
