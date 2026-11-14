"""Rehearsal Engine for SlideMind AI.

Analyzes verbal rehearsal delivery against slide content and speaker notes:
- Speaking pace (WPM) & pacing classification
- Filler word detection and frequency ('um', 'uh', 'like', 'you know', 'basically', etc.)
- Concept & key claim coverage against bullets and speaker notes
- Overall delivery score & personalized coaching feedback
- Slide-by-slide and full-deck rehearsal scorecard
"""
import re
from typing import Any

from database import db
from models import Presentation, Slide

WPM_OPTIMAL_MIN = 120
WPM_OPTIMAL_MAX = 150

FILLER_PATTERNS = [
    r"\bum\b", r"\buh\b", r"\ber\b", r"\bah\b", r"\blike\b", r"\byou know\b",
    r"\bbasically\b", r"\bactually\b", r"\bliterally\b", r"\bsort of\b", r"\bkind of\b",
    r"\bi mean\b",
]

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "as",
    "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "could",
    "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from", "further", "had",
    "has", "have", "having", "he", "her", "here", "hers", "herself", "him", "himself", "his", "how",
    "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me", "more", "most", "my", "myself",
    "no", "nor", "not", "now", "of", "off", "on", "once", "only", "or", "other", "our", "ours", "ourselves",
    "out", "over", "own", "s", "same", "she", "should", "so", "some", "such", "t", "than", "that", "the",
    "their", "theirs", "them", "themselves", "then", "there", "these", "they", "this", "those", "through",
    "to", "too", "under", "until", "up", "very", "was", "we", "were", "what", "when", "where", "which",
    "while", "who", "whom", "why", "will", "with", "would", "you", "your", "yours", "yourself",
}


def _clean_words(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"\b[a-zA-Z0-9_\-\$%\.]+\b", text or "")]


def _extract_keywords(text: str) -> set[str]:
    words = _clean_words(text)
    return {w for w in words if len(w) > 2 and w not in STOPWORDS and not w.isdigit()}


def analyze_slide_rehearsal(
    slide_title: str,
    bullets: list[str],
    speaker_notes: str,
    transcript: str,
    duration_seconds: int,
) -> dict[str, Any]:
    """Analyzes a practice transcript for a single slide."""
    spoken_words = _clean_words(transcript)
    word_count = len(spoken_words)
    dur = max(1, duration_seconds)
    wpm = round((word_count / dur) * 60)

    # 1. Pace Analysis
    if wpm > 170:
        pace_status = "too_fast"
        pace_score = max(30, 100 - int((wpm - 170) * 1.5))
    elif wpm > 150:
        pace_status = "energetic"
        pace_score = 90
    elif wpm >= 115:
        pace_status = "conversational"
        pace_score = 100
    elif wpm >= 90:
        pace_status = "steady"
        pace_score = 80
    else:
        pace_status = "too_slow"
        pace_score = max(20, int((wpm / 90) * 80))

    # 2. Filler Word Detection
    lower_transcript = (transcript or "").lower()
    filler_counts: dict[str, int] = {}
    total_fillers = 0
    for pat in FILLER_PATTERNS:
        matches = re.findall(pat, lower_transcript)
        if matches:
            label = pat.replace(r"\b", "")
            filler_counts[label] = len(matches)
            total_fillers += len(matches)

    filler_rate = round((total_fillers / max(1, word_count)) * 100, 1)
    if filler_rate <= 1.0:
        filler_score = 100
    elif filler_rate <= 2.5:
        filler_score = 85
    elif filler_rate <= 5.0:
        filler_score = 70
    elif filler_rate <= 8.0:
        filler_score = 50
    else:
        filler_score = max(15, 50 - int((filler_rate - 8.0) * 5))

    # 3. Content Coverage Analysis
    all_slide_concepts = set()
    for b in bullets:
        all_slide_concepts.update(_extract_keywords(b))
    if speaker_notes:
        all_slide_concepts.update(_extract_keywords(speaker_notes))

    spoken_concepts = set(_clean_words(transcript))
    if all_slide_concepts:
        matched_concepts = all_slide_concepts.intersection(spoken_concepts)
        coverage_pct = round((len(matched_concepts) / len(all_slide_concepts)) * 100, 1)
    else:
        coverage_pct = 100.0

    coverage_score = round(coverage_pct)

    # 4. Overall Slide Delivery Score
    overall_score = round((coverage_score * 0.40) + (pace_score * 0.30) + (filler_score * 0.30))
    overall_score = max(0, min(100, overall_score))

    # 5. Coaching Feedback Tips
    coaching_tips = []
    if pace_status == "too_fast":
        coaching_tips.append(f"Your speaking rate was fast ({wpm} WPM). Slow down and take deliberate pauses after key insights.")
    elif pace_status == "too_slow":
        coaching_tips.append(f"Your pace was slightly slow ({wpm} WPM). Increase energy to maintain audience engagement.")
    else:
        coaching_tips.append(f"Pacing is on point ({wpm} WPM) with natural conversational flow.")

    if total_fillers > 0:
        top_fillers = sorted(filler_counts.items(), key=lambda x: x[1], reverse=True)[:2]
        fillers_str = ", ".join(f"'{k}' ({v}x)" for k, v in top_fillers)
        coaching_tips.append(f"Detected {total_fillers} filler words ({fillers_str}). Practice replacing vocal fillers with silent pauses.")
    else:
        coaching_tips.append("Zero filler words detected — clean, articulate speech.")

    if coverage_pct < 65:
        coaching_tips.append(f"Coverage of key points was {coverage_pct}%. Review the slide bullets and speaker notes to hit all core takeaways.")
    else:
        coaching_tips.append(f"Strong content coverage ({coverage_pct}% of slide concepts articulated).")

    return {
        "slide_title": slide_title,
        "duration_seconds": duration_seconds,
        "word_count": word_count,
        "wpm": wpm,
        "pace_status": pace_status,
        "pace_score": pace_score,
        "total_fillers": total_fillers,
        "filler_rate_pct": filler_rate,
        "filler_breakdown": filler_counts,
        "filler_score": filler_score,
        "coverage_pct": coverage_pct,
        "coverage_score": coverage_score,
        "overall_score": overall_score,
        "coaching_tips": coaching_tips,
    }


