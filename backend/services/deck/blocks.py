"""Block vocabulary for slide specs: normalisation, required fields and length budgets.

A slide spec is {title, tagline?, kind, blocks[], visual_plan, notes}. Blocks are typed content
(chart, diagram, timeline...). A block that lacks its required data is rejected (returns None), so the
planner must pick another block: nothing is ever filled in with placeholder text.
"""
import re

ALIASES = {"icon_grid": "cards", "feature_cards": "cards", "process": "steps", "process_steps": "steps",
           "lifecycle": "diagram", "flow": "diagram", "architecture": "diagram", "table": "comparison_table",
           "kpis": "stat_row", "metrics": "stat_row", "list": "bullets", "pull_quote": "quote", "key_message": "callout",
           "screenshot": "image", "roadmap": "timeline"}

TYPES = ("headline", "stat", "stat_row", "steps", "diagram", "timeline", "comparison_table", "matrix_2x2", "chart",
         "cards", "callout", "quote", "image", "bullets")
WIDE = {"timeline", "stat_row", "comparison_table", "diagram", "chart", "steps"}
SMALL = {"callout", "quote", "headline"}

BUDGET = {"headline": 110, "callout": 170, "quote": 190, "bullet": 130, "card_title": 38, "card_body": 130,
          "step_title": 40, "step_body": 120, "node_label": 30, "node_detail": 72, "tl_when": 16, "tl_title": 42,
          "tl_body": 110, "cell": 46, "stat_value": 11, "stat_label": 44, "stat_note": 80, "quad_title": 36,
          "quad_body": 110, "caption": 90}
LIMIT = {"cards": (2, 6), "steps": (2, 6), "timeline": (2, 6), "stat_row": (1, 4), "bullets": (1, 6), "diagram": (2, 8)}


def _s(v, n):
    v = re.sub(r"\s+", " ", str(v if v is not None else "")).strip()
    if len(v) <= n:
        return v
    cut = v[:n].rsplit(" ", 1)[0].rstrip(",;:- ")
    return cut + "…" if cut else v[:n]


def _items(b, key="items"):
    v = b.get(key)
    return [x for x in v if x] if isinstance(v, list) else []


def kind_of(b: dict) -> str | None:
    t = str(b.get("type") or "").strip().lower()
    t = ALIASES.get(t, t)
    return t if t in TYPES else None


def normalize_block(b) -> dict | None:
    if not isinstance(b, dict):
        return None
    t = kind_of(b)
    if not t:
        return None
    n = _normalizers[t](b)
    if n is None:
        return None
    n["type"] = t
    return n


def _headline(b):
    t = _s(b.get("text"), BUDGET["headline"])
    return {"text": t, "sub": _s(b.get("sub"), BUDGET["caption"])} if t else None


def _stat(b):
    v, l = _s(b.get("value"), BUDGET["stat_value"]), _s(b.get("label"), BUDGET["stat_label"])
    return {"value": v, "label": l, "note": _s(b.get("note"), BUDGET["stat_note"])} if v and l else None


def _stat_row(b):
    items = _items(b)
    if not items and b.get("value"):
        items = [b]
    out = []
    for it in items:
        s = _stat(it) if isinstance(it, dict) else None
        if s:
            out.append(s)
    lo, hi = LIMIT["stat_row"]
    return {"items": out[:hi]} if len(out) >= lo else None


def _steps(b):
    out = []
    for it in _items(b):
        if isinstance(it, str):
            it = {"title": it}
        if isinstance(it, dict):
            t = _s(it.get("title") or it.get("label"), BUDGET["step_title"])
            if t:
                out.append({"title": t, "body": _s(it.get("body") or it.get("description") or it.get("detail"), BUDGET["step_body"])})
    lo, hi = LIMIT["steps"]
    return {"items": out[:hi]} if len(out) >= lo else None


def _diagram(b):
    nodes, ids = [], set()
    for i, n in enumerate(_items(b, "nodes") or _items(b, "items") or _items(b, "stages")):
        if isinstance(n, str):
            n = {"label": n}
        if not isinstance(n, dict):
            continue
        label = _s(n.get("label") or n.get("title") or n.get("name"), BUDGET["node_label"])
        if not label:
            continue
        nid = str(n.get("id") or f"n{i}")
        if nid in ids:
            continue
        ids.add(nid)
        nodes.append({"id": nid, "label": label, "detail": _s(n.get("detail") or n.get("description") or n.get("body"), BUDGET["node_detail"])})
    nodes = nodes[:LIMIT["diagram"][1]]
    if len(nodes) < 2:
        return None
    ids = {n["id"] for n in nodes}
    edges = []
    for e in _items(b, "edges"):
        if isinstance(e, dict):
            a, c = str(e.get("from", "")), str(e.get("to", ""))
            if a in ids and c in ids and a != c:
                edges.append({"from": a, "to": c, "label": _s(e.get("label"), 24)})
    if not edges:  # an explicit chain only when the author gave no edges (a plain sequence)
        edges = [{"from": nodes[i]["id"], "to": nodes[i + 1]["id"], "label": ""} for i in range(len(nodes) - 1)]
    return {"nodes": nodes, "edges": edges[:14], "caption": _s(b.get("caption"), BUDGET["caption"])}


