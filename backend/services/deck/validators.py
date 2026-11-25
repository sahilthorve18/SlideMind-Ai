"""Hard checks on slide specs. A failure triggers one repair pass, then a safe fallback built only from real facts."""
import logging
import re

from .blocks import block_text, normalize_blocks

log = logging.getLogger(__name__)

PLANNING_WORDS = ("slide goal", "purpose:", "this slide will", "this slide shows", "talking point", "placeholder", "lorem", "tbd", "todo",
                  "insert ", "your text here", "example text", "[")
KNOWN_FILLER = ("10x", "99.4%", "0s friction", "slidemind next-gen", "design standard")
AUTO_LABEL = re.compile(r"\b(Pillar|Phase|Stage|Step|Point|Item|Feature)\s+\d\b", re.I)
NUM = re.compile(
    r"(?<![\w.])(\d[\d,]*(?:\.\d+)?(?:\s*(?:percent|pct|thousand|million|billion|trillion)\b|[%xX+]|[kmbtKMBT](?![a-zA-Z0-9_]))?)(?![\w])",
    re.I,
)
_NUM_MULT = {
    "k": 1e3, "thousand": 1e3,
    "m": 1e6, "million": 1e6,
    "b": 1e9, "billion": 1e9,
    "t": 1e12, "trillion": 1e12,
}


def _norm_num(s: str) -> str:
    raw = str(s).strip().lower().replace(",", "").rstrip(".")
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(percent|pct|thousand|million|billion|trillion|[%kmbtx+])?", raw)
    if not m:
        return raw.rstrip("%+.")
    val_str, suf = m.group(1), (m.group(2) or "").strip()
    if suf == "x":
        val = float(val_str)
        return f"{int(round(val))}x" if abs(val - round(val)) < 1e-6 else f"{val:g}x"
    val = float(val_str) * _NUM_MULT.get(suf, 1.0)
    if abs(val - round(val)) < 1e-6:
        return str(int(round(val)))
    return f"{val:g}"


def fact_number_pool(facts: list[dict], user_text: str = "") -> set[str]:
    pool = set()
    for f in facts:
        for src in (f.get("claim", ""), str(f.get("number") or "")):
            pool.update(_norm_num(m) for m in NUM.findall(src))
    pool.update(_norm_num(m) for m in NUM.findall(user_text or ""))
    return pool


def untraced_numbers(text: str, pool: set[str], allow_small: bool = True) -> list[str]:
    bad = []
    for m in NUM.findall(text):
        n = _norm_num(m)
        if allow_small and re.fullmatch(r"\d{1,2}", n) and int(n) <= 12:
            continue  # counts and ordinals ("3 roles", "step 2") derive from the structure itself
        if n not in pool:
            bad.append(m)
    return bad


def filter_grounded_facts(facts: list[dict], user_text: str, passages: list[dict], web: str) -> list[dict]:
    """Drop facts whose numbers (>12) contradict or spoof their attributed source ('user', exact 'P#' id, or 'W').
    Expands suffixes/words by value (e.g., 2.5M == 2.5 million, $1.2k == $1,200, 30% == 30 percent) and keeps 'general' facts."""
    p_map = {p.get("id"): p.get("text", "") for p in (passages or []) if isinstance(p, dict) and p.get("id")}
    all_passages = " ".join(p_map.values())
    user_pool = {_norm_num(m) for m in NUM.findall(user_text or "")}
    web_pool = {_norm_num(m) for m in NUM.findall(web or "")}
    passage_pool = {_norm_num(m) for m in NUM.findall(all_passages)}

    kept = []
    for f in facts:
        src = str(f.get("source") or "general").strip()
        text = f"{f.get('claim', '')} {f.get('number') or ''}"
        nums = untraced_numbers(text, set(), allow_small=True)
        if nums and src != "general":
            norm_nums = [_norm_num(x) for x in nums]
            drop_reason = None
            if src == "user":
                if any(n not in user_pool for n in norm_nums):
                    drop_reason = "not in user request"
            elif src == "W":
                if any(n not in web_pool for n in norm_nums):
                    drop_reason = "not in web text"
            elif src in p_map:
                if any(n not in passage_pool for n in norm_nums):
                    drop_reason = f"not in passage pool for {src}"
            else:
                if any(n not in (user_pool | passage_pool | web_pool) for n in norm_nums):
                    drop_reason = f"unrecognized source '{src}'"
            if drop_reason:
                log.warning("Dropped ungrounded fact (source=%s, reason=%s): %s", src, drop_reason, f.get("claim", "")[:140])
                continue
        kept.append(f)
    return kept


def validate_slide(spec: dict, facts: list[dict], user_text: str, source_text: str = "") -> list[str]:
    errors = []
    kind = spec.get("kind", "content")
    title = str(spec.get("title", "")).strip()
    if not title:
        errors.append("missing title")
    elif kind == "content" and len(title.split()) < 3:
        errors.append("title must be a full takeaway sentence, not a topic label")
    if len(title) > 95:
        errors.append("title longer than 95 characters")
    blocks = normalize_blocks(spec.get("blocks"))
    if kind == "content" and not blocks:
        errors.append("no block had its required fields filled (pick a block type the facts can support)")
    raw_n = len(spec.get("blocks") or [])
    if kind == "content" and raw_n and raw_n > len(blocks):
        errors.append(f"{raw_n - len(blocks)} block(s) were incomplete or invalid and were dropped")
    text = " ".join([title, spec.get("tagline", "") or ""] + [block_text(b) for b in blocks])
    low = text.lower()
    for w in PLANNING_WORDS:
        if w in low:
            errors.append(f"planning/placeholder text found: '{w.strip()}'")
    for w in KNOWN_FILLER:
        if w in low and w not in (user_text + " " + source_text).lower():
            errors.append(f"filler text not in the sources: '{w}'")
    m = AUTO_LABEL.search(text)
    if m and m.group(0).lower() not in (user_text + " " + source_text).lower():
        errors.append(f"auto-generated label '{m.group(0)}' (name the item from the facts)")
    pool = fact_number_pool(facts, user_text)
    bad = untraced_numbers(text, pool)
    if bad:
        errors.append("numbers not found in the fact sheet: " + ", ".join(sorted(set(bad))[:6]))
    for b in blocks:
        if b["type"] == "chart":
            for s in b["series"]:
                for v in s["values"]:
                    if _norm_num(f"{v:g}") not in pool:
                        errors.append(f"chart value {v:g} is not in the fact sheet")
                        break
    return errors
