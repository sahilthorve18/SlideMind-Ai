"""Scene -> PDF (reportlab). Same scene as the PPTX writer, so the PDF matches the deck."""
import io
import math

from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from . import images

PT = 72.0
BASE = {("Calibri", False): "Helvetica", ("Calibri", True): "Helvetica-Bold", ("Georgia", False): "Times-Roman", ("Georgia", True): "Times-Bold",
        ("Consolas", False): "Courier", ("Consolas", True): "Courier-Bold"}


def _font(name, bold, italic):
    f = BASE.get((name, bool(bold)), "Helvetica-Bold" if bold else "Helvetica")
    if italic and not bold:
        f = {"Helvetica": "Helvetica-Oblique", "Times-Roman": "Times-Italic", "Courier": "Courier-Oblique"}.get(f, f)
    return f


def _wrap(s, font, size, width_pt):
    lines = []
    for para in str(s).split("\n"):
        cur = ""
        for w in para.split():
            t = (cur + " " + w).strip()
            if stringWidth(t, font, size) <= width_pt or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def _col(h):
    return HexColor("#" + h)


def scenes_to_pdf(scenes: list[dict], title: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(13.333 * PT, 7.5 * PT))
    c.setTitle(title[:200])
    H = 7.5 * PT
    for sc in scenes:
        c.setFillColor(_col(sc["bg"]))
        c.rect(0, 0, 13.333 * PT, H, stroke=0, fill=1)
        for p in sc["items"]:
            k = p["k"]
            if k in ("rect", "ellipse"):
                x, y, w, h = p["x"] * PT, H - (p["y"] + p["h"]) * PT, p["w"] * PT, p["h"] * PT
                c.saveState()
                c.setFillAlpha(p.get("alpha", 1) if p.get("fill") else 1)
                if p.get("fill"):
                    c.setFillColor(_col(p["fill"]))
                if p.get("line"):
                    c.setStrokeColor(_col(p["line"]))
                    c.setLineWidth(p.get("lw", 1))
                fl, st = 1 if p.get("fill") else 0, 1 if p.get("line") else 0
                if k == "ellipse":
                    c.ellipse(x, y, x + w, y + h, stroke=st, fill=fl)
                elif p.get("r", 0) > 0.001:
                    c.roundRect(x, y, w, h, min(p["r"] * PT, min(w, h) / 2), stroke=st, fill=fl)
                else:
                    c.rect(x, y, w, h, stroke=st, fill=fl)
                c.restoreState()
            elif k == "line":
                c.saveState()
                c.setStrokeColor(_col(p["color"]))
                c.setFillColor(_col(p["color"]))
                c.setLineWidth(p.get("lw", 1.5))
                if p.get("dash"):
                    c.setDash(5, 4)
                x1, y1, x2, y2 = p["x1"] * PT, H - p["y1"] * PT, p["x2"] * PT, H - p["y2"] * PT
                c.line(x1, y1, x2, y2)
                if p.get("arrow"):
                    c.setDash()
                    ang = math.atan2(y2 - y1, x2 - x1)
                    a = 8
                    path = c.beginPath()
                    path.moveTo(x2, y2)
                    path.lineTo(x2 - a * math.cos(ang - 0.45), y2 - a * math.sin(ang - 0.45))
                    path.lineTo(x2 - a * math.cos(ang + 0.45), y2 - a * math.sin(ang + 0.45))
                    path.close()
                    c.drawPath(path, stroke=0, fill=1)
                c.restoreState()
            elif k == "text":
                font = _font(p.get("font"), p.get("bold"), p.get("italic"))
                size = p["size"]
                lines = _wrap(p["text"], font, size, p["w"] * PT)
                lh = size * 1.2
                total = lh * len(lines)
                top = H - p["y"] * PT
                if p.get("valign") == "m":
                    top -= (p["h"] * PT - total) / 2
                elif p.get("valign") == "b":
                    top -= p["h"] * PT - total
                c.setFillColor(_col(p["color"]))
                c.setFont(font, size)
                for i, ln in enumerate(lines):
                    yy = top - lh * (i + 1) + size * 0.22
                    xx = p["x"] * PT
                    wd = stringWidth(ln, font, size)
                    if p.get("align") == "c":
                        xx += (p["w"] * PT - wd) / 2
                    elif p.get("align") == "r":
                        xx += p["w"] * PT - wd
                    c.drawString(xx, yy, ln)
            elif k == "image":
                raw = images.image_bytes(p.get("src"))
                conv = images.to_png_or_jpeg(raw) if raw else None
                if not conv:
                    continue
                from reportlab.lib.utils import ImageReader
                data, iw, ih = conv
                x, y, w, h = p["x"] * PT, H - (p["y"] + p["h"]) * PT, p["w"] * PT, p["h"] * PT
                sc_ = max(w / iw, h / ih)
                dw, dh = iw * sc_, ih * sc_
                c.saveState()
                pth = c.beginPath()
                if p.get("r", 0) > 0.001:
                    pth.roundRect(x, y, w, h, min(p["r"] * PT, min(w, h) / 2))
                else:
                    pth.rect(x, y, w, h)
                c.clipPath(pth, stroke=0, fill=0)
                c.drawImage(ImageReader(io.BytesIO(data)), x - (dw - w) / 2, y - (dh - h) / 2, dw, dh)
                c.restoreState()
            elif k == "chart":
                _chart(c, p, H)
        c.showPage()
    c.save()
    return buf.getvalue()


