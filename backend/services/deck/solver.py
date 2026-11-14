"""Layout solver: slide spec + theme tokens -> a *scene* (positioned drawing primitives, inches, 13.333x7.5).

One scene feeds the PPTX writer, the PDF writer and the React preview, so they cannot drift apart.
Primitives: rect, ellipse, text, line, image, chart. Every primitive may carry `g` (block group id) so
the PPTX writer can animate a whole block at once.
"""
import math
from dataclasses import dataclass, field

from . import fit as F
from .blocks import SMALL, WIDE, normalize_blocks
from .tokens import Theme, _mix, font_kind, resolve_theme

W, H = 13.333, 7.5


@dataclass
class Ctx:
    t: Theme
    idx: int = 0
    total: int = 1
    deck_title: str = ""
    items: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    gid: int = 0

    def add(self, p):
        p.setdefault("g", self.gid)
        self.items.append(p)


# ---------------------------------------------------------------- primitives
def rect(c, x, y, w, h, fill=None, line=None, lw=1.0, radius=0.0, alpha=1.0, shadow=False):
    c.add({"k": "rect", "x": x, "y": y, "w": w, "h": h, "fill": fill, "line": line, "lw": lw, "r": radius, "alpha": alpha, "shadow": shadow})


def ellipse(c, x, y, w, h, fill=None, line=None, lw=1.0, alpha=1.0):
    c.add({"k": "ellipse", "x": x, "y": y, "w": w, "h": h, "fill": fill, "line": line, "lw": lw, "alpha": alpha})


def line(c, x1, y1, x2, y2, color, lw=1.5, arrow=False, dash=False):
    c.add({"k": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "color": color, "lw": lw, "arrow": arrow, "dash": dash})


def text(c, x, y, w, h, s, size, color, bold=False, italic=False, align="l", valign="t", font=None, upper=False):
    if not s:
        return
    c.add({"k": "text", "x": x, "y": y, "w": w, "h": h, "text": s.upper() if upper else s, "size": size, "color": color, "bold": bold,
           "italic": italic, "align": align, "valign": valign, "font": font or c.t.font_body})


def fit_text(c, x, y, w, h, s, max_size, min_size, color, bold=False, italic=False, align="l", valign="t", font=None,
             serif=None, upper=False, role="body"):
    """Place text sized to fit the box. Never goes below min_size: truncates at a word boundary instead."""
    if not s:
        return 0.0
    font = font or c.t.font_body
    serif = font_kind(font) if serif is None else serif
    size, lines, over = F.fit(s, w, h, max_size, min_size, bold, serif)
    if over:
        s2 = F.truncate_to_fit(s, w, h, size, bold, serif)
        c.warnings.append(f"text truncated at minimum size: {s[:40]}")
        s = s2
        lines = F.wrap(s, w, size, bold, serif)
    used = F.height_in(len(lines), size)
    text(c, x, y, w, h, s, size, color, bold, italic, align, valign, font, upper)
    return used


def card(c, x, y, w, h, style=None, tint=False):
    """Draw a card container; returns (text colour, muted colour, inner padding)."""
    t = c.t
    st = style or t.comp.card_style
    pad = 0.22
    if st == "filled":
        rect(c, x, y, w, h, fill=t.card, line=t.border, lw=0.75, radius=t.radius)
        return t.title, t.body, pad
    if st == "outline":
        rect(c, x, y, w, h, fill=None, line=t.title if not t.dark else t.accent, lw=1.5, radius=t.radius)
        return t.title, t.body, pad
    if st == "underline":
        line(c, x, y, x + w, y, t.accent, 3)
        return t.title, t.body, pad
    if st == "accent":
        rect(c, x, y, w, h, fill=t.accent, radius=t.radius)
        return t.on_accent, t.on_accent, pad
    rect(c, x, y, w, h, fill=t.card, line=t.accent2, lw=1, radius=t.radius, alpha=0.85)  # glass
    return t.title, t.body, pad


# ---------------------------------------------------------------- block renderers
def r_headline(c, b, r):
    x, y, w, h = r
    t = c.t
    s, lines, _ = F.fit(b["text"], w, h - (0.5 if b.get("sub") else 0.2), 40, 28, True, t.title_serif)
    used = fit_text(c, x, y, w, h - (0.5 if b.get("sub") else 0.2), b["text"], 40, 28, t.title, True, font=t.font_title, valign="m")
    rect(c, x, y + h - 0.12, 1.0, 0.06, fill=t.accent)
    if b.get("sub"):
        text(c, x, y + h - 0.55, w, 0.4, b["sub"], 14, t.muted)


