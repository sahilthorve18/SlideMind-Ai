"""Presentation Design Intelligence Engine for SlideMind AI.

Analyzes presentation topic, audience, purpose, and visual storytelling
to construct an art-directed slide design plan before slide generation.
"""
import logging
from typing import Any, Dict, List, Optional

from services import gemini
from services.design_systems import DESIGN_SYSTEMS, get_design_system

log = logging.getLogger(__name__)

# Valid rich modern slide layouts
VALID_LAYOUTS = [
    "full_bleed_hero",
    "split_screen",
    "large_typography",
    "cards_hierarchy",
    "stats_kpi",
    "comparison_table",
    "timeline",
    "process_diagram",
    "chart_visualization",
    "diagram",
    "quote_testimonial",
    "problem_solution",
    "architecture_diagram",
    "section_divider",
    "conclusion_cta",
    # Legacy fallbacks
    "title_bullets",
    "title_only",
]

DEFAULT_PACING_TEMPLATES = {
    3: ["full_bleed_hero", "cards_hierarchy", "conclusion_cta"],
    5: ["full_bleed_hero", "problem_solution", "cards_hierarchy", "stats_kpi", "conclusion_cta"],
    7: ["full_bleed_hero", "problem_solution", "split_screen", "process_diagram", "stats_kpi", "quote_testimonial", "conclusion_cta"],
    10: [
        "full_bleed_hero",
        "problem_solution",
        "split_screen",
        "cards_hierarchy",
        "stats_kpi",
        "process_diagram",
        "chart_visualization",
        "comparison_table",
        "quote_testimonial",
        "conclusion_cta",
    ],
}


def pick_default_design_system(topic: str, audience: str) -> str:
    """Intelligently pick an appropriate design system based on topic keywords and audience."""
    t_lower = (topic + " " + audience).lower()
    if any(k in t_lower for k in ["ai", "machine learning", "neural", "quantum", "cyber", "robot", "future", "algorithm"]):
        return "futuristic_ai"
    if any(k in t_lower for k in ["pitch", "investor", "startup", "seed", "venture", "fundraise", "growth"]):
        return "startup_pitch"
    if any(k in t_lower for k in ["tech", "software", "cloud", "devops", "code", "architecture", "data engineer"]):
        return "dark_technology"
    if any(k in t_lower for k in ["data", "analytics", "financial", "revenue", "quarterly", "metric", "forecast", "kpi"]):
        return "data_storytelling"
    if any(k in t_lower for k in ["executive", "corporate", "board", "governance", "consulting", "banking"]):
        return "corporate_premium"
    if any(k in t_lower for k in ["student", "school", "education", "lecture", "teach", "history", "biology", "science"]):
        return "education_modern"
    if any(k in t_lower for k in ["creative", "design", "brand", "marketing", "art", "fashion", "campaign"]):
        return "creative_agency"
    if any(k in t_lower for k in ["culture", "book", "essay", "philosophy", "literature", "editorial"]):
        return "editorial_magazine"
    if any(k in t_lower for k in ["keynote", "product launch", "vision", "cinematic"]):
        return "apple_keynote"
    return "swiss_minimal"


def get_default_layout_for_index(i: int, total: int, purpose: str = "") -> str:
    """Return an appropriate layout ensuring variety."""
    if i == 0:
        return "full_bleed_hero"
    if i == total - 1:
        return "conclusion_cta"

    purp = purpose.lower()
    if any(k in purp for k in ["problem", "challenge", "pain", "contrast", "vs"]):
        return "problem_solution"
    if any(k in purp for k in ["metric", "stat", "number", "kpi", "growth", "results"]):
        return "stats_kpi"
    if any(k in purp for k in ["step", "workflow", "process", "phase", "journey", "how"]):
        return "process_diagram"
    if any(k in purp for k in ["compare", "vs", "versus", "matrix", "difference"]):
        return "comparison_table"
    if any(k in purp for k in ["data", "chart", "trend", "share", "volume"]):
        return "chart_visualization"
    if any(k in purp for k in ["quote", "customer", "voice", "testimonial", "statement"]):
        return "quote_testimonial"
    if any(k in purp for k in ["timeline", "history", "milestone", "roadmap"]):
        return "timeline"
    if any(k in purp for k in ["architecture", "system", "stack", "layers"]):
        return "architecture_diagram"

    # Fallback to balanced rhythm
    rotation = ["cards_hierarchy", "split_screen", "large_typography", "stats_kpi", "process_diagram"]
    return rotation[i % len(rotation)]