def _chart(c, p, H):
    x, y, w, h = p["x"] * PT, H - (p["y"] + p["h"]) * PT, p["w"] * PT, p["h"] * PT
    labels, series, cols = p["labels"], p["series"], p["colors"]
    fg = _col(p["fg"])
    n = len(labels)
    if p["kind"] in ("pie", "donut"):
        vals = series[0]["values"]
        tot = sum(vals) or 1
        r = min(w * 0.5, h) / 2 - 8
        cx, cy = x + r + 10, y + h / 2
        ang = 90
        for i, v in enumerate(vals):
            sweep = 360 * v / tot
            c.setFillColor(_col(cols[i % len(cols)]))
            c.setStrokeColor(_col(p["bg"]))
            c.wedge(cx - r, cy - r, cx + r, cy + r, ang - sweep, sweep, stroke=1, fill=1)
            ang -= sweep
        if p["kind"] == "donut":
            c.setFillColor(_col(p["bg"]))
            c.circle(cx, cy, r * 0.55, stroke=0, fill=1)
        c.setFont("Helvetica", 13)
        for i, l in enumerate(labels):
            yy = y + h - 24 - i * 20
            c.setFillColor(_col(cols[i % len(cols)]))
            c.rect(x + 2 * r + 40, yy, 11, 11, stroke=0, fill=1)
            c.setFillColor(fg)
            c.drawString(x + 2 * r + 58, yy + 1, f"{l}  {vals[i]:g}")
        return
    allv = [v for s in series for v in s["values"]]
    vmax, vmin = max(allv + [0]), min(allv + [0])
    span = (vmax - vmin) or 1
    left, bottom = x + 34, y + 26
    cw, ch = w - 44, h - 40
    c.setStrokeColor(_col(p["grid"]))
    c.setLineWidth(0.6)
    c.setFont("Helvetica", 11)
    c.setFillColor(fg)
    for g in range(5):
        gy = bottom + ch * g / 4
        c.line(left, gy, left + cw, gy)
        c.drawRightString(left - 5, gy - 3, f"{vmin + span * g / 4:g}")
    slot = cw / n
    zero = bottom + ch * (0 - vmin) / span
    for si, s in enumerate(series):
        col = _col(cols[si % len(cols)])
        if p["kind"] == "line":
            c.setStrokeColor(col)
            c.setLineWidth(3)
            pts = [(left + slot * (i + 0.5), bottom + ch * (v - vmin) / span) for i, v in enumerate(s["values"])]
            for a, b in zip(pts, pts[1:]):
                c.line(a[0], a[1], b[0], b[1])
            c.setFillColor(col)
            for px, py in pts:
                c.circle(px, py, 4, stroke=0, fill=1)
        else:
            bw = slot * 0.7 / len(series)
            c.setFillColor(col)
            for i, v in enumerate(s["values"]):
                bx = left + slot * i + slot * 0.15 + bw * si
                by = bottom + ch * (min(v, 0) - vmin) / span
                c.rect(bx, by, bw, ch * abs(v) / span, stroke=0, fill=1)
                if len(series) == 1:
                    c.setFillColor(fg)
                    c.setFont("Helvetica-Bold", 12)
                    c.drawCentredString(bx + bw / 2, bottom + ch * (v - vmin) / span + 4, f"{v:g}")
                    c.setFillColor(col)
    c.setFillColor(fg)
    c.setFont("Helvetica", 12)
    for i, l in enumerate(labels):
        c.drawCentredString(left + slot * (i + 0.5), y + 8, l[:14])
