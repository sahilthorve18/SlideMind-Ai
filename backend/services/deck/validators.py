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
    r"(?<![\w.])(\d[\d,]*(?:\.\d+)?(?:\s*(?:percent|pct|thousand|million|billion|trillion)\b|[%xX+]|(?:bn|mn|mm|[kmbt])(?![a-zA-Z0-9_]))?)(?![\w])",
    re.I,
)
_NUM_MULT = {
    "k": 1e3, "thousand": 1e3,
    "m": 1e6, "mn": 1e6, "mm": 1e6, "million": 1e6,
    "b": 1e9, "bn": 1e9, "billion": 1e9,
    "t": 1e12, "trillion": 1e12,
}
_DOC_ATTRIBUTION_RE = re.compile(
    r"\b("
    r"per the (?:document|report|pdf|file|paper|source|slides?|text)|"
    r"according to (?:the )?(?:document|report|pdf|file|source|study|company)|"
    r"from the (?:document|report|pdf|file|source)|"
    r"revenue|arr|mrr|ebitda|profit margin|valuation|headcount|burn rate|"
    r"our (?:company|team|product|customers|users)|this (?:company|quarter|fiscal year)"
    r")\b",
    re.I,
)
MAX_GENERAL_NUMERIC_FACTS = 2


def _norm_num(s: str) -> str:
    raw = str(s).strip().lower().replace(",", "").rstrip(".")
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(percent|pct|thousand|million|billion|trillion|bn|mn|mm|[%kmbtx+])?", raw)
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
    - Expands suffixes/words by value (2.5M == 2.5 million, $10bn == $10B, $1.2k == $1,200, 30% == 30 percent).
    - Ties passage citations strictly to the cited passage's own text (p_map[src]).
    - When documents/web exist, drops numeric 'general' claims with document/proprietary phrasing, caps non-doc numeric
      general facts at MAX_GENERAL_NUMERIC_FACTS (2), and marks them unverified=True."""
    p_map = {p.get("id"): p.get("text", "") for p in (passages or []) if isinstance(p, dict) and p.get("id")}
    per_passage_pools = {pid: {_norm_num(m) for m in NUM.findall(txt)} for pid, txt in p_map.items()}
    all_passage_pool = set().union(*per_passage_pools.values()) if per_passage_pools else set()
    user_pool = {_norm_num(m) for m in NUM.findall(user_text or "")}
    web_pool = {_norm_num(m) for m in NUM.findall(web or "")}
    combined_pool = user_pool | all_passage_pool | web_pool
    has_material = bool(p_map or (web and web.strip()))

    kept = []
    general_numeric_count = 0
    for f in facts:
        src = str(f.get("source") or "general").strip()
        text = f"{f.get('claim', '')} {f.get('number') or ''}"
        nums = untraced_numbers(text, set(), allow_small=True)
        if nums:
            norm_nums = [_norm_num(x) for x in nums]
            if src == "general":
                if has_material:
                    if _DOC_ATTRIBUTION_RE.search(text):
                        log.warning("Dropped ungrounded fact (source=general, reason=document/proprietary wording): %s", f.get("claim", "")[:140])
                        continue
                    if any(n not in combined_pool for n in norm_nums):
                        if general_numeric_count >= MAX_GENERAL_NUMERIC_FACTS:
                            log.warning("Dropped ungrounded fact (source=general, reason=general numeric cap reached): %s", f.get("claim", "")[:140])
                            continue
                        general_numeric_count += 1
                        f = {**f, "unverified": True}
            else:
                drop_reason = None
                if src == "user":
                    if any(n not in user_pool for n in norm_nums):
                        drop_reason = "not in user request"
                elif src == "W":
                    if any(n not in web_pool for n in norm_nums):
                        drop_reason = "not in web text"
                elif src in per_passage_pools:
                    if any(n not in per_passage_pools[src] for n in norm_nums):
                        drop_reason = f"not in cited passage {src}"
                else:
                    if any(n not in combined_pool for n in norm_nums):
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
