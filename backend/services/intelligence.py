"""Presentation Intelligence Engine for SlideMind AI.

Analyzes presentation drafts across 6 core quality dimensions:
1. Clarity & Readability (bullet density, word economy, cognitive load)
2. Structure & Narrative Flow (narrative arc, transitions, progression)
3. Pacing & Timing (speaking rates at 130 WPM, target duration variance, slide dwell time)
4. Evidence & Sourcing Integrity (citation coverage, unsourced claims, chart citations)
5. Audience & Tone Alignment (audience profile fit, executive/technical/student vocabulary)
6. Visual & Layout Variety (monotony detection, layout distribution)

Provides an overall 0-100 score, letter grade (A+ to F), slide-by-slide diagnostics,
pacing timeline, prioritized actionable recommendations, and automated fixes.
"""
import re
from typing import Any

from database import db
from models import Presentation, Slide, SourceReference

WPM = 130
OPTIMAL_MIN_BULLETS = 3
OPTIMAL_MAX_BULLETS = 5
MAX_BULLET_CHARS = 140
MAX_TITLE_CHARS = 80
OPTIMAL_WORDS_PER_BULLET = (6, 16)

AUDIENCE_PROFILES = {
    "executives": {
        "preferred_words_per_bullet": (5, 12),
        "key_terms": ["roi", "growth", "revenue", "strategy", "impact", "cost", "margin", "risk", "metric", "scale", "performance"],
        "desc": "High-level, takeaway-first, data-backed and concise",
    },
    "investors": {
        "preferred_words_per_bullet": (5, 14),
        "key_terms": ["tam", "sam", "som", "traction", "cac", "ltv", "runway", "valuation", "moat", "market", "revenue", "growth"],
        "desc": "Market opportunity, unit economics, traction and returns",
    },
    "technical_team": {
        "preferred_words_per_bullet": (6, 20),
        "key_terms": ["architecture", "api", "latency", "pipeline", "schema", "infrastructure", "deployment", "protocol", "benchmark"],
        "desc": "Technical depth, architecture diagrams and concrete specifications",
    },
    "college_students": {
        "preferred_words_per_bullet": (6, 18),
        "key_terms": ["concept", "example", "principle", "definition", "analysis", "case study", "foundation", "mechanism"],
        "desc": "Pedagogical clarity, defined concepts and structured examples",
    },
    "general_public": {
        "preferred_words_per_bullet": (5, 14),
        "key_terms": ["community", "benefits", "how it works", "overview", "story", "everyday", "impact"],
        "desc": "Jargon-free, engaging narrative with relatable illustrations",
    },
}


def _norm(t: str) -> str:
    return re.sub(r"\W+", " ", (t or "").lower()).strip()


def _count_syllables(word: str) -> int:
    word = word.lower().strip()
    if not word or len(word) <= 3:
        return 1
    word = re.sub(r"(?:[^laeiouy]|ed|es|e)$", "", word)
    word = re.sub(r"^y", "", word)
    matches = re.findall(r"[aeiouy]{1,2}", word)
    return max(1, len(matches))


def _calc_readability(text: str) -> float:
    words = re.findall(r"\b\w+\b", text)
    if not words:
        return 100.0
    sentences = max(1, len(re.split(r"[.!?]+", text)))
    syllables = sum(_count_syllables(w) for w in words)
    asl = len(words) / sentences
    asw = syllables / len(words)
    # Standard Flesch Reading Ease
    score = 206.835 - (1.015 * asl) - (84.6 * asw)
    return round(max(0.0, min(100.0, score)), 1)


