"""Comprehensive unit and integration tests for SlideMind AI Visual Intelligence Engine.
Verifies Phase 1 implementation:
- Structured visual briefs
- Live Wikimedia Commons image retrieval
- Metadata attribution (artist, license, license_url, dimensions)
- Semantic candidate ranking and aspect ratio validation
- Intelligent visual selection with deduplication
- Graceful fallbacks
"""
import pytest
from services import visual_intelligence
from services.visual_intelligence import (
    CandidateImage,
    VisualBrief,
    evaluate_and_rank_candidates,
    generate_visual_brief,
    retrieve_image_candidates,
    search_curated_fallback,
    search_wikimedia_commons,
    select_best_slide_visual,
)


def test_generate_visual_brief_photograph():
    """Verify structured visual brief generation for a photography-rich slide."""
    brief = generate_visual_brief(
        topic="Renewable Energy Transition",
        slide_title="Solar Photovoltaic Expansion",
        purpose="Illustrate modern utility-scale solar generation",
        bullets=[
            "Utility-scale solar farms provide over 40% of new capacity additions",
            "Bifacial panel technology boosts energy yield by up to 15%",
        ],
        layout="split_screen",
        slide_index=1,
        total_slides=8,
    )

    assert isinstance(brief, VisualBrief)
    assert brief.slide_title == "Solar Photovoltaic Expansion"
    assert brief.required_visual_type in ("photograph", "diagram", "chart")
    assert any("solar" in kw.lower() or "photovoltaic" in kw.lower() for kw in brief.search_keywords)
    assert brief.preferred_composition in ("split_right", "split_left", "full_bleed", "card_embedded")
    assert brief.aspect_ratio in ("16:9", "4:3", "any")


def test_generate_visual_brief_typography_restraint():
    """Verify visual brief acknowledges when slides need restraint (e.g. quote/data)."""
    brief = generate_visual_brief(
        topic="Minimalist Architecture",
        slide_title="Executive Finding",
        purpose="Highlight a single impactful quote with high typographic focus",
        bullets=["Simplicity is the ultimate sophistication."],
        layout="quote_testimonial",
        slide_index=4,
        total_slides=6,
    )
    assert isinstance(brief, VisualBrief)
    # Quote layout should recognize typographic focus or restrained visual
    assert brief.visual_placement in ("subtle_backdrop", "none", "card_embedded", "split_left")


def test_search_wikimedia_commons_live():
    """Verify live Wikimedia Commons search returns real images with attribution metadata."""
    candidates = search_wikimedia_commons("wind turbine", limit=4)

    assert len(candidates) > 0
    candidate = candidates[0]
    assert isinstance(candidate, CandidateImage)
    assert candidate.source == "Wikimedia Commons"
    assert candidate.image_url.startswith("http")
    assert candidate.thumb_url.startswith("http")
    assert candidate.width > 0
    assert candidate.height > 0
    assert candidate.aspect_ratio > 0
    # Must have licensing attribution
    assert len(candidate.license) > 0
    assert candidate.source_page.startswith("https://commons.wikimedia.org")


def test_search_curated_fallback():
    """Verify curated fallback returns high-resolution domain photos with Unsplash attribution."""
    candidates = search_curated_fallback("artificial intelligence neural networks", limit=3)
    assert len(candidates) >= 1
    c = candidates[0]
    assert c.source == "Unsplash"
    assert "Unsplash" in c.license
    assert "images.unsplash.com" in c.image_url
    assert c.aspect_ratio > 1.0  # Landscape


def test_retrieve_image_candidates_deduplication():
    """Verify retrieve_image_candidates deduplicates already used URLs."""
    brief = VisualBrief(
        slide_title="Wind Turbines",
        main_message="Wind generation capacity",
        key_concepts=["wind", "turbine", "energy"],
        required_visual_type="photograph",
        search_keywords=["wind turbine clean energy"],
        preferred_composition="split_right",
        aspect_ratio="16:9",
        visual_placement="right_column",
        style="cinematic",
        negative_space="left",
    )

    all_candidates = retrieve_image_candidates(brief)
    if all_candidates:
        used_url = all_candidates[0].image_url
        filtered_candidates = retrieve_image_candidates(brief, already_used_urls={used_url})
        assert all(c.image_url != used_url for c in filtered_candidates)


def test_candidate_ranking_and_aspect_ratio_preference():
    """Verify aspect ratio preference boosts 16:9 landscape candidates over portrait/extreme ratios."""
    brief = VisualBrief(
        slide_title="Autonomous Vehicles",
        main_message="Self driving sensor suite",
        key_concepts=["lidar", "radar", "camera"],
        required_visual_type="photograph",
        search_keywords=["autonomous car sensor"],
        preferred_composition="split_right",
        aspect_ratio="16:9",
        visual_placement="right_column",
        style="technical",
        negative_space="left",
    )

    landscape = CandidateImage(
        id="c1",
        title="Autonomous vehicle sensor array on vehicle roof",
        image_url="https://example.com/c1.jpg",
        thumb_url="https://example.com/c1_thumb.jpg",
        source="Wikimedia Commons",
        source_page="https://commons.wikimedia.org/wiki/File:C1.jpg",
        artist="Engineer",
        artist_url=None,
        license="CC BY-SA 4.0",
        license_url="https://creativecommons.org/licenses/by-sa/4.0",
        width=1920,
        height=1080,
        aspect_ratio=1.777,  # Exact 16:9
        description="Autonomous vehicle sensor array lidar rooftop demonstration",
    )

    portrait = CandidateImage(
        id="c2",
        title="Autonomous vehicle sensor vertical stand",
        image_url="https://example.com/c2.jpg",
        thumb_url="https://example.com/c2_thumb.jpg",
        source="Wikimedia Commons",
        source_page="https://commons.wikimedia.org/wiki/File:C2.jpg",
        artist="Engineer",
        artist_url=None,
        license="CC BY-SA 4.0",
        license_url="https://creativecommons.org/licenses/by-sa/4.0",
        width=600,
        height=1200,
        aspect_ratio=0.5,  # Tall portrait
        description="Autonomous vehicle sensor array lidar rooftop demonstration",
    )

    ranked = evaluate_and_rank_candidates([portrait, landscape], brief)
    # Landscape candidate should rank first due to matching 16:9 presentation aspect ratio
    assert ranked[0].id == "c1"
    assert ranked[0].score > ranked[1].score


def test_select_best_slide_visual_end_to_end():
    """Verify top-level selector returns rich metadata with attribution and dimensions."""
    visual = select_best_slide_visual(
        topic="Renewable Energy",
        slide_title="Offshore Wind Turbines",
        purpose="Showcase modern offshore marine wind farms",
        bullets=["Deepwater floating foundations enable deployment in high-wind regions"],
        layout="split_screen",
        slide_index=2,
        total_slides=6,
    )

    assert visual is not None
    assert "url" in visual
    assert "title" in visual
    assert "source" in visual
    assert visual["source"] in ("Wikimedia Commons", "Unsplash", "Pexels")
    assert "license" in visual
    assert "dimensions" in visual
    assert visual["dimensions"]["width"] > 0
    assert visual["dimensions"]["height"] > 0
    assert "composition" in visual
    assert "relevance_score" in visual
    assert visual["relevance_score"] >= 50.0
