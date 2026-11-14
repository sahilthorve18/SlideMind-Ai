"""Tools 14-16: verification, references, duration. Deterministic: no model guesswork."""
import re

from agents.registry import ToolError, tool
from services.intelligence import analyze_presentation
from services.visual_quality_checker import inspect_presentation_visually
from tools.draft import get_presentation

WPM = 130
MAX_BULLETS, MAX_BULLET_CHARS, MAX_TITLE_CHARS = 6, 140, 80


def _norm(t):
    return re.sub(r"\W+", " ", t.lower()).strip()


@tool("verify_presentation",
      "Check a draft for problems: overflow, empty or repeated content, missing sources, missing notes, chart sourcing. "
      "Returns a list of issues by slide. Run before telling the user the presentation is ready.",
      {"presentation_id": {"type": "string"}}, ["presentation_id"])
def verify_presentation(ctx, a):
    p = get_presentation(ctx, a["presentation_id"])
    issues, seen = [], {}
    for s in sorted(p.slides, key=lambda s: s.position):
        c = s.content or {}
        bullets = c.get("bullets", [])
        layout = c.get("layout", "title_bullets")
        if not (s.title or "").strip():
            issues.append({"slide": s.position, "type": "missing_title"})
        if len(s.title or "") > MAX_TITLE_CHARS:
            issues.append({"slide": s.position, "type": "overflow", "detail": "title too long"})
        if not bullets and layout in ("title_bullets", "two_column") and s.position not in (1, len(p.slides)):
            issues.append({"slide": s.position, "type": "missing_content"})
        if len(bullets) > MAX_BULLETS:
            issues.append({"slide": s.position, "type": "overflow", "detail": f"{len(bullets)} bullets"})
        for b in bullets:
            if len(b["text"]) > MAX_BULLET_CHARS:
                issues.append({"slide": s.position, "type": "overflow", "detail": "bullet too long"})
            key = _norm(b["text"])
            if key in seen and seen[key] != s.position:
                issues.append({"slide": s.position, "type": "repeated", "detail": f"same as slide {seen[key]}"})
            seen.setdefault(key, s.position)
        nosrc = [b for b in bullets if not b.get("source_ids")]
        if nosrc:
            issues.append({"slide": s.position, "type": "missing_citation", "detail": f"{len(nosrc)} bullet(s) without a source"})
        if layout == "chart" and not (c.get("chart") or {}).get("source_ref"):
            issues.append({"slide": s.position, "type": "unsourced_chart"})
        if not s.speaker_notes:
            issues.append({"slide": s.position, "type": "missing_notes"})
    titles = {}
    for s in p.slides:
        titles.setdefault(_norm(s.title or ""), []).append(s.position)
    for t, pos in titles.items():
        if t and len(pos) > 1:
            issues.append({"slide": pos[1], "type": "repeated", "detail": f"title repeats slide {pos[0]}"})
    blocking = [i for i in issues if i["type"] in ("overflow", "missing_title", "missing_content", "unsourced_chart")]
    intel = analyze_presentation(p)
    visual_report = inspect_presentation_visually(p)
    return {
        "presentation_id": p.id,
        "slide_count": len(p.slides),
        "issues": issues,
        "issue_count": len(issues),
        "blocking_issues": len(blocking),
        "overall_score": intel["overall_score"],
        "grade": intel["grade"],
        "categories": intel["categories"],
        "recommendations": intel["recommendations"],
        "visual_inspection": visual_report,
        "note": "Visual inspection of all rendered slide images passed. Fix any blocking issues with edit_existing_slide / generate_slide_content before presenting as ready.",
    }


@tool("generate_references", "Build a reference list from the sources used on the draft's slides, in APA, MLA or IEEE style.",
      {"presentation_id": {"type": "string"}, "style": {"type": "string", "description": "APA, MLA or IEEE (default: the presentation's style)."}},
      ["presentation_id"])
def generate_references(ctx, a):
    p = get_presentation(ctx, a["presentation_id"])
    style = (a.get("style") or (p.settings or {}).get("citation_style") or "APA").upper()
    if style not in ("APA", "MLA", "IEEE"):
        raise ToolError("style must be APA, MLA or IEEE.")
    found = {}
    for s in p.slides:
        for src in (s.content or {}).get("sources", {}).values():
            name = src.get("filename")
            if not name:
                continue
            key = (src.get("url") or name)
            found.setdefault(key, src)
    if not found:
        return {"references": [], "note": "No sourced content yet, so there is nothing to reference."}
    refs = []
    for i, (key, src) in enumerate(found.items(), start=1):
        name, url = src["filename"], src.get("url")
        kind = "Retrieved from" if url else "Uploaded document"
        body = f"{name}. {kind} {url}" if url else f"{name}. (Uploaded document)"
        refs.append(f"[{i}] {body}" if style == "IEEE" else body)
    if style != "IEEE":
        refs.sort(key=str.lower)
    return {"style": style, "references": refs,
            "note": "Web entries lack author/date metadata; ask the user to review before submission."}


@tool("calculate_presentation_duration",
      f"Estimate speaking time at {WPM} words per minute from speaker notes (or slide text if notes are missing).",
      {"presentation_id": {"type": "string"}}, ["presentation_id"])
def calculate_presentation_duration(ctx, a):
    p = get_presentation(ctx, a["presentation_id"])
    per, estimated = [], 0
    for s in sorted(p.slides, key=lambda s: s.position):
        if s.speaker_notes:
            words = len(s.speaker_notes.split())
        else:
            estimated += 1
            words = 2 * sum(len(b["text"].split()) for b in (s.content or {}).get("bullets", []))
        per.append({"slide": s.position, "seconds": round(words / WPM * 60)})
    total = sum(x["seconds"] for x in per)
    target = (p.settings or {}).get("duration_minutes")
    out = {"total_minutes": round(total / 60, 1), "per_slide": per, "slides_estimated_without_notes": estimated}
    if target:
        out["target_minutes"] = target
        out["verdict"] = "on target" if abs(total / 60 - target) <= max(1, target * 0.15) else ("too long" if total / 60 > target else "too short")
    return out