def r_stat_row(c, b, r):
    x, y, w, h = r
    t = c.t
    items = b["items"]
    n = len(items)
    gap = 0.3 * t.comp.gap
    cw = (w - gap * (n - 1)) / n
    if cw < 2.6:  # narrow area: stack the stats as rows (big value left, label right)
        rh = min((h - gap * (n - 1)) / n, 1.8)
        oy = y + (h - (rh * n + gap * (n - 1))) / 2
        for i, it in enumerate(items):
            ry = oy + i * (rh + gap)
            tc, mc, pad = card(c, x, ry, w, rh)
            vc = tc if t.comp.card_style == "accent" else t.accent
            vw = w * 0.38
            vsize, _, _ = F.fit(it["value"], vw - pad, rh - 0.2, 54, 32, True, t.title_serif)
            text(c, x + pad, ry, vw - pad, rh, it["value"], vsize, vc, True, font=t.font_title, valign="m")
            lw_ = w - vw - pad
            used = fit_text(c, x + vw, ry + 0.12, lw_, rh * 0.5, it["label"], 20, 18, tc, True, valign="b" if it.get("note") else "m")
            if it.get("note"):
                fit_text(c, x + vw, ry + 0.12 + rh * 0.5 + 0.04, lw_, rh * 0.5 - 0.2, it["note"], 16, 14, mc)
        return
    ch = min(h, 3.6)
    y0 = y + (h - ch) / 2
    for i, it in enumerate(items):
        cx = x + i * (cw + gap)
        tc, mc, pad = card(c, cx, y0, cw, ch)
        vc = tc if t.comp.card_style == "accent" else t.accent
        iw = cw - 2 * pad
        vsize, _, _ = F.fit(it["value"], iw, 1.2, 66, 34, True, t.title_serif)
        text(c, cx + pad, y0 + 0.2, iw, 1.3, it["value"], vsize, vc, True, font=t.font_title, valign="m")
        used = fit_text(c, cx + pad, y0 + 1.55, iw, 0.9, it["label"], 22, 18, tc, True)
        if it.get("note"):
            fit_text(c, cx + pad, y0 + 1.55 + max(used, 0.4) + 0.08, iw, ch - (1.55 + max(used, 0.4) + 0.2), it["note"], 16, 14, mc)


def r_steps(c, b, r):
    x, y, w, h = r
    t = c.t
    items = b["items"]
    n = len(items)
    cols = n if n <= 4 else 3
    rows = math.ceil(n / cols)
    gap = 0.3 * t.comp.gap
    cw = (w - gap * (cols - 1)) / cols
    rh = h / rows
    shift = max(0.0, (h - 3.2) * 0.35) if rows == 1 else 0.0
    for i, it in enumerate(items):
        col, row = i % cols, i // cols
        cx, cy = x + col * (cw + gap), y + row * rh + shift
        d = 0.62
        outline = t.comp.number_style == "outline"
        if col < cols - 1 and i < n - 1:
            line(c, cx + d + 0.1, cy + d / 2, cx + cw + gap - 0.05, cy + d / 2, t.border if not t.dark else t.muted, 1.5)
        ellipse(c, cx, cy, d, d, fill=None if outline else t.accent, line=t.accent if outline else None, lw=2)
        text(c, cx, cy, d, d, str(i + 1) if t.comp.number_style != "plain" else f"{i + 1:02d}", 20 if t.comp.number_style != "plain" else 16,
             t.accent if outline else t.on_accent, True, align="c", valign="m")
        if t.comp.number_style == "plain":
            ellipse(c, cx, cy, d, d, fill=None, line=t.accent, lw=1.5)
        used = fit_text(c, cx, cy + d + 0.12, cw - 0.1, 0.95, it["title"], 22, 18, t.title, True, font=t.font_title)
        if it.get("body"):
            top = cy + d + 0.2 + max(used, 0.35)
            fit_text(c, cx, top, cw - 0.1, rh - (top - cy) - 0.1, it["body"], 20, 14, t.body)


def _layers(nodes, edges):
    ids = [n["id"] for n in nodes]
    out = {i: [] for i in ids}
    for e in edges:
        out[e["from"]].append(e["to"])
    state, back = {}, set()

    def dfs(u):
        state[u] = 1
        for v in out[u]:
            if state.get(v) == 1:
                back.add((u, v))
            elif state.get(v) is None:
                dfs(v)
        state[u] = 2

    indeg = {i: 0 for i in ids}
    for e in edges:
        indeg[e["to"]] += 1
    for s in [i for i in ids if indeg[i] == 0] + ids:
        if state.get(s) is None:
            dfs(s)
    layer = {i: 0 for i in ids}
    for _ in range(len(ids)):
        for e in edges:
            if (e["from"], e["to"]) not in back and layer[e["to"]] < layer[e["from"]] + 1:
                layer[e["to"]] = layer[e["from"]] + 1
    return layer


