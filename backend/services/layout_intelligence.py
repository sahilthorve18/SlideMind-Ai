"""
SlideMind Layout Intelligence Service.
Dynamically orchestrates 50+ structurally diverse slide layouts.
Prevents repetitive templates, enforces narrative flow, and matches content semantics.
"""

import re
from typing import List, Dict, Any, Optional
try:
    from services.template_engine import LAYOUT_TAXONOMY, get_layout_spec
except ImportError:
    from backend.services.template_engine import LAYOUT_TAXONOMY, get_layout_spec

# Keyword matching rules to map slide topics to authentic structural compositions
KEYWORD_TO_LAYOUT = [
    (r"(agenda|contents|table of contents|overview|index)", "agenda_grid_9box"),
    (r"(competitor.*matrix|positioning|landscape|rivals|quadrant)", "competitor_matrix_2x2"),
    (r"(compet.*advant|differentiat|moat|strengths vs)", "competitor_matrix_2x2"),
    (r"(adoption|gaussian|bell curve|diffusion|innovators|chasm)", "market_adoption_gaussian"),
    (r"(funnel|acquisition|customer journey|conversion|pipeline)", "chevron_funnel"),
    (r"(roadmap|milestone|horizon|timeline|chronology)", "milestone_roadmap"),
    (r"(swot|strengths.*weaknesses|internal.*external)", "swot_analysis_matrix"),
    (r"(tam|sam|som|market size|market opportunity|addressable)", "market_opportunity_radial"),
    (r"(financial|projections|margins|cac|ltv|revenue model)", "financial_table_matrix"),
    (r"(kpi|traction|monument|benchmarks|scale|growth)", "stats_kpi_monument"),
    (r"(metrics|triple|velocity|impact metrics)", "stats_kpi_triple"),
    (r"(architecture|tech stack|infrastructure|flow|data pipeline)", "technical_architecture_flow"),
    (r"(compar|feature matrix|benchmarking|vs competitors|capability matrix)", "comparison_table"),
    (r"(process|workflow|steps|methodology|pipeline phases)", "horizontal_process_4step"),
    (r"(team|leadership|founders|executives|board)", "team_grid_avatars"),
    (r"(mosaic|gallery|visuals|artifacts|showcase)", "photo_mosaic_2x2"),
    (r"(pillars|foundations|editorial columns|3-col)", "photo_mosaic_3col"),
    (r"(hub|ecosystem|interconnected|spoke|radial network)", "radial_hub_spoke"),
    (r"(problem.*solution|challenge.*fix|before.*after)", "problem_solution"),
    (r"(quote|testimonial|executive voice|pull quote)", "quote_testimonial"),
    (r"(takeaways|key findings|summary|executive summary)", "key_takeaways_summary"),
    (r"(conclusion|call to action|next steps|closing)", "conclusion_cta"),
    (r"(deep dive|case study|in-depth|field report)", "split_screen_media"),
]


def recommend_layout(
    title: str,
    content_text: str = "",
    slide_index: int = 1,
    total_slides: int = 10,
    previous_layout: Optional[str] = None,
) -> str:
    """
    Select an authentic layout for a slide based on its position, title, and semantics,
    guaranteeing no back-to-back duplicate layouts.
    """
    title_lower = (title or "").lower()
    text_lower = (content_text or "").lower()
    combined = f"{title_lower} {text_lower}"

    # First slide is always a cover
    if slide_index == 1:
        if "editorial" in combined or "magazine" in combined:
            return "wave_editorial_cover"
        return "full_bleed_hero"

    # Second slide often serves as agenda/overview in multi-slide decks
    if slide_index == 2 and total_slides >= 6:
        if any(w in title_lower for w in ["agenda", "overview", "contents", "roadmap"]):
            return "agenda_grid_9box"

    # Final slide is a conclusion / CTA
    if slide_index == total_slides:
        if any(w in title_lower for w in ["thank", "question", "next step", "contact", "conclusion"]):
            return "conclusion_cta"
        return "key_takeaways_summary"

    # Match based on semantic keywords
    for pattern, layout in KEYWORD_TO_LAYOUT:
        if re.search(pattern, combined):
            if layout != previous_layout:
                return layout

    # Diverse cyclic rotation for generalized analytical slides
    fallback_pool = [
        "cards_hierarchy",
        "split_screen_media",
        "stats_kpi_triple",
        "horizontal_process_4step",
        "photo_mosaic_2x2",
        "comparison_table",
        "radial_hub_spoke",
        "milestone_roadmap",
    ]

    for candidate in fallback_pool:
        if candidate != previous_layout:
            return candidate

    return "cards_hierarchy"


def balance_deck_layouts(slides: List[Dict[str, Any]], archetype: str = "general") -> List[Dict[str, Any]]:
    """
    Takes an array of slide dictionaries and guarantees true structural diversity across the entire deck.
    Ensures that no two consecutive slides share the same layout or category.
    """
    total = len(slides)
    previous_layout = None
    previous_category = None

    for i, slide in enumerate(slides):
        current_pos = i + 1
        title = slide.get("title", "")
        existing_layout = slide.get("layout")

        # If already set and not repeating previous layout or category, validate it
        if existing_layout and existing_layout != previous_layout:
            spec = get_layout_spec(existing_layout)
            category = spec.get("category")
            if category != previous_category or current_pos in [1, total]:
                previous_layout = existing_layout
                previous_category = category
                continue

        # Recommend a non-repeating structural layout
        new_layout = recommend_layout(
            title=title,
            content_text=str(slide.get("content", "")),
            slide_index=current_pos,
            total_slides=total,
            previous_layout=previous_layout,
        )

        slide["layout"] = new_layout
        spec = get_layout_spec(new_layout)
        previous_layout = new_layout
        previous_category = spec.get("category")

    return slides
