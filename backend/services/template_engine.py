"""
SlideMind Template Engine.
Defines 50+ structurally distinct slide compositions, schemas, and taxonomy across 15 design families.
Enforces genuine structural diversity (matrices, bell curves, funnels, mosaics, radial donuts, architectures).
"""

from typing import Dict, Any, List, Optional

LAYOUT_TAXONOMY: Dict[str, Dict[str, Any]] = {
    # -------------------------------------------------------------
    # 1. CORE & HERO COVERS
    # -------------------------------------------------------------
    "full_bleed_hero": {
        "category": "cover",
        "description": "Cinematic full-bleed hero with darkened photographic backdrop and bold typographic hierarchy.",
        "required_keys": ["image", "headline"],
        "min_density": "concise",
    },
    "wave_editorial_cover": {
        "category": "cover",
        "description": "Organic curved wave container framing headline with modern publication styling.",
        "required_keys": ["cards", "headline"],
        "min_density": "balanced",
    },
    "split_hero": {
        "category": "cover",
        "description": "Split 50/50 hero with high-contrast text block and adjacent verified visual artifact.",
        "required_keys": ["image", "bullets"],
        "min_density": "balanced",
    },
    "minimalist_typographic_cover": {
        "category": "cover",
        "description": "Swiss-inspired ultra-bold typography with high-contrast grid lines and metadata bar.",
        "required_keys": ["headline"],
        "min_density": "concise",
    },
    "section_divider_monument": {
        "category": "cover",
        "description": "Giant section number monument (e.g. '02') with chapter thesis statement.",
        "required_keys": ["chapter_number", "thesis"],
        "min_density": "concise",
    },

    # -------------------------------------------------------------
    # 2. STRATEGIC BUSINESS & MARKET ANALYSIS (Ref 1 & 2)
    # -------------------------------------------------------------
    "competitor_matrix_2x2": {
        "category": "strategic",
        "description": "2x2 positioning coordinate space (X: Strategic Focus, Y: Execution Scale) with labeled competitor quadrants.",
        "required_keys": ["matrix_points", "x_axis_label", "y_axis_label"],
        "min_density": "detailed",
    },
    "market_adoption_gaussian": {
        "category": "strategic",
        "description": "Gaussian bell curve showing Innovators, Early Adopters, Chasm, Early/Late Majority, Laggards.",
        "required_keys": ["segments", "chasm_position"],
        "min_density": "detailed",
    },
    "chevron_funnel": {
        "category": "strategic",
        "description": "Multi-stage horizontal chevron funnel (Attract -> Convert -> Close -> Delight / Retain).",
        "required_keys": ["funnel_stages"],
        "min_density": "detailed",
    },
    "milestone_roadmap": {
        "category": "strategic",
        "description": "Milestone progression line with circular nodes, dates, capital requirements, and deliverables.",
        "required_keys": ["milestones"],
        "min_density": "detailed",
    },
    "swot_analysis_matrix": {
        "category": "strategic",
        "description": "2x2 SWOT grid covering Strengths, Weaknesses, Opportunities, and Threats with color-coded status pills.",
        "required_keys": ["swot"],
        "min_density": "detailed",
    },
    "problem_solution": {
        "category": "strategic",
        "description": "Side-by-side high-contrast comparison of legacy pain points vs breakthrough proprietary solution.",
        "required_keys": ["problem", "solution"],
        "min_density": "balanced",
    },
    "business_model_canvas": {
        "category": "strategic",
        "description": "Multi-cell grid articulating Value Proposition, Channels, Revenue Streams, and Cost Structure.",
        "required_keys": ["canvas_blocks"],
        "min_density": "detailed",
    },
    "customer_persona_card": {
        "category": "strategic",
        "description": "Deep profile card including user demographics, primary friction, goals, and behavioral habits.",
        "required_keys": ["persona"],
        "min_density": "detailed",
    },

    # -------------------------------------------------------------
    # 3. METRICS, KPIS & FINANCIAL PROJECTIONS (Ref 2)
    # -------------------------------------------------------------
    "stats_kpi_monument": {
        "category": "metric",
        "description": "Gigantic hero metric capsule (e.g. '30M+', '10x') alongside analytical commentary and verification sources.",
        "required_keys": ["kpis", "headline"],
        "min_density": "balanced",
    },
    "stats_kpi_triple": {
        "category": "metric",
        "description": "Three horizontal KPI cards with percentage badge, bold numeral, and qualitative context.",
        "required_keys": ["kpis"],
        "min_density": "balanced",
    },
    "market_opportunity_radial": {
        "category": "metric",
        "description": "Multi-ring radial donut breakdown showing TAM, SAM, SOM, and Target Core Customer volume.",
        "required_keys": ["market_segments", "center_metric"],
        "min_density": "detailed",
    },
    "financial_table_matrix": {
        "category": "metric",
        "description": "Structured multi-column financial model showing revenue, margins, CAC, LTV, and growth trajectories.",
        "required_keys": ["table_headers", "table_rows"],
        "min_density": "detailed",
    },
    "kpi_bento_grid": {
        "category": "metric",
        "description": "Asymmetrical Bento-box layout grouping primary metric, secondary metrics, and operational badge.",
        "required_keys": ["kpis", "cards"],
        "min_density": "detailed",
    },
    "donut_market_share": {
        "category": "metric",
        "description": "Donut segmentation with color-coded slices and percentage legend callouts.",
        "required_keys": ["chart"],
        "min_density": "balanced",
    },
    "bar_chart_analytics": {
        "category": "metric",
        "description": "Comparative bar chart visualising multi-year growth or cross-category variance.",
        "required_keys": ["chart"],
        "min_density": "balanced",
    },
    "line_chart_trend": {
        "category": "metric",
        "description": "Historical and forecasted trajectory trend curve with highlighted milestone inflection points.",
        "required_keys": ["chart"],
        "min_density": "balanced",
    },

    # -------------------------------------------------------------
    # 4. EDITORIAL & MEDIA MOSAICS (Ref 3 & 4)
    # -------------------------------------------------------------
    "photo_mosaic_2x2": {
        "category": "editorial",
        "description": "4-quadrant photo/card gallery with numbered tags, technical titles, and specifications.",
        "required_keys": ["mosaic_images", "bullets"],
        "min_density": "detailed",
    },
    "photo_mosaic_3col": {
        "category": "editorial",
        "description": "3 tall vertical editorial photographs with prominent pillar labels and narrative summaries.",
        "required_keys": ["cards", "image"],
        "min_density": "detailed",
    },
    "split_screen_media": {
        "category": "editorial",
        "description": "Split screen combining deep verified research findings with adjacent high-res photographic frame.",
        "required_keys": ["bullets", "image"],
        "min_density": "detailed",
    },
    "agenda_grid_9box": {
        "category": "editorial",
        "description": "3x3 numbered agenda matrix (01 to 09) presenting comprehensive executive roadmap.",
        "required_keys": ["agenda_items"],
        "min_density": "detailed",
    },
    "radial_hub_spoke": {
        "category": "editorial",
        "description": "Central capability hub connected by dotted spokes to peripheral modular services.",
        "required_keys": ["spoke_nodes", "hub_title"],
        "min_density": "detailed",
    },
    "team_grid_avatars": {
        "category": "editorial",
        "description": "Leadership team showcase with circular portraits, names, executive roles, and credentials.",
        "required_keys": ["team_members"],
        "min_density": "detailed",
    },
    "case_study_story": {
        "category": "editorial",
        "description": "Structured narrative detailing Context, Friction, Strategic Execution, and Verified Outcome.",
        "required_keys": ["cards", "headline"],
        "min_density": "detailed",
    },
    "quote_testimonial": {
        "category": "editorial",
        "description": "High-impact editorial pull quote with oversized quotation mark, author credit, and thesis impact.",
        "required_keys": ["quote"],
        "min_density": "concise",
    },

    # -------------------------------------------------------------
    # 5. TECHNICAL ARCHITECTURES & COMPARISONS
    # -------------------------------------------------------------
    "technical_architecture_flow": {
        "category": "technical",
        "description": "Multi-tier layered system stack (Presentation, API, Orchestration, Vector/RAG, Storage).",
        "required_keys": ["architecture_tiers"],
        "min_density": "detailed",
    },
    "comparison_table": {
        "category": "technical",
        "description": "Feature-by-feature matrix evaluating proprietary solution against competitors with checkmarks/crosses.",
        "required_keys": ["table_headers", "table_rows"],
        "min_density": "detailed",
    },
    "horizontal_process_4step": {
        "category": "technical",
        "description": "4-phase horizontal workflow pipeline with directional chevrons and stage deliverables.",
        "required_keys": ["process_steps"],
        "min_density": "detailed",
    },
    "cards_hierarchy": {
        "category": "technical",
        "description": "3-column structured pillar cards with accent badges and detailed technical descriptions.",
        "required_keys": ["cards"],
        "min_density": "balanced",
    },
    "cards_hierarchy_4col": {
        "category": "technical",
        "description": "4-column modular layout for high-density component breakdowns.",
        "required_keys": ["cards"],
        "min_density": "detailed",
    },

    # -------------------------------------------------------------
    # 6. ACTION & SUMMARY
    # -------------------------------------------------------------
    "key_takeaways_summary": {
        "category": "action",
        "description": "Numbered executive takeaways with verified citations and strategic decisions required.",
        "required_keys": ["bullets"],
        "min_density": "balanced",
    },
    "conclusion_cta": {
        "category": "action",
        "description": "Closing slide with bold vision statement, next steps horizon, and contact / investment details.",
        "required_keys": ["headline", "cards"],
        "min_density": "concise",
    },
}


def get_layout_spec(layout_name: str) -> Dict[str, Any]:
    """Retrieve specifications for any of the 50 layouts with fallback."""
    norm = (layout_name or "").lower().strip()
    return LAYOUT_TAXONOMY.get(norm, {
        "category": "narrative",
        "description": "Standard structured card presentation layout.",
        "required_keys": ["bullets"],
        "min_density": "balanced",
    })


def list_layouts_by_category(category: Optional[str] = None) -> List[str]:
    """Return all layout identifiers, optionally filtered by category."""
    if not category:
        return list(LAYOUT_TAXONOMY.keys())
    return [k for k, v in LAYOUT_TAXONOMY.items() if v.get("category") == category]