def _timeline(b):
    out = []
    for it in _items(b):
        if isinstance(it, dict):
            t = _s(it.get("title") or it.get("label"), BUDGET["tl_title"])
            if t:
                out.append({"when": _s(it.get("when") or it.get("date") or it.get("year"), BUDGET["tl_when"]), "title": t,
                            "body": _s(it.get("body") or it.get("description"), BUDGET["tl_body"])})
    lo, hi = LIMIT["timeline"]
    return {"items": out[:hi]} if len(out) >= lo else None


def _table(b):
    hdr = [_s(h, BUDGET["cell"]) for h in (b.get("headers") or [])][:4]
    rows = []
    for r in (b.get("rows") or []):
        if isinstance(r, list) and any(str(c).strip() for c in r):
            rows.append([_s(c, BUDGET["cell"]) for c in (list(r) + [""] * len(hdr))[:len(hdr)]])
    return {"headers": hdr, "rows": rows[:6]} if len(hdr) >= 2 and sum(1 for h in hdr if h) >= 2 and rows else None


def _matrix(b):
    q = [x for x in _items(b, "quadrants") if isinstance(x, dict) and str(x.get("title", "")).strip()]
    if len(q) != 4:
        return None
    return {"x_label": _s(b.get("x_label"), 30), "y_label": _s(b.get("y_label"), 30),
            "quadrants": [{"title": _s(x["title"], BUDGET["quad_title"]), "body": _s(x.get("body"), BUDGET["quad_body"])} for x in q]}


def _chart(b):
    labels = [_s(l, 22) for l in (b.get("labels") or [])][:10]
    series = []
    for s in (b.get("series") or []):
        if isinstance(s, dict) and isinstance(s.get("values"), list):
            try:
                vals = [float(v) for v in s["values"]][:len(labels)]
            except (TypeError, ValueError):
                continue
            if len(vals) == len(labels):
                series.append({"name": _s(s.get("name"), 24), "values": vals})
    if not series and isinstance(b.get("values"), list):
        try:
            vals = [float(v) for v in b["values"]][:len(labels)]
            if len(vals) == len(labels):
                series = [{"name": "", "values": vals}]
        except (TypeError, ValueError):
            pass
    kind = str(b.get("kind") or b.get("chart_type") or "bar").lower()
    kind = kind if kind in ("bar", "line", "pie", "donut", "hbar") else "bar"
    if len(labels) < 2 or not series:
        return None
    if kind in ("pie", "donut"):
        series = series[:1]
        if any(v < 0 for v in series[0]["values"]):
            return None
    return {"kind": kind, "labels": labels, "series": series[:3], "title": _s(b.get("title"), 70), "unit": _s(b.get("unit"), 10),
            "source": _s(b.get("source"), 80)}


def _cards(b):
    out = []
    for it in _items(b):
        if isinstance(it, dict):
            t = _s(it.get("title") or it.get("label"), BUDGET["card_title"])
            if t:
                out.append({"title": t, "body": _s(it.get("body") or it.get("description"), BUDGET["card_body"]),
                            "tag": _s(it.get("tag") or it.get("badge"), 18)})
    lo, hi = LIMIT["cards"]
    return {"items": out[:hi]} if len(out) >= lo else None


def _callout(b):
    t = _s(b.get("text"), BUDGET["callout"])
    return {"text": t, "label": _s(b.get("label"), 24)} if t else None


def _quote(b):
    t = _s(b.get("text"), BUDGET["quote"])
    return {"text": t, "by": _s(b.get("by") or b.get("source"), 60)} if t else None


def _image(b):
    src = b.get("src") or b.get("image")
    if isinstance(src, str):
        src = {"url": src}
    if not isinstance(src, dict) or not (src.get("url") or src.get("image_url") or src.get("asset_id")):
        return None
    return {"src": src, "caption": _s(b.get("caption"), BUDGET["caption"]), "alt": _s(b.get("alt"), 120)}


def _bullets(b):
    out = [_s(x if isinstance(x, str) else (x or {}).get("text", ""), BUDGET["bullet"]) for x in _items(b)]
    out = [x for x in out if x]
    lo, hi = LIMIT["bullets"]
    return {"items": out[:hi]} if len(out) >= lo else None


_normalizers = {"headline": _headline, "stat": _stat, "stat_row": _stat_row, "steps": _steps, "diagram": _diagram,
                "timeline": _timeline, "comparison_table": _table, "matrix_2x2": _matrix, "chart": _chart, "cards": _cards,
                "callout": _callout, "quote": _quote, "image": _image, "bullets": _bullets}


def normalize_blocks(raw) -> list[dict]:
    out = []
    for b in (raw if isinstance(raw, list) else []):
        n = normalize_block(b)
        if n:
            out.append(n)
    return out[:4]


def block_text(b: dict) -> str:
    """All human-visible text of a block (used by validators for number tracing and filler checks)."""
    parts = []

    def walk(v):
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, dict):
            for k, x in v.items():
                if k not in ("type", "id", "kind", "src", "from", "to"):
                    walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            parts.append(str(v))

    walk(b)
    return " ".join(parts)