def analyze_deck_rehearsal(
    presentation: Presentation,
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregates rehearsal runs across all slides into a comprehensive deck scorecard."""
    slides = sorted(presentation.slides, key=lambda s: s.position)
    slide_map = {s.position: s for s in slides}

    slide_results = []
    total_seconds = 0
    total_words = 0
    total_fillers = 0

    for run in runs:
        pos = run.get("slide_position")
        s = slide_map.get(pos)
        title = s.title if s else f"Slide {pos}"
        bullets = [b.get("text", "") for b in ((s.content or {}).get("bullets", []))] if s else []
        notes = s.speaker_notes if s else ""
        dur = int(run.get("duration_seconds", 30))
        tx = str(run.get("transcript", ""))

        res = analyze_slide_rehearsal(title, bullets, notes, tx, dur)
        res["slide_position"] = pos
        slide_results.append(res)

        total_seconds += dur
        total_words += res["word_count"]
        total_fillers += res["total_fillers"]

    total_minutes = round(total_seconds / 60, 1)
    overall_wpm = round((total_words / max(1, total_seconds)) * 60) if total_seconds else 0
    avg_score = round(sum(r["overall_score"] for r in slide_results) / max(1, len(slide_results)))

    # Letter grade
    if avg_score >= 93:
        grade = "A+"
    elif avg_score >= 85:
        grade = "A"
    elif avg_score >= 75:
        grade = "B"
    elif avg_score >= 65:
        grade = "C"
    else:
        grade = "D"

    target_duration = (presentation.settings or {}).get("duration_minutes")

    # High-level coaching summary
    summary_tips = []
    if target_duration:
        variance = round(abs(total_minutes - target_duration), 1)
        if variance <= target_duration * 0.15:
            summary_tips.append(f"Excellent time management: total rehearsal time of {total_minutes}m closely aligns with target {target_duration}m.")
        elif total_minutes > target_duration:
            summary_tips.append(f"Total time ({total_minutes}m) exceeded your target ({target_duration}m). Consider tightening transitions.")
        else:
            summary_tips.append(f"Total time ({total_minutes}m) is under target ({target_duration}m). Expand slightly on key examples.")

    if total_fillers > 5:
        summary_tips.append(f"Total filler words ({total_fillers}) can be reduced. Focus on pausing comfortably during slide changes.")

    weakest_slides = [r for r in slide_results if r["overall_score"] < 70]

    return {
        "presentation_id": presentation.id,
        "title": presentation.title,
        "overall_score": avg_score,
        "grade": grade,
        "total_minutes": total_minutes,
        "target_minutes": target_duration,
        "total_words": total_words,
        "overall_wpm": overall_wpm,
        "total_fillers": total_fillers,
        "slide_count": len(slide_results),
        "slide_results": slide_results,
        "weakest_slides": [w["slide_position"] for w in weakest_slides],
        "summary_tips": summary_tips,
    }