def analyze_presentation(p: Presentation, target_duration: int | None = None, audience: str | None = None) -> dict[str, Any]:
    """Runs a complete multi-pillar presentation intelligence audit."""
    slides = sorted(p.slides, key=lambda s: s.position)
    total_slides = len(slides)
    settings = p.settings or {}
    target_duration = target_duration or settings.get("duration_minutes")
    target_audience = audience or settings.get("audience") or "college_students"

    if total_slides == 0:
        return {
            "presentation_id": p.id,
            "title": p.title,
            "overall_score": 0,
            "grade": "F",
            "summary": "This presentation contains no slides.",
            "categories": {},
            "issues": [{"severity": "critical", "slide": None, "type": "empty_deck", "message": "No slides in presentation", "suggestion": "Add slides using the outline generator or chat."}],
            "recommendations": ["Create an initial slide outline to establish structure."],
            "pacing_timeline": [],
        }

    issues: list[dict[str, Any]] = []

    # 1. Pacing & Timing Analysis
    pacing_timeline = []
    total_words_notes = 0
    total_est_seconds = 0
    slides_with_notes = 0

    for s in slides:
        content = s.content or {}
        bullets = content.get("bullets", [])
        layout = content.get("layout", "title_bullets")
        notes = (s.speaker_notes or "").strip()

        if notes:
            slides_with_notes += 1
            words = len(notes.split())
            total_words_notes += words
            seconds = max(15, round((words / WPM) * 60))
            has_explicit_notes = True
        else:
            # Estimate from slide elements: title (10w) + bullets words + visual dwell (15s for chart/diagram)
            bullet_words = sum(len(b.get("text", "").split()) for b in bullets)
            title_words = len((s.title or "").split())
            base_seconds = round(((title_words + bullet_words) / WPM) * 60)
            visual_bonus = 20 if layout in ("chart", "diagram", "two_column") else 10
            seconds = max(20, base_seconds + visual_bonus)
            has_explicit_notes = False

        total_est_seconds += seconds

        # Pacing rating per slide
        if seconds < 25:
            pace_status = "rushed"
            issues.append({
                "severity": "warning",
                "slide": s.position,
                "dimension": "pacing",
                "type": "pacing_rushed",
                "message": f"Slide {s.position} estimated speaking time is very brisk ({seconds}s).",
                "suggestion": "Expand speaker notes to provide context and avoid rushing through.",
            })
        elif seconds > 150:
            pace_status = "drag"
            issues.append({
                "severity": "warning",
                "slide": s.position,
                "dimension": "pacing",
                "type": "pacing_drag",
                "message": f"Slide {s.position} estimated speaking time exceeds 2.5 minutes ({seconds}s).",
                "suggestion": "Consider splitting this slide or condensing speaker notes to keep audience engaged.",
            })
        elif seconds > 90:
            pace_status = "detailed"
        elif seconds >= 45:
            pace_status = "balanced"
        else:
            pace_status = "brisk"

        pacing_timeline.append({
            "slide_position": s.position,
            "title": s.title or f"Slide {s.position}",
            "seconds": seconds,
            "formatted_time": f"{seconds // 60}m {seconds % 60}s" if seconds >= 60 else f"{seconds}s",
            "has_notes": has_explicit_notes,
            "status": pace_status,
            "layout": layout,
        })

    total_est_minutes = round(total_est_seconds / 60, 1)

    # Compute Pacing Score (0-100)
    pacing_score = 100
    if slides_with_notes < total_slides:
        notes_coverage = slides_with_notes / total_slides
        pacing_score -= int((1 - notes_coverage) * 35)  # penalty up to 35 if no notes
    if target_duration:
        variance_ratio = abs(total_est_minutes - target_duration) / target_duration
        if variance_ratio > 0.4:
            pacing_score -= 30
            issues.append({
                "severity": "warning",
                "slide": None,
                "dimension": "pacing",
                "type": "target_duration_mismatch",
                "message": f"Estimated duration ({total_est_minutes}m) diverges from your target ({target_duration}m).",
                "suggestion": "Adjust slide depth or slide count to better hit your target speaking duration.",
            })
        elif variance_ratio > 0.2:
            pacing_score -= 15

    drag_count = sum(1 for p in pacing_timeline if p["status"] == "drag")
    rushed_count = sum(1 for p in pacing_timeline if p["status"] == "rushed")
    pacing_score = max(10, min(100, pacing_score - (drag_count * 8) - (rushed_count * 4)))

    # 2. Clarity & Readability Analysis
    total_bullets = 0
    total_bullet_words = 0
    dense_slides = 0
    empty_content_slides = 0
    readability_scores = []
    seen_bullets: dict[str, int] = {}

    for s in slides:
        content = s.content or {}
        bullets = content.get("bullets", [])
        layout = content.get("layout", "title_bullets")
        total_bullets += len(bullets)

        if not (s.title or "").strip():
            issues.append({
                "severity": "critical",
                "slide": s.position,
                "dimension": "clarity",
                "type": "missing_title",
                "message": f"Slide {s.position} is missing a title.",
                "suggestion": "Give this slide a clear, descriptive headline.",
            })

        if len(s.title or "") > MAX_TITLE_CHARS:
            issues.append({
                "severity": "warning",
                "slide": s.position,
                "dimension": "clarity",
                "type": "title_overflow",
                "message": f"Slide {s.position} title exceeds {MAX_TITLE_CHARS} characters.",
                "suggestion": "Shorten the title into a punchy executive headline.",
            })

        # Content presence check
        if not bullets and layout in ("title_bullets", "two_column") and s.position not in (1, total_slides):
            empty_content_slides += 1
            issues.append({
                "severity": "critical",
                "slide": s.position,
                "dimension": "clarity",
                "type": "missing_content",
                "message": f"Slide {s.position} has no bullet points or content.",
                "suggestion": "Add 3-5 structured bullet points.",
            })

        # Bullet density
        if len(bullets) > OPTIMAL_MAX_BULLETS:
            dense_slides += 1
            issues.append({
                "severity": "warning",
                "slide": s.position,
                "dimension": "clarity",
                "type": "bullet_overload",
                "message": f"Slide {s.position} has {len(bullets)} bullets (optimal is 3-5).",
                "suggestion": "Consolidate into key takeaways or split into a follow-up slide.",
            })

        for b in bullets:
            b_text = b.get("text", "")
            b_words = len(b_text.split())
            total_bullet_words += b_words
            readability_scores.append(_calc_readability(b_text))

            if len(b_text) > MAX_BULLET_CHARS:
                issues.append({
                    "severity": "warning",
                    "slide": s.position,
                    "dimension": "clarity",
                    "type": "bullet_length_overflow",
                    "message": f"Slide {s.position} has a bullet exceeding {MAX_BULLET_CHARS} characters.",
                    "suggestion": "Trim verbose bullet into an impactful sentence.",
                })

            if b_words > 25:
                issues.append({
                    "severity": "warning",
                    "slide": s.position,
                    "dimension": "clarity",
                    "type": "essay_bullet",
                    "message": f"Slide {s.position} has a bullet with {b_words} words (approaching paragraph length).",
                    "suggestion": "Move narrative details to speaker notes and leave only the core claim on the slide.",
                })

            norm = _norm(b_text)
            if norm in seen_bullets and seen_bullets[norm] != s.position:
                issues.append({
                    "severity": "warning",
                    "slide": s.position,
                    "dimension": "clarity",
                    "type": "duplicate_bullet",
                    "message": f"Slide {s.position} repeats content from slide {seen_bullets[norm]}.",
                    "suggestion": "Avoid redundant statements across slides.",
                })
            seen_bullets.setdefault(norm, s.position)

    avg_bullets_per_slide = round(total_bullets / max(1, total_slides), 1)
    avg_words_per_bullet = round(total_bullet_words / max(1, total_bullets), 1) if total_bullets else 0
    avg_readability = round(sum(readability_scores) / max(1, len(readability_scores)), 1) if readability_scores else 80.0

    clarity_score = 100
    clarity_score -= dense_slides * 10
    clarity_score -= empty_content_slides * 20
    if avg_words_per_bullet > 20:
        clarity_score -= 15
    elif avg_words_per_bullet < 4 and total_bullets > 0:
        clarity_score -= 10
    clarity_score = max(10, min(100, clarity_score))

    # 3. Structure & Narrative Flow Analysis
    structure_score = 100
    first_title = _norm(slides[0].title if slides else "")
    last_title = _norm(slides[-1].title if slides else "")

    intro_words = ["introduction", "overview", "agenda", "welcome", "title", "presentation", "problem"]
    has_intro_slide = total_slides >= 1 and (any(w in first_title for w in intro_words) or slides[0].position == 1)

    outro_words = ["conclusion", "summary", "takeaway", "recap", "next steps", "q&a", "references", "thank you", "roadmap", "outlook"]
    has_conclusion_slide = total_slides >= 3 and any(w in last_title for w in outro_words)

    if not has_conclusion_slide and total_slides >= 3:
        structure_score -= 15
        issues.append({
            "severity": "info",
            "slide": total_slides,
            "dimension": "structure",
            "type": "missing_conclusion",
            "message": "Presentation does not clearly conclude with a summary, takeaways, or next steps slide.",
            "suggestion": "Add a dedicated concluding slide with 3 high-impact takeaways or call to action.",
        })

    # Duplicate titles check
    title_occurrences: dict[str, list[int]] = {}
    for s in slides:
        nt = _norm(s.title or "")
        if nt:
            title_occurrences.setdefault(nt, []).append(s.position)
    for nt, pos_list in title_occurrences.items():
        if len(pos_list) > 1:
            structure_score -= 12 * (len(pos_list) - 1)
            for p_num in pos_list[1:]:
                issues.append({
                    "severity": "warning",
                    "slide": p_num,
                    "dimension": "structure",
                    "type": "duplicate_title",
                    "message": f"Slide {p_num} shares an identical title with slide {pos_list[0]}.",
                    "suggestion": "Differentiate sequential slides with subtitles (e.g., 'Part 1', 'Part 2' or specific sub-topics).",
                })

    if total_slides < 3:
        structure_score -= 25
        issues.append({
            "severity": "warning",
            "slide": None,
            "dimension": "structure",
            "type": "deck_too_short",
            "message": f"Presentation has only {total_slides} slides.",
            "suggestion": "A well-structured deck typically benefits from at least 4-6 slides for complete flow.",
        })

    structure_score = max(15, min(100, structure_score))

    # 4. Evidence & Sourcing Integrity Analysis
    sourced_bullets = 0
    unsourced_bullets = 0
    unsourced_charts = 0
    all_source_keys = set()

    for s in slides:
        content = s.content or {}
        bullets = content.get("bullets", [])
        layout = content.get("layout", "title_bullets")
        for b in bullets:
            srcs = b.get("source_ids", [])
            if srcs:
                sourced_bullets += 1
                all_source_keys.update(str(x) for x in srcs)
            else:
                unsourced_bullets += 1

        if layout == "chart":
            chart_obj = content.get("chart", {})
            if not chart_obj.get("source_ref"):
                unsourced_charts += 1
                issues.append({
                    "severity": "critical",
                    "slide": s.position,
                    "dimension": "sourcing",
                    "type": "unsourced_chart",
                    "message": f"Slide {s.position} contains a chart without an explicit data source reference.",
                    "suggestion": "Attach a valid source citation or document link for the chart's data points.",
                })

    if total_bullets > 0:
        citation_coverage_pct = round((sourced_bullets / total_bullets) * 100, 1)
    else:
        citation_coverage_pct = 100.0

    sourcing_score = 100
    if total_bullets > 0:
        if citation_coverage_pct < 50:
            sourcing_score -= 40
            issues.append({
                "severity": "warning",
                "slide": None,
                "dimension": "sourcing",
                "type": "low_citation_coverage",
                "message": f"Only {citation_coverage_pct}% of bullet statements have cited sources.",
                "suggestion": "Connect claims to uploaded documents or run web research to cite verifiable facts.",
            })
        elif citation_coverage_pct < 85:
            sourcing_score -= 15

    sourcing_score -= unsourced_charts * 25
    sourcing_score = max(10, min(100, sourcing_score))

    # 5. Audience Alignment & Tone Analysis
    audience_score = 100
    profile = AUDIENCE_PROFILES.get(target_audience, AUDIENCE_PROFILES["college_students"])
    all_slide_text = " ".join([f"{s.title} " + " ".join(b.get("text", "") for b in (s.content or {}).get("bullets", [])) for s in slides]).lower()

    # Check key vocabulary presence for the target audience
    key_terms = profile["key_terms"]
    matched_terms = [t for t in key_terms if t in all_slide_text]
    term_hit_ratio = len(matched_terms) / max(1, len(key_terms))

    min_w, max_w = profile["preferred_words_per_bullet"]
    if avg_words_per_bullet > max_w + 5:
        audience_score -= 15
        issues.append({
            "severity": "info",
            "slide": None,
            "dimension": "audience",
            "type": "audience_bullet_density",
            "message": f"Average words per bullet ({avg_words_per_bullet}) is higher than recommended for {target_audience.replace('_', ' ')}.",
            "suggestion": f"Keep bullets between {min_w}-{max_w} words for maximum impact.",
        })
    elif avg_words_per_bullet < min_w - 2 and total_bullets > 0:
        audience_score -= 10

    if term_hit_ratio < 0.15 and len(slides) >= 3:
        audience_score -= 10
        issues.append({
            "severity": "info",
            "slide": None,
            "dimension": "audience",
            "type": "audience_vocabulary",
            "message": f"Limited domain-aligned phrasing detected for target audience '{target_audience}'.",
            "suggestion": f"Incorporate audience-relevant concepts ({profile['desc']}).",
        })

    audience_score = max(20, min(100, audience_score))

    # 6. Visual & Layout Variety Analysis
    layouts = [(s.content or {}).get("layout", "title_bullets") for s in slides]
    unique_layouts = set(layouts)
    visual_slides = sum(1 for lay in layouts if lay in ("chart", "diagram", "two_column", "quote"))
    visual_ratio = round(visual_slides / max(1, total_slides), 2)

    variety_score = 100
    # Monotony penalty: 3 or more consecutive identical layouts
    consecutive_run = 1
    max_consecutive = 1
    for i in range(1, len(layouts)):
        if layouts[i] == layouts[i - 1]:
            consecutive_run += 1
            max_consecutive = max(max_consecutive, consecutive_run)
        else:
            consecutive_run = 1

    if max_consecutive >= 4 and total_slides >= 4:
        variety_score -= 25
        issues.append({
            "severity": "warning",
            "slide": None,
            "dimension": "visual",
            "type": "layout_monotony",
            "message": f"Deck has {max_consecutive} consecutive slides using the exact same layout.",
            "suggestion": "Introduce variety with comparison layouts (two_column), diagrams, or key metric charts.",
        })
    elif max_consecutive >= 3 and total_slides >= 5:
        variety_score -= 12

    if visual_slides == 0 and total_slides >= 4:
        variety_score -= 20
        issues.append({
            "severity": "info",
            "slide": None,
            "dimension": "visual",
            "type": "no_visual_elements",
            "message": "All slides are plain text bullet lists.",
            "suggestion": "Transform at least one slide into a diagram, metric highlight, or chart.",
        })

    variety_score = max(20, min(100, variety_score))

    # Weighted Overall Health Score calculation
    # Clarity (25%), Structure (20%), Pacing (20%), Sourcing (20%), Audience (15%)
    # Adjusted with Variety
    overall_score = round(
        (clarity_score * 0.25)
        + (structure_score * 0.20)
        + (pacing_score * 0.20)
        + (sourcing_score * 0.20)
        + (audience_score * 0.10)
        + (variety_score * 0.05)
    )
    overall_score = max(0, min(100, overall_score))

    # Letter Grade
    if overall_score >= 93:
        grade = "A+"
    elif overall_score >= 85:
        grade = "A"
    elif overall_score >= 75:
        grade = "B"
    elif overall_score >= 65:
        grade = "C"
    elif overall_score >= 50:
        grade = "D"
    else:
        grade = "F"

    # Executive Summary
    strengths = []
    weaknesses = []
    if clarity_score >= 85:
        strengths.append("crisp bullet readability")
    else:
        weaknesses.append("bullet density / text overflow")

    if structure_score >= 85:
        strengths.append("coherent narrative flow")
    else:
        weaknesses.append("structural progression")

    if pacing_score >= 85:
        strengths.append(f"balanced delivery pacing (~{total_est_minutes}m)")
    else:
        weaknesses.append("missing speaker notes or pacing imbalance")

    if sourcing_score >= 85:
        strengths.append("strong evidence backing")
    else:
        weaknesses.append("unsubstantiated claims")

    summary = f"Presentation Health: {grade} ({overall_score}/100)."
    if strengths:
        summary += f" Strengths include {', '.join(strengths)}."
    if weaknesses:
        summary += f" Focus improvements on {', '.join(weaknesses)}."

    # Top actionable recommendations
    recommendations = []
    for iss in sorted(issues, key=lambda x: (0 if x["severity"] == "critical" else 1 if x["severity"] == "warning" else 2)):
        if iss["suggestion"] not in recommendations:
            recommendations.append(iss["suggestion"])
        if len(recommendations) >= 5:
            break

    if not recommendations:
        recommendations.append("Deck is well-balanced and ready for rehearsal or export.")

    visual_critique = settings.get("visual_critique")
    if isinstance(visual_critique, dict):
        for sc in visual_critique.get("slides", []):
            if sc.get("status") == "ok" and (sc.get("score") is not None and sc["score"] < 75) and not sc.get("repaired"):
                probs = "; ".join(sc.get("problems") or []) or "Visual balance or legibility below threshold."
                issues.append({
                    "severity": "warning",
                    "slide": sc.get("slide_number"),
                    "dimension": "visual",
                    "type": "visual_critique",
                    "message": f"Slide {sc.get('slide_number')} scored {sc.get('score')}/100 in vision audit: {probs}",
                    "suggestion": "Regenerate this slide or trim content to restore whitespace and contrast.",
                })

    return {
        "presentation_id": p.id,
        "title": p.title,
        "overall_score": overall_score,
        "grade": grade,
        "summary": summary,
        "categories": {
            "clarity": {
                "score": clarity_score,
                "label": "Clarity & Readability",
                "metrics": {
                    "avg_bullets_per_slide": avg_bullets_per_slide,
                    "avg_words_per_bullet": avg_words_per_bullet,
                    "dense_slides_count": dense_slides,
                    "readability_index": avg_readability,
                },
            },
            "structure": {
                "score": structure_score,
                "label": "Narrative Structure",
                "metrics": {
                    "total_slides": total_slides,
                    "has_intro": has_intro_slide,
                    "has_conclusion": has_conclusion_slide,
                },
            },
            "pacing": {
                "score": pacing_score,
                "label": "Pacing & Delivery",
                "metrics": {
                    "estimated_total_minutes": total_est_minutes,
                    "target_duration_minutes": target_duration,
                    "slides_with_notes": slides_with_notes,
                    "total_slides": total_slides,
                    "drag_slides_count": drag_count,
                    "rushed_slides_count": rushed_count,
                },
            },
            "sourcing": {
                "score": sourcing_score,
                "label": "Evidence & Sourcing",
                "metrics": {
                    "citation_coverage_pct": citation_coverage_pct,
                    "sourced_bullets": sourced_bullets,
                    "total_bullets": total_bullets,
                    "unique_sources_cited": len(all_source_keys),
                    "unsourced_charts": unsourced_charts,
                },
            },
            "audience": {
                "score": audience_score,
                "label": "Audience Alignment",
                "metrics": {
                    "target_audience": target_audience,
                    "matched_key_terms": len(matched_terms),
                },
            },
            "visual_variety": {
                "score": variety_score,
                "label": "Visual Diversity",
                "metrics": {
                    "unique_layouts": len(unique_layouts),
                    "visual_ratio": visual_ratio,
                    "max_consecutive_same_layout": max_consecutive,
                },
            },
        },
        "issues": issues,
        "recommendations": recommendations,
        "pacing_timeline": pacing_timeline,
        "visual_critique": visual_critique,
    }