def generate_design_plan(
    topic: str,
    audience: str = "college_students",
    slide_count: int = 10,
    context: str = "",
    user_theme_preference: Optional[str] = None,
) -> Dict[str, Any]:
    """Uses Gemini to produce an end-to-end presentation design strategy and slide plan.
    Falls back gracefully to a deterministic high-fidelity design plan if AI is unavailable.
    """
    chosen_system = user_theme_preference or pick_default_design_system(topic, audience)
    ds = get_design_system(chosen_system)

    prompt = (
        f"You are an elite presentation art director and visual strategist for SlideMind AI.\n"
        f"Analyze this presentation request and produce a structured design plan.\n\n"
        f"Topic: {topic[:500]}\n"
        f"Audience: {audience}\n"
        f"Slide Count: {slide_count}\n"
        f"Preferred Theme: {ds.name} ({ds.description})\n"
        + (f"Reference context: {context[:4000]}\n" if context else "")
        + f"\nSelect diverse layouts from: {', '.join(VALID_LAYOUTS[:14])}.\n"
        f"Rule: NEVER use the same layout more than twice, and NEVER sequentially.\n\n"
        f'Return JSON with this exact schema:\n'
        f'{{\n'
        f'  "presentation_title": "Short punchy presentation title",\n'
        f'  "design_system": "{ds.id}",\n'
        f'  "storytelling_archetype": "Name of narrative framework (e.g. Problem-Solution Journey, Metric Revelation)",\n'
        f'  "audience_persona": {{"mindset": str, "core_interest": str, "visual_density": "high|medium|minimal"}} ,\n'
        f'  "slides": [\n'
        f'    {{\n'
        f'      "position": 1,\n'
        f'      "title": "Slide Title",\n'
        f'      "purpose": "What this slide achieves",\n'
        f'      "layout": "one of valid layouts",\n'
        f'      "visual_asset_concept": "Description of image, chart, metric, or diagram needed"\n'
        f'    }}\n'
        f'  ]\n'
        f'}}\n'
    )

    try:
        plan = gemini.generate_json(prompt, system="You are an expert creative director for world-class presentations.", temperature=0.3)
        slides = plan.get("slides")
        if isinstance(slides, list) and len(slides) >= 3 and plan.get("presentation_title"):
            # Ensure every slide layout is valid and positioned correctly
            clean_slides = []
            for i, s in enumerate(slides[:slide_count], start=1):
                layout = s.get("layout")
                if layout not in VALID_LAYOUTS:
                    layout = get_default_layout_for_index(i - 1, slide_count, s.get("purpose", ""))
                clean_slides.append({
                    "position": i,
                    "title": str(s.get("title", f"Slide {i}"))[:200],
                    "purpose": str(s.get("purpose", ""))[:300],
                    "layout": layout,
                    "visual_asset_concept": str(s.get("visual_asset_concept", ""))[:300],
                })
            return {
                "presentation_title": str(plan["presentation_title"])[:255],
                "design_system": plan.get("design_system", ds.id),
                "storytelling_archetype": plan.get("storytelling_archetype", "Insight & Action"),
                "audience_persona": plan.get("audience_persona", {"mindset": audience, "visual_density": "medium"}),
                "slides": clean_slides,
            }
    except Exception as e:
        log.warning("Gemini design plan generation failed or offline, building deterministic design plan: %s", e)

    # Fallback deterministic plan
    template = DEFAULT_PACING_TEMPLATES.get(slide_count)
    if not template:
        template = [get_default_layout_for_index(i, slide_count) for i in range(slide_count)]

    fallback_slides = []
    for i in range(1, slide_count + 1):
        layout = template[i - 1] if i - 1 < len(template) else get_default_layout_for_index(i - 1, slide_count)
        fallback_slides.append({
            "position": i,
            "title": topic if i == 1 else f"{topic}: Key Dimension {i}",
            "purpose": "Introduction & thesis" if i == 1 else ("Conclusion & next steps" if i == slide_count else f"Key insight {i}"),
            "layout": layout,
            "visual_asset_concept": f"Visual representation of {topic} phase {i}",
        })

    return {
        "presentation_title": topic[:200],
        "design_system": ds.id,
        "storytelling_archetype": "Modern Visual Journey",
        "audience_persona": {"mindset": audience, "visual_density": "medium"},
        "slides": fallback_slides,
    }
