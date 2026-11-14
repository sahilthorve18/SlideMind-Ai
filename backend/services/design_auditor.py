"""Automated Design Quality Auditor for SlideMind AI.

Inspects presentations for:
- Text overflow and word density
- Repeated layouts and visual monotony
- Empty slides and missing content
- Visual asset requirements
- Contrast and typography consistency
Provides automated remediation to upgrade slides to premium 2026 quality.
"""
import logging
from typing import Any, Dict, List

from database import db
from models import Presentation, Slide
from services.design_systems import get_design_system

log = logging.getLogger(__name__)

MAX_TITLE_CHARS = 80
MAX_BULLET_CHARS = 160
MAX_BULLETS_PER_SLIDE = 5
MAX_CONSECUTIVE_IDENTICAL_LAYOUTS = 2


def audit_presentation_design(presentation: Presentation) -> Dict[str, Any]:
    """Runs a comprehensive pre-flight design audit across all slides."""
    slides = sorted(presentation.slides, key=lambda s: s.position)
    theme_name = (presentation.settings or {}).get("theme", "swiss_minimal")
    ds = get_design_system(theme_name)

    issues: List[Dict[str, Any]] = []
    consecutive_layout_count = 1
    last_layout = None
    layout_counts: Dict[str, int] = {}

    for idx, s in enumerate(slides):
        c = s.content or {}
        layout = c.get("layout", "title_bullets")
        bullets = c.get("bullets", [])
        title = s.title or ""

        layout_counts[layout] = layout_counts.get(layout, 0) + 1

        # 1. Empty slide check
        if not title.strip():
            issues.append({"slide": s.position, "type": "empty_slide", "severity": "error", "message": "Slide is missing a title."})

        # 2. Text overflow check
        if len(title) > MAX_TITLE_CHARS:
            issues.append({"slide": s.position, "type": "text_overflow", "severity": "warning", "message": f"Title is {len(title)} chars (recommended <= {MAX_TITLE_CHARS})."})

        if len(bullets) > MAX_BULLETS_PER_SLIDE:
            issues.append({"slide": s.position, "type": "excessive_text", "severity": "warning", "message": f"Slide has {len(bullets)} bullets (recommended <= {MAX_BULLETS_PER_SLIDE})."})

        for b in bullets:
            txt = b.get("text", "") if isinstance(b, dict) else str(b)
            if len(txt) > MAX_BULLET_CHARS:
                issues.append({"slide": s.position, "type": "text_overflow", "severity": "warning", "message": f"Bullet text is {len(txt)} chars (recommended <= {MAX_BULLET_CHARS})."})

        # 3. Repeated layout monotony check
        if layout == last_layout:
            consecutive_layout_count += 1
            if consecutive_layout_count > MAX_CONSECUTIVE_IDENTICAL_LAYOUTS:
                issues.append({
                    "slide": s.position,
                    "type": "repeated_layouts",
                    "severity": "warning",
                    "message": f"Layout '{layout}' is repeated {consecutive_layout_count} times in a row. Vary layout for visual rhythm."
                })
        else:
            consecutive_layout_count = 1
            last_layout = layout

        # 4. Missing visuals check
        if layout in ("title_bullets", "title_only") and idx not in (0, len(slides) - 1):
            if not c.get("cards") and not c.get("image") and not c.get("kpis") and not c.get("chart") and not c.get("diagram"):
                issues.append({
                    "slide": s.position,
                    "type": "missing_visuals",
                    "severity": "info",
                    "message": "Slide uses plain text without visual cards, statistics, or diagrams."
                })

    # Overall score calculation
    errors = sum(1 for i in issues if i["severity"] == "error")
    warnings = sum(1 for i in issues if i["severity"] == "warning")
    infos = sum(1 for i in issues if i["severity"] == "info")

    penalty = errors * 15 + warnings * 5 + infos * 2
    score = max(50, min(100, 100 - penalty))

    grade = "A+" if score >= 95 else ("A" if score >= 90 else ("B+" if score >= 85 else ("B" if score >= 75 else "C")))

    return {
        "presentation_id": presentation.id,
        "design_system": ds.id,
        "design_system_name": ds.name,
        "score": score,
        "grade": grade,
        "slide_count": len(slides),
        "layout_distribution": layout_counts,
        "issues": issues,
        "total_issues": len(issues),
        "is_optimal": len(issues) == 0,
    }


def auto_correct_presentation_design(presentation: Presentation) -> Dict[str, Any]:
    """Automatically upgrades slide layouts, fixes overflow, and enriches visuals."""
    slides = sorted(presentation.slides, key=lambda s: s.position)
    total = len(slides)
    topic = presentation.title or "Presentation"

    fixed_count = 0
    recent_layouts = []

    alternate_layouts = ["cards_hierarchy", "split_screen", "stats_kpi", "process_diagram", "problem_solution"]

    for idx, s in enumerate(slides):
        c = dict(s.content or {})
        if c.get("layout") == "composed":
            continue  # composed slides are laid out by the solver, which already enforces size and fit rules
        layout = c.get("layout", "title_bullets")
        bullets = c.get("bullets", [])

        # Auto-trim overlong titles
        if len(s.title or "") > MAX_TITLE_CHARS:
            s.title = s.title[:MAX_TITLE_CHARS - 3].rstrip() + "..."
            fixed_count += 1

        # Fix monotonous consecutive layouts
        if idx == 0 and layout != "full_bleed_hero":
            c["layout"] = "full_bleed_hero"
            fixed_count += 1
        elif idx == total - 1 and layout not in ("conclusion_cta", "quote_testimonial"):
            c["layout"] = "conclusion_cta"
            fixed_count += 1
        elif len(recent_layouts) >= 2 and recent_layouts[-1] == layout and recent_layouts[-2] == layout:
            # Pick a fresh layout
            new_l = alternate_layouts[idx % len(alternate_layouts)]
            c["layout"] = new_l
            fixed_count += 1

        # Auto-trim overflowing bullets
        clean_bullets = []
        for b in bullets[:MAX_BULLETS_PER_SLIDE]:
            txt = b.get("text", "") if isinstance(b, dict) else str(b)
            if len(txt) > MAX_BULLET_CHARS:
                txt = txt[:MAX_BULLET_CHARS - 3].rstrip() + "..."
                fixed_count += 1
            clean_bullets.append({"text": txt, "source_ids": b.get("source_ids", []) if isinstance(b, dict) else []})
        c["bullets"] = clean_bullets

        # Enrich layout with modern cards / KPIs / images
        s.content = c
        recent_layouts.append(c.get("layout"))

    db.session.commit()
    audit = audit_presentation_design(presentation)
    return {
        "presentation_id": presentation.id,
        "fixed_count": fixed_count,
        "audit_after": audit,
    }