def r_diagram(c, b, r):
    x, y, w, h = r
    t = c.t
    nodes, edges = b["nodes"], b["edges"]
    cap_h = 0.45 if b.get("caption") else 0.0
    h -= cap_h
    layer = _layers(nodes, edges)
    L = max(layer.values()) + 1
    pos = {}
    if len(nodes) > 3 and (L > 5 or (w - 0.55 * (L - 1)) / L < 2.0):  # too wide: snake into two rows
        half = math.ceil(len(nodes) / 2)
        for i, n in enumerate(nodes):
            pos[n["id"]] = (i % half, i // half)
        ncols, nrows = half, 2
    else:
        rowcount = {}
        for n in nodes:
            col = layer[n["id"]]
            pos[n["id"]] = (col, rowcount.get(col, 0))
            rowcount[col] = rowcount.get(col, 0) + 1
        ncols, nrows = L, max(rowcount.values())
    has_detail = any(n["detail"] for n in nodes)
    back_room = 0.55
    gx = (0.8 if any(e.get('label') for e in edges) else 0.55) * t.comp.gap if ncols > 1 else 0
    nw = min(3.0, (w - gx * (ncols - 1)) / ncols)
    nh_max = 1.5 if has_detail else 0.95
    gy = 0.45
    nh = min(nh_max, (h - back_room - gy * (nrows - 1)) / nrows)
    total_w = nw * ncols + gx * (ncols - 1)
    total_h = nh * nrows + gy * (nrows - 1)
    ox, oy = x + (w - total_w) / 2, y + (h - back_room - total_h) / 2 + 0.1
    box = {}
    for n in nodes:
        col, row = pos[n["id"]]
        bx, by = ox + col * (nw + gx), oy + row * (nh + gy)
        box[n["id"]] = (bx, by, nw, nh)
    ecol = t.accent if not t.dark else t.accent
    for e in edges:
        a, bb = box[e["from"]], box[e["to"]]
        ca, ra = pos[e["from"]]
        cb, rb = pos[e["to"]]
        ax, ay = a[0] + a[2], a[1] + a[3] / 2
        tx, ty = bb[0], bb[1] + bb[3] / 2
        label_at = None
        if rb > ra and cb <= ca:  # wrap to next row
            ym = a[1] + a[3] + gy / 2
            sx, sy = a[0] + a[2] / 2, a[1] + a[3]
            ex, ey = bb[0] + bb[2] / 2, bb[1]
            line(c, sx, sy, sx, ym, ecol, 2)
            line(c, sx, ym, ex, ym, ecol, 2)
            line(c, ex, ym, ex, ey, ecol, 2, arrow=True)
            label_at = ((sx + ex) / 2, ym)
        elif cb < ca or rb < ra or (cb == ca and rb == ra):  # back/upward edge: routed under the rows, clear of other nodes
            yb = oy + total_h + 0.28
            sx, ex = a[0] + a[2] / 2, bb[0] + bb[2] / 2
            line(c, sx, a[1] + a[3], sx, yb, ecol, 2, dash=True)
            line(c, sx, yb, ex, yb, ecol, 2, dash=True)
            line(c, ex, yb, ex, bb[1] + bb[3], ecol, 2, dash=True, arrow=True)
            label_at = ((sx + ex) / 2, yb)
        elif cb == ca:  # same column, stacked
            sx = a[0] + a[2] / 2
            if rb > ra:
                line(c, sx, a[1] + a[3], sx, bb[1], ecol, 2, arrow=True)
            else:
                line(c, sx, a[1], sx, bb[1] + bb[3], ecol, 2, arrow=True)
            label_at = (sx, (a[1] + a[3] + bb[1]) / 2)
        elif rb == ra:
            line(c, ax, ay, tx, ty, ecol, 2, arrow=True)
            label_at = ((ax + tx) / 2, ay)
        else:
            xm = (ax + tx) / 2
            line(c, ax, ay, xm, ay, ecol, 2)
            line(c, xm, ay, xm, ty, ecol, 2)
            line(c, xm, ty, tx, ty, ecol, 2, arrow=True)
            label_at = (xm, (ay + ty) / 2)
        if e.get("label") and label_at:
            lw_ = F.text_width_in(e["label"], 12) + 0.2
            rect(c, label_at[0] - lw_ / 2, label_at[1] - 0.3, lw_, 0.24, fill=t.bg, radius=0.04)
            text(c, label_at[0] - lw_ / 2, label_at[1] - 0.3, lw_, 0.24, e["label"], 12, t.muted, bold=True, align="c", valign="m")
    for i, n in enumerate(nodes):
        bx, by, bw, bh = box[n["id"]]
        tc, mc, pad = card(c, bx, by, bw, bh, style="filled" if t.comp.card_style in ("underline",) else None)
        if t.comp.card_style == "underline":
            rect(c, bx, by, bw, bh, fill=t.card, line=t.border, lw=0.75, radius=t.radius)
            rect(c, bx, by, 0.07, bh, fill=t.accent)
            tc, mc = t.title, t.body
        p = 0.1
        lab_h = bh - 2 * p if not n["detail"] else min(0.7, bh * 0.5)
        used = fit_text(c, bx + p, by + p, bw - 2 * p, lab_h, n["label"], 20, 18, tc, True, align="c", valign="m" if not n["detail"] else "t",
                        font=t.font_title)
        if n["detail"]:
            top = by + p + max(used, 0.3) + 0.04
            fit_text(c, bx + p, top, bw - 2 * p, bh - (top - by) - p, n["detail"], 16, 14, mc, align="c")
    if b.get("caption"):
        text(c, x, y + h + 0.05, w, 0.35, b["caption"], 12, t.muted, italic=True)


def r_timeline(c, b, r):
    x, y, w, h = r
    t = c.t
    items = b["items"]
    n = len(items)
    cw = w / n
    ym = y + h / 2
    line(c, x, ym, x + w, ym, t.border if not t.dark else t.muted, 3)
    tw = min(3.6, cw * 1.7)
    for i, it in enumerate(items):
        cx = x + cw * (i + 0.5)
        above = i % 2 == 0
        ellipse(c, cx - 0.16, ym - 0.16, 0.32, 0.32, fill=t.accent, line=t.bg, lw=3)
        bx = min(max(cx - tw / 2, x), x + w - tw)
        room = h / 2 - 0.55
        if above:
            line(c, cx, ym - 0.16, cx, ym - 0.45, t.accent, 1.5)
        else:
            line(c, cx, ym + 0.16, cx, ym + 0.45, t.accent, 1.5)
        paras = []
        if it["when"]:
            paras.append((it["when"], 20, 18, t.accent, True, t.font_title))
        paras.append((it["title"], 20, 18, t.title, True, t.font_title))
        if it["body"]:
            paras.append((it["body"], 16, 14, t.body, False, t.font_body))
        # measure paragraph heights to stack them
        sizes = []
        for s, mx, mn, col, bd, fnt in paras:
            sz, lines, _ = F.fit(s, tw, room, mx, mn, bd, font_kind(fnt))
            sizes.append((s, sz, F.height_in(len(lines), sz), col, bd, fnt))
        tot = sum(z[2] for z in sizes) + 0.05 * (len(sizes) - 1)
        cy = (ym - 0.5 - tot) if above else (ym + 0.5)
        al = "c"
        for s, sz, hh, col, bd, fnt in sizes:
            text(c, bx, cy, tw, hh + 0.04, s, sz, col, bd, align=al, font=fnt)
            cy += hh + 0.05


def r_table(c, b, r):
    x, y, w, h = r
    t = c.t
    hdr, rows = b["headers"], b["rows"]
    nc = len(hdr)
    first = 0.34 if nc >= 3 else 0.5
    widths = [w * first] + [w * (1 - first) / (nc - 1)] * (nc - 1)
    rh = min(0.9, h / (len(rows) + 1))
    cx = [x + sum(widths[:i]) for i in range(nc)]
    for j, hd in enumerate(hdr):
        rect(c, cx[j], y, widths[j], rh, fill=t.accent if j else t.title if not t.dark else t.card, line=None)
        fit_text(c, cx[j] + 0.12, y, widths[j] - 0.24, rh, hd, 20, 16, t.on_accent if j else (t.bg if not t.dark else t.title), True, valign="m",
                 font=t.font_title)
    for i, row in enumerate(rows):
        yy = y + rh * (i + 1)
        rect(c, x, yy, w, rh, fill=t.card if i % 2 == 0 else None, line=None)
        line(c, x, yy + rh, x + w, yy + rh, t.border, 0.75)
        for j, cell in enumerate(row):
            fit_text(c, cx[j] + 0.12, yy, widths[j] - 0.24, rh, cell, 18, 14, t.title if j == 0 else t.body, j == 0, valign="m")


def r_matrix(c, b, r):
    x, y, w, h = r
    t = c.t
    lab = 0.4 if (b["x_label"] or b["y_label"]) else 0.0
    gx = 0.25
    qw, qh = (w - lab - gx) / 2, (h - lab - gx) / 2
    for i, q in enumerate(b["quadrants"]):
        qx, qy = x + lab + (i % 2) * (qw + gx), y + (i // 2) * (qh + gx)
        tc, mc, pad = card(c, qx, qy, qw, qh, style="filled" if i != 1 else "accent")
        used = fit_text(c, qx + pad, qy + pad, qw - 2 * pad, 0.9, q["title"], 22, 18, tc, True, font=t.font_title)
        if q["body"]:
            top = qy + pad + max(used, 0.35) + 0.08
            fit_text(c, qx + pad, top, qw - 2 * pad, qh - (top - qy) - pad, q["body"], 18, 14, mc)
    if b["x_label"]:
        text(c, x + lab, y + h - 0.32, w - lab, 0.3, b["x_label"] + "  →", 12, t.muted, align="c", upper=True)
    if b["y_label"]:
        text(c, x, y + h - lab - 0.1, h, 0.3, "↑  " + b["y_label"], 12, t.muted, upper=True)


def r_chart(c, b, r):
    x, y, w, h = r
    t = c.t
    top = 0.0
    if b["title"]:
        fit_text(c, x, y, w, 0.5, b["title"], 22, 18, t.title, True, font=t.font_title)
        top = 0.6
    bot = 0.35 if b["source"] else 0.0
    c.add({"k": "chart", "x": x, "y": y + top, "w": w, "h": h - top - bot, "kind": b["kind"], "labels": b["labels"],
           "series": b["series"], "unit": b["unit"], "colors": t.palette[:max(len(b["series"]), 1)] if b["kind"] not in ("pie", "donut") else t.palette,
           "fg": t.body, "grid": t.border, "bg": t.bg, "font": t.font_body, "size": 14})
    if b["source"]:
        text(c, x, y + h - 0.32, w, 0.3, "Source: " + b["source"], 12, t.muted)


def r_cards(c, b, r):
    x, y, w, h = r
    t = c.t
    items = b["items"]
    n = len(items)
    cols = n if n <= 3 else (2 if n == 4 and h > 3.6 else (4 if n == 4 else 3))
    gap = 0.28 * t.comp.gap
    if w / cols < 3.0 and n <= 4:  # narrow area: one card per row, title left / body right
        rh = min((h - gap * (n - 1)) / n, 1.7)
        oy = y + (h - (rh * n + gap * (n - 1))) / 2
        for i, it in enumerate(items):
            cy = oy + i * (rh + gap)
            tc, mc, pad = card(c, x, cy, w, rh)
            tw = w * 0.36
            badge = it.get("tag") or f"{i + 1:02d}"
            text(c, x + pad, cy + 0.12, tw, 0.3, badge, 12, t.accent if t.comp.card_style != "accent" else t.on_accent, True, upper=True)
            fit_text(c, x + pad, cy + 0.42, tw - pad, rh - 0.5, it["title"], 22, 18, tc, True, font=t.font_title)
            if it["body"]:
                fit_text(c, x + tw + pad, cy + 0.12, w - tw - 2 * pad, rh - 0.24, it["body"], 18, 14, mc, valign="m")
        return
    rows = math.ceil(n / cols)
    cw, chh = (w - gap * (cols - 1)) / cols, (h - gap * (rows - 1)) / rows
    chh = min(chh, 3.4)
    oy = y + (h - (chh * rows + gap * (rows - 1))) / 2 if rows == 1 else y
    for i, it in enumerate(items):
        cx, cy = x + (i % cols) * (cw + gap), oy + (i // cols) * (chh + gap)
        tc, mc, pad = card(c, cx, cy, cw, chh)
        badge = it.get("tag") or f"{i + 1:02d}"
        text(c, cx + pad, cy + pad - 0.04, cw - 2 * pad, 0.3, badge, 12, t.accent if t.comp.card_style != "accent" else t.on_accent, True, upper=True)
        used = fit_text(c, cx + pad, cy + pad + 0.3, cw - 2 * pad, 1.0, it["title"], 22, 18, tc, True, font=t.font_title)
        if it["body"]:
            top = cy + pad + 0.38 + max(used, 0.35)
            fit_text(c, cx + pad, top, cw - 2 * pad, chh - (top - cy) - pad, it["body"], 20, 14, mc)


def r_callout(c, b, r):
    x, y, w, h = r
    t = c.t
    rect(c, x, y, w, h, fill=t.card, line=t.border, lw=0.75, radius=t.radius)
    rect(c, x, y, 0.1, h, fill=t.accent)
    top = y + 0.18
    if b.get("label"):
        text(c, x + 0.35, top, w - 0.6, 0.3, b["label"], 12, t.accent, True, upper=True)
        top += 0.34
    fit_text(c, x + 0.35, top, w - 0.65, y + h - top - 0.15, b["text"], 28, 20, t.title, True, font=t.font_title, valign="m")


def r_quote(c, b, r):
    x, y, w, h = r
    t = c.t
    text(c, x, y - 0.1, 1.0, 1.2, "“", 88, t.accent, True, font="Georgia")
    by_h = 0.4 if b.get("by") else 0
    fit_text(c, x + 1.0, y, w - 1.0, h - by_h, b["text"], 30, 20, t.title, False, True, font=t.font_title, valign="m")
    if b.get("by"):
        text(c, x + 1.0, y + h - 0.38, w - 1.0, 0.35, "— " + b["by"], 14, t.muted)


def r_bullets(c, b, r):
    x, y, w, h = r
    t = c.t
    items = b["items"]
    n = len(items)
    each = h / n
    for i, s in enumerate(items):
        yy = y + i * each
        rect(c, x, yy + 0.16, 0.14, 0.14, fill=t.accent, radius=0 if t.radius < 0.05 else 0.07)
        fit_text(c, x + 0.4, yy, w - 0.4, each - 0.05, s, 24, 18, t.title, valign="m")


def r_image(c, b, r, style=None):
    x, y, w, h = r
    t = c.t
    cap = 0.34 if b.get("caption") else 0
    st = style or t.comp.image_style
    rr = t.radius if st == "framed" else 0
    c.add({"k": "image", "x": x, "y": y, "w": w, "h": h - cap, "src": b["src"], "alt": b.get("alt", ""), "r": rr,
           "line": t.border if st == "framed" else None})
    if cap:
        text(c, x, y + h - cap + 0.04, w, 0.3, b["caption"], 12, t.muted, italic=True)


def r_stat(c, b, r):
    r_stat_row(c, {"items": [b]}, r)


RENDER = {"headline": r_headline, "stat": r_stat, "stat_row": r_stat_row, "steps": r_steps, "diagram": r_diagram, "timeline": r_timeline,
          "comparison_table": r_table, "matrix_2x2": r_matrix, "chart": r_chart, "cards": r_cards, "callout": r_callout, "quote": r_quote,
          "image": r_image, "bullets": r_bullets}


# ---------------------------------------------------------------- arrangement
def _need_height(b, w):
    t = b["type"]
    if t == "callout":
        s, lines, _ = F.fit(b["text"], w - 0.65, 3, 28, 20, True)
        return F.height_in(len(lines), s) + (0.34 if b.get("label") else 0) + 0.4
    if t == "quote":
        s, lines, _ = F.fit(b["text"], w - 1.0, 3, 30, 20, False)
        return F.height_in(len(lines), s) + 0.5 + (0.4 if b.get("by") else 0)
    if t == "headline":
        s, lines, _ = F.fit(b["text"], w, 3, 40, 28, True)
        return F.height_in(len(lines), s) + (0.7 if b.get("sub") else 0.35)
    return 1.0


def _place(blocks, rect_, gap, mirror=False):
    x, y, w, h = rect_
    n = len(blocks)
    if n == 1:
        return [(blocks[0], rect_)]
    small = [b for b in blocks if b["type"] in SMALL]
    rest = [b for b in blocks if b["type"] not in SMALL]
    if small and rest:
        sh = min(max(_need_height(b, w) for b in small), h * 0.34)
        out = []
        if mirror:  # small block below instead of above, for compositional variety
            out += _place(rest, (x, y, w, h - sh - gap), gap, mirror)
            out += [(small[0], (x, y + h - sh, w, sh))]
            if len(small) > 1:
                out += _place(small[1:], (x, y + h - sh, w, sh), gap)
        else:
            out += [(small[0], (x, y, w, sh))]
            out += _place(rest, (x, y + sh + gap, w, h - sh - gap), gap, mirror)
        return out
    if n == 2:
        a, b = blocks
        a_wide, b_wide = a["type"] in WIDE, b["type"] in WIDE
        if (a_wide or b_wide) and not (a_wide and b_wide and w / h < 2):
            wt = {"steps": 0.7, "timeline": 0.9}
            wa_, wb_ = wt.get(a["type"], 1.3 if a_wide else 0.7), wt.get(b["type"], 1.3 if b_wide else 0.7)
            ha = h * wa_ / (wa_ + wb_)
            sr = min(3.0, max(2.4, h * 0.4))
            if a["type"] == "stat_row":
                ha = sr
            elif b["type"] == "stat_row":
                ha = h - sr
            return [(a, (x, y, w, ha - gap / 2)), (b, (x, y + ha + gap / 2, w, h - ha - gap / 2))]
        wa = w * (0.44 if mirror else 0.5)
        return [(a, (x, y, wa - gap / 2, h)), (b, (x + wa + gap / 2, y, w - wa - gap / 2, h))]
    if n == 3:
        if any(b["type"] in WIDE for b in blocks):
            first = blocks[0]
            top_h = h * 0.5
            return [(first, (x, y, w, top_h - gap / 2))] + _place(blocks[1:], (x, y + top_h + gap / 2, w, h - top_h - gap / 2), gap)
        cw = (w - 2 * gap) / 3
        return [(b, (x + i * (cw + gap), y, cw, h)) for i, b in enumerate(blocks)]
    cw, ch = (w - gap) / 2, (h - gap) / 2
    return [(b, (x + (i % 2) * (cw + gap), y + (i // 2) * (ch + gap), cw, ch)) for i, b in enumerate(blocks[:4])]


# ---------------------------------------------------------------- slide frames
def _ornament(c, kind, x, y, align="l"):
    t = c.t
    if kind == "rule":
        rect(c, x if align == "l" else x - 0.6, y, 1.2, 0.07, fill=t.accent)
    elif kind == "block":
        rect(c, x - 0.0, y - 0.02, 0.28, 0.28, fill=t.accent, radius=0)
    elif kind == "stripe":
        rect(c, 0, 0, 0.16, H, fill=t.accent)
    elif kind == "dots":
        for i in range(4):
            for j in range(3):
                ellipse(c, W - 1.45 + i * 0.26, 0.4 + j * 0.26, 0.09, 0.09, fill=t.accent, alpha=0.7)
    elif kind == "corner":
        rect(c, W - 1.6, 0, 1.6, 0.22, fill=t.accent)
        rect(c, W - 0.22, 0, 0.22, 1.2, fill=t.accent)


def _footer(c, light=False):
    t = c.t
    col = t.muted
    text(c, 0.75, H - 0.5, 8, 0.3, c.deck_title, 12, col)
    text(c, W - 1.75, H - 0.5, 1.0, 0.3, f"{c.idx + 1} / {c.total}", 12, col, align="r")


def _frame(c, title, tagline, kicker, side_bleed=None):
    """Draws the title area per theme rules; returns the content rect."""
    t = c.t
    place = t.comp.title_place
    m = 0.75
    c.gid = 0
    rect(c, 0, 0, W, H, fill=t.bg)
    if place == "rail":
        rw = 4.3
        _ornament(c, t.comp.ornament if t.comp.ornament != "rule" else "none", 0, 0)
        if kicker:
            text(c, m, 0.8, rw, 0.3, kicker, 12, t.accent, True, upper=t.comp.uppercase_kicker)
        used = fit_text(c, m, 1.2, rw, 3.4, title, min(t.comp.title_max, 38), 28, t.title, True, font=t.font_title)
        yy = 1.2 + used + 0.25
        if t.comp.ornament == "rule":
            rect(c, m, yy, 1.0, 0.07, fill=t.accent)
            yy += 0.3
        if tagline:
            fit_text(c, m, yy, rw, 2.0, tagline, 18, 16, t.muted)
        _footer(c)
        return (m + rw + 0.5, 0.8, W - (m + rw + 0.5) - m, H - 1.7)
    if place == "band":
        bh = 1.65
        rect(c, 0, 0, W, bh, fill=t.accent if t.comp.card_style in ("filled", "accent") or not t.dark else t.card)
        band_col = t.on_accent if t.comp.card_style in ("filled", "accent") or not t.dark else t.title
        if t.comp.ornament == "stripe":
            rect(c, 0, bh, W, 0.06, fill=t.accent2)
        fit_text(c, m, 0.2, W - 2 * m - 1.2, bh - 0.4, title, min(t.comp.title_max, 38), 32, band_col, True, font=t.font_title, valign="m")
        if kicker:
            text(c, W - m - 2.2, 0.3, 2.2, 0.3, kicker, 12, band_col, True, align="r", upper=True)
        _footer(c)
        return (m, bh + 0.45, W - 2 * m, H - bh - 1.2)

    # top or center - protect against bleed image overlap
    tx = m
    tw = W - 2 * m
    if side_bleed:
        biw, bflip = side_bleed
        tw = W - 2 * m - biw - 0.4
        if bflip:
            tx = biw + 0.5

    al = "c" if place == "center" and not side_bleed else "l"
    _ornament(c, t.comp.ornament, tx, 0.55)
    ky = 0.5
    if kicker:
        text(c, tx + (0.4 if t.comp.ornament == "block" else 0), ky, tw, 0.3, kicker, 12, t.accent, True, align=al, upper=t.comp.uppercase_kicker)
    used = fit_text(c, tx, 0.85, tw, 1.1, title, t.comp.title_max, 32, t.title, True, align=al, font=t.font_title)
    yy = 0.85 + used + 0.08
    if t.comp.ornament == "rule":
        rect(c, tx if al == "l" else (W - 1.2) / 2, yy + 0.06, 1.2, 0.07, fill=t.accent)
        yy += 0.22
    if tagline and used < 0.95:
        text(c, tx, yy + 0.02, tw, 0.4, tagline, 16, t.muted, align=al)
        yy += 0.42
    _footer(c)
    top = max(yy + 0.3, 2.0)
    return (m, top, W - 2 * m, H - top - 0.75)


def _title_slide(c, spec, img):
    t = c.t
    place = t.comp.title_place
    title, tag, kicker = spec["title"], spec.get("tagline", ""), spec.get("kicker", "")
    rect(c, 0, 0, W, H, fill=t.bg)
    light = None
    if img and t.comp.image_style == "overlay":
        c.add({"k": "image", "x": 0, "y": 0, "w": W, "h": H, "src": img, "alt": "", "r": 0, "line": None})
        rect(c, 0, 0, W, H, fill="0B0B0F", alpha=0.62)
        light = "FFFFFF"
    tcol, mcol = (light, "D8D8DE") if light else (t.title, t.muted)
    if place == "center" or light:
        al = "c" if place == "center" else "l"
        x0, ww = (1.2, W - 2.4) if al == "c" else (0.9, 8.6)
        if kicker:
            text(c, x0, 2.0, ww, 0.3, kicker, 14, t.accent if not light else "FFFFFF", True, align=al, upper=True)
        used = fit_text(c, x0, 2.4, ww, 2.4, title, max(t.comp.title_max, 54), 40, tcol, True, align=al, font=t.font_title, valign="m")
        rect(c, x0 if al == "l" else (W - 1.4) / 2, 4.95, 1.4, 0.08, fill=t.accent)
        if tag:
            fit_text(c, x0, 5.2, ww, 1.2, tag, 24, 18, mcol, align=al)
        return
    if place == "rail":
        rect(c, 0, 0, 0.2, H, fill=t.accent)
        if kicker:
            text(c, 1.0, 1.5, 7, 0.3, kicker, 14, t.accent, True, upper=True)
        fit_text(c, 1.0, 1.9, 6.8, 3.0, title, max(t.comp.title_max, 50), 40, tcol, True, font=t.font_title, valign="m")
        if tag:
            fit_text(c, 1.0, 5.1, 6.4, 1.4, tag, 22, 18, mcol)
        _hero_panel(c, img, (8.3, 0.0, W - 8.3, H))
        return
    if place == "band":
        pw = 4.4
        rect(c, 0, 0, pw, H, fill=t.accent)
        if kicker:
            text(c, 0.6, 0.7, pw - 1.0, 0.8, kicker, 18, t.on_accent, True, upper=True)
        text(c, 0.6, H - 1.3, pw - 1, 0.6, f"{c.total} slides", 14, t.on_accent)
        fit_text(c, pw + 0.8, 1.6, W - pw - 1.6, 3.0, title, max(t.comp.title_max, 48), 38, tcol, True, font=t.font_title, valign="m")
        if tag:
            fit_text(c, pw + 0.8, 4.9, W - pw - 1.6, 1.5, tag, 22, 18, mcol)
        return
    # top: big title, framed hero at right
    if kicker:
        text(c, 0.9, 0.9, 7, 0.3, kicker, 14, t.accent, True, upper=True)
    fit_text(c, 0.9, 1.3, 7.2, 3.0, title, max(t.comp.title_max, 50), 40, tcol, True, font=t.font_title, valign="m")
    rect(c, 0.9, 4.5, 1.2, 0.08, fill=t.accent)
    if tag:
        fit_text(c, 0.9, 4.85, 7.0, 1.6, tag, 22, 18, mcol)
    _hero_panel(c, img, (8.6, 0.9, W - 8.6 - 0.9, H - 1.8), framed=True)


def _hero_panel(c, img, r, framed=False):
    x, y, w, h = r
    t = c.t
    if img:
        c.add({"k": "image", "x": x, "y": y, "w": w, "h": h, "src": img, "alt": "", "r": t.radius if framed else 0,
               "line": t.border if framed else None})
        return
    # No relevant photo: a purely geometric composition from the theme's own colours (not a fake image)
    rect(c, x, y, w, h, fill=t.accent, radius=t.radius if framed else 0)
    ellipse(c, x + w * 0.15, y + h * 0.12, w * 0.9, w * 0.9, fill=t.accent2, alpha=0.55)
    ellipse(c, x - w * 0.2, y + h * 0.55, w * 0.8, w * 0.8, fill=t.bg, alpha=0.25)
    rect(c, x + w * 0.1, y + h * 0.86, w * 0.5, 0.07, fill=t.on_accent)


def _section_slide(c, spec):
    t = c.t
    rect(c, 0, 0, W, H, fill=t.accent if not t.dark else t.card)
    col = t.on_accent if not t.dark else t.title
    num = spec.get("kicker") or f"{c.idx + 1:02d}"
    text(c, 0.9, 1.6, 6, 2.0, num, 120, col, True, font=t.font_title)
    fit_text(c, 0.9, 3.9, W - 3.0, 1.8, spec["title"], 48, 34, col, True, font=t.font_title)
    if spec.get("tagline"):
        fit_text(c, 0.9, 5.7, W - 3.0, 0.9, spec["tagline"], 22, 18, col)


def build_scene(spec: dict, theme_name, idx=0, total=1, deck_title="") -> dict:
    """spec: {title, tagline?, kicker?, kind: title|section|content, blocks[], image?}"""
    t = resolve_theme(theme_name)
    c = Ctx(t=t, idx=idx, total=total, deck_title=deck_title)
    kind = spec.get("kind") or "content"
    img = spec.get("image")
    if kind == "title":
        _title_slide(c, spec, img)
    elif kind == "section":
        _section_slide(c, spec)
    else:
        blocks = normalize_blocks(spec.get("blocks"))
        flip = t.comp.mirror and idx % 2 == 1
        iw = min(4.6, (W - 1.5) * 0.38)
        has_bleed_img = bool(img and blocks and t.comp.image_style == "bleed")
        side_bleed = (iw, flip) if has_bleed_img else None
        area = _frame(c, spec.get("title", ""), spec.get("tagline", ""), spec.get("kicker", ""), side_bleed=side_bleed)
        x, y, w, h = area
        if img and blocks and t.comp.image_style in ("framed", "bleed", "overlay"):
            iw = min(4.6, w * 0.38)
            if t.comp.image_style == "bleed":
                ix = (W - iw) if not flip else 0
                c.gid = 90
                iy = 1.65 if t.comp.title_place == "band" else 0
                ih = H - iy
                r_image(c, {"src": img, "caption": ""}, (ix, iy, iw, ih), style="bleed")
                if not flip:
                    w = W - iw - 0.75 - 0.4
                    x = 0.75
                else:
                    x = iw + 0.5
                    w = W - iw - 0.75 - 0.5
                if t.comp.title_place == "rail":
                    w = max(w, 4.0)
            else:
                c.gid = 90
                ix = x + w - iw if not flip else x
                r_image(c, {"src": img, "caption": ""}, (ix, y, iw, h), style="framed")
                if not flip:
                    w -= iw + 0.4
                else:
                    x += iw + 0.4
                    w -= iw + 0.4
        gap = 0.35 * t.comp.gap
        for i, (b, rr) in enumerate(_place(blocks, (x, y, w, h), gap, flip)):
            c.gid = i + 1
            RENDER[b["type"]](c, b, rr)
    return {"w": W, "h": H, "bg": t.bg, "items": c.items, "transition": t.comp.transition, "entrance": t.comp.entrance,
            "warnings": c.warnings, "theme": t.id, "notes": spec.get("notes", ""), "kind": kind}