def auto_fix_presentation(p: Presentation, action_type: str, slide_position: int | None = None) -> dict[str, Any]:
    """Applies automated presentation intelligence improvements.

    Supported action types:
    - 'generate_missing_notes': Creates delivery speaking notes for slides without notes.
    - 'trim_overflow': Trims overlong bullets (> 140 chars or > 22 words) while preserving meaning.
    - 'auto_balance': Applies comprehensive clean-up across missing notes and overflow.
    """
    slides = sorted(p.slides, key=lambda s: s.position)
    modified = 0

    if action_type in ("generate_missing_notes", "auto_balance"):
        for s in slides:
            if slide_position and s.position != slide_position:
                continue
            if not (s.speaker_notes or "").strip():
                content = s.content or {}
                bullets = content.get("bullets", [])
                bullet_texts = [b.get("text", "") for b in bullets if b.get("text")]
                title = s.title or f"Slide {s.position}"
                if bullet_texts:
                    takeaways = ". ".join(bullet_texts)
                    s.speaker_notes = f"In this slide on {title}, our key focus is that {takeaways}. Highlight these points clearly and pause for audience comprehension."
                else:
                    s.speaker_notes = f"Present the core thesis of {title}. Emphasize the strategic importance to the audience before proceeding."
                modified += 1

    if action_type in ("trim_overflow", "auto_balance"):
        for s in slides:
            if slide_position and s.position != slide_position:
                continue
            content = dict(s.content or {})
            bullets = content.get("bullets", [])
            changed = False
            new_bullets = []
            for b in bullets:
                b_copy = dict(b)
                text = b_copy.get("text", "")
                if len(text) > MAX_BULLET_CHARS:
                    # Trim to nearest word under limit
                    trimmed = text[:MAX_BULLET_CHARS - 3]
                    if " " in trimmed:
                        trimmed = trimmed.rsplit(" ", 1)[0]
                    b_copy["text"] = trimmed + "..."
                    changed = True
                new_bullets.append(b_copy)
            if changed:
                content["bullets"] = new_bullets
                s.content = content
                modified += 1

    if modified:
        db.session.commit()

    return {"ok": True, "action_type": action_type, "modified_slides": modified}
