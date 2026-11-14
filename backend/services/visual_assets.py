"""Professional Visual Assets & Layout Specification Engine for SlideMind AI.

Manages curated, licensed photography (Unsplash License), vector icons,
SVG diagrams, and structured data specifications for every layout.
"""
import hashlib
import logging
import re
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

# Curated, verified high-resolution Unsplash photo IDs by thematic categories
CURATED_CATEGORY_PHOTOS = {
    "technology": [
        ("photo-1518770660439-4636190af475", "Microchip circuitry and hardware architecture"),
        ("photo-1451187580459-43490279c0fa", "Satellite earth network and global connectivity"),
        ("photo-1526374965328-7f61d4dc18c5", "Digital code matrix and cybersecurity encryption"),
        ("photo-1504384308090-c894fdcc538d", "Modern tech workstation and cloud infrastructure"),
        ("photo-1531297484001-80022131f5a1", "Sleek modern laptop hardware and engineering"),
    ],
    "ai": [
        ("photo-1677442136019-21780efad99a", "Artificial intelligence neural nodes visualization"),
        ("photo-1620712943543-bcc4688e7485", "Machine learning digital brain interface"),
        ("photo-1618005182384-a83a8bd57fbe", "Abstract generative computing landscape"),
        ("photo-1614680376593-902f749f7ffc", "Deep learning algorithms and synthetic cognition"),
    ],
    "business": [
        ("photo-1486406146926-c627a92ad1ab", "Modern glass architectural corporate headquarters"),
        ("photo-1460925895917-afdab827c52f", "Strategic analytics dashboard and financial growth"),
        ("photo-1507679799987-c73779587ccf", "Executive leadership presenting in modern boardroom"),
        ("photo-1551836022-d5d88e9218df", "Collaborative strategic enterprise summit"),
    ],
    "energy": [
        ("photo-1509391365360-2e959784a276", "Solar photovoltaic panel farm under azure sky"),
        ("photo-1466611653911-95081537e5b7", "Clean energy wind turbines over mountain ridge"),
        ("photo-1473341304170-971dccb5ac1e", "Luminescent eco-friendly electricity grid"),
        ("photo-1497435334941-8c899ee9e8e9", "Sustainable clean energy landscape"),
    ],
    "science": [
        ("photo-1532094349884-543bc11b234d", "Laboratory biochemistry glassware research"),
        ("photo-1507668077129-56e32842fceb", "Scientific innovation and quantum analysis"),
        ("photo-1518152006812-edab29b069ac", "Medical diagnostics and biotechnology microscope"),
    ],
    "creative": [
        ("photo-1513364776144-60967b0f800f", "Expressive modern color splash and visual art"),
        ("photo-1500462918059-b1a0cb512f1d", "Dynamic geometric light rays and creative gradients"),
        ("photo-1550684848-fac1c5b4e853", "Minimalist studio composition and vibrant textures"),
    ],
    "nature": [
        ("photo-1470071459604-3b5ec3a7fe05", "Mist-shrouded mountain forest wilderness"),
        ("photo-1441974231531-c6227db76b6e", "Verdant sunbeam canopy and ecological biodiversity"),
    ],
    "education": [
        ("photo-1541339907198-e08756dedf3f", "Modern university campus hall and collaborative student space"),
        ("photo-1523240795612-9a054b0db644", "University students collaborating in academic library"),
        ("photo-1562774053-701939374585", "Historic university brick campus and academic grounds"),
        ("photo-1498243691581-b145c3f54a5a", "Campus academic library reading hall and modern architecture"),
    ],
    "facilities_operations": [
        ("photo-1581092160607-ee22621dd758", "Field engineer inspecting industrial equipment and technical systems"),
        ("photo-1581092335397-9583fe92d232", "Maintenance specialist with diagnostic tablet performing hardware checks"),
        ("photo-1504384308090-c894fdcc538d", "Operations control center and facility monitoring room"),
        ("photo-1581091226825-a6a2a5aee158", "Technician servicing building electrical and climate infrastructure"),
    ],
}


def get_thematic_image(topic: str, slide_title: str, index: int = 0) -> Dict[str, str]:
    """Resolves an appropriate high-resolution licensed Unsplash photo with attribution."""
    t_query = topic.lower()
    s_query = slide_title.lower()
    query = (t_query + " " + s_query)

    category = "business"
    if any(k in s_query for k in ["ticket", "repair", "technician", "maintenance", "facility", "facilities", "equipment", "hardware", "fix", "mechanics"]):
        category = "facilities_operations"
    elif any(k in query for k in ["campus", "university", "student", "college", "school", "academic", "education", "classroom"]):
        category = "education"
    elif any(k in query for k in ["ticket", "repair", "technician", "maintenance", "facility", "facilities", "equipment", "hardware", "fix", "mechanics"]):
        category = "facilities_operations"
    elif any(k in query for k in ["ai", "machine learning", "neural", "deep learning", "robot", "gpt"]):
        category = "ai"
    elif any(k in query for k in ["tech", "software", "cloud", "code", "cyber", "data", "algorithm", "developer"]):
        category = "technology"
    elif any(k in query for k in ["energy", "solar", "wind", "climate", "sustainable", "green", "carbon"]):
        category = "energy"
    elif any(k in query for k in ["science", "medical", "biology", "physics", "health", "research", "lab"]):
        category = "science"
    elif any(k in query for k in ["creative", "design", "art", "marketing", "brand", "agency"]):
        category = "creative"
    elif any(k in query for k in ["nature", "environment", "planet", "earth", "eco"]):
        category = "nature"

    photos = CURATED_CATEGORY_PHOTOS.get(category, CURATED_CATEGORY_PHOTOS["business"])
    # Cycle gracefully through category images based on slide index and query hash
    photo_idx = (index + int(hashlib.md5(query.encode()).hexdigest(), 16)) % len(photos)
    photo_id, alt = photos[photo_idx]

    # Unsplash 16:9 crop optimized for slides
    url = f"https://images.unsplash.com/{photo_id}?auto=format&fit=crop&w=1280&h=720&q=80"
    return {
        "url": url,
        "alt": alt,
        "source": "Unsplash",
        "license": "Unsplash License (Free to use, commercial and non-commercial)",
        "photo_id": photo_id,
    }


def get_intelligent_visual(
    topic: str,
    slide_title: str,
    bullets: Optional[List[str]] = None,
    layout: str = "split_screen",
    index: int = 0,
    total_slides: int = 10,
    already_used_urls: Optional[set] = None,
) -> Dict[str, Any]:
    """Retrieves an intelligently matched visual using the Visual Intelligence Engine:
    slide-specific visual brief -> live multi-source search (Wikimedia Commons/Unsplash/Pexels)
    -> semantic scoring and aspect-ratio ranking -> full license attribution.

    Gracefully falls back to curated photographic library on network errors.
    """
    try:
        from services import visual_intelligence

        result = visual_intelligence.select_best_slide_visual(
            topic=topic,
            slide_title=slide_title,
            bullets=bullets,
            layout=layout,
            slide_index=index,
            total_slides=total_slides,
            already_used_urls=already_used_urls,
        )
        if result and result.get("url"):
            # Ensure backwards-compatible 'alt' attribute exists alongside rich metadata
            result["alt"] = result.get("description") or result.get("title") or f"{slide_title} visual"
            return result
    except Exception as e:
        log.warning("Intelligent visual search encountered error: %s. Falling back to curated catalog.", e)

    # Fallback to curated catalog
    return get_thematic_image(topic, slide_title, index)


def enrich_slide_specification(slide_dict: Dict[str, Any], topic: str, index: int, total_slides: int) -> Dict[str, Any]:
    """Generates layout-specific structured visual specifications (cards, KPIs, steps, quotes).
    Ensures every layout has rich visual content and is never just blank bullet points.
    """
    layout = slide_dict.get("layout", "title_bullets")
    title = slide_dict.get("title", f"Slide {index + 1}")
    bullets = slide_dict.get("bullets", [])

    # Extract clean text from bullets
    bullet_texts = [b["text"] if isinstance(b, dict) else str(b) for b in bullets if b]
    if not bullet_texts:
        bullet_texts = [f"Key structural foundation of {topic}", f"Implementation and impact across key workflows"]

    spec: Dict[str, Any] = {
        "layout": layout,
        "title": title,
        "bullets": [{"text": t, "source_ids": b.get("source_ids", []) if isinstance(b, dict) else []} for t, b in zip(bullet_texts, bullets or [{}])]
    }

    # Add relevant photo asset for visual layouts via the Visual Intelligence Engine
    if layout in ("full_bleed_hero", "split_screen", "image_gallery", "conclusion_cta", "section_divider"):
        spec["image"] = get_intelligent_visual(
            topic=topic,
            slide_title=title,
            bullets=bullet_texts,
            layout=layout,
            index=index,
            total_slides=total_slides,
        )

    # 1. Cards Hierarchy (e.g. 2-4 cards with title, text, icon/badge)
    if layout in ("cards_hierarchy", "two_column"):
        cards = []
        icons = ["zap", "shield", "sparkles", "trending-up", "layers", "target"]
        for ci, text in enumerate(bullet_texts[:4]):
            parts = text.split(":", 1) if ":" in text else text.split(" - ", 1)
            card_title = parts[0].strip() if len(parts) > 1 else f"Pillar {ci + 1}"
            card_desc = parts[1].strip() if len(parts) > 1 else parts[0].strip()
            cards.append({
                "title": card_title[:60],
                "description": card_desc[:180],
                "icon": icons[ci % len(icons)],
                "badge": f"0{ci + 1}",
            })
        spec["cards"] = cards

    # 2. Stats / KPI Slide
    elif layout == "stats_kpi":
        kpis = []
        default_stats = [
            ("10x", "Acceleration", "Velocity gain in presentation output"),
            ("99.4%", "Precision", "Factually grounded in primary source files"),
            ("0s", "Friction", "Automated design layout and typography pairing"),
            ("2026", "Design Standard", "Modern high-end art direction built-in")
        ]
        for ki, text in enumerate(bullet_texts[:4]):
            # Try to extract numbers from text
            match = re.search(r"(\$?\d+[\d,\.]*[%xXkKMmBb\+]?)", text)
            val = match.group(1) if match else default_stats[ki % len(default_stats)][0]
            label = default_stats[ki % len(default_stats)][1]
            desc = text[:120]
            kpis.append({"value": val, "label": label, "description": desc})
        spec["kpis"] = kpis

    # 3. Problem vs Solution
    elif layout == "problem_solution":
        spec["problem"] = {
            "title": "The Challenge & Friction",
            "points": bullet_texts[:2] or ["Legacy manual deck creation takes hours of alignment", "Disjointed typography, poor contrast, and text-heavy slides"],
        }
        spec["solution"] = {
            "title": "The Strategic Breakthrough",
            "points": bullet_texts[2:4] or ["Autonomous intelligent visual design systems", "Grounded research, automated visual variety, and instant exports"],
        }

    # 4. Process Diagram / Steps
    elif layout in ("process_diagram", "timeline"):
        steps = []
        for si, text in enumerate(bullet_texts[:4], start=1):
            parts = text.split(":", 1) if ":" in text else text.split(" - ", 1)
            step_name = parts[0].strip() if len(parts) > 1 else f"Phase {si}"
            step_detail = parts[1].strip() if len(parts) > 1 else parts[0].strip()
            steps.append({
                "step_number": si,
                "title": step_name[:50],
                "description": step_detail[:140],
            })
        spec["process_steps"] = steps

    # 5. Comparison Table
    elif layout == "comparison_table":
        spec["comparison"] = {
            "headers": ["Dimension", "Traditional Approach", "SlideMind Next-Gen"],
            "rows": [
                ["Design Quality", "Generic bullet lists", "10+ Premium Art-Directed Systems"],
                ["Layout Variety", "Identical title + body", "15 Adaptive Layout Formats"],
                ["Data Integrity", "Unchecked assumptions", "Strict Document & Research Grounding"],
                ["Export Options", "Locked formats", "Native PPTX, PDF & Google Slides Sync"]
            ]
        }

    # 6. Quote / Testimonial
    elif layout == "quote_testimonial":
        quote_text = bullet_texts[0] if bullet_texts else f"{topic} represents a paradigm shift in how ideas are communicated."
        spec["quote"] = {
            "text": quote_text[:220],
            "author": "Key Strategic Finding",
            "role": f"Verified Insight in {topic[:40]}",
        }

    # 7. Architecture Diagram
    elif layout == "architecture_diagram":
        spec["architecture"] = {
            "layers": [
                {"name": "Experience Layer", "tech": "React, Tailwind, Responsive 16:9 Canvas"},
                {"name": "Intelligence Engine", "tech": "Design Planning, Quality Auditor, Pacing Engine"},
                {"name": "Model Orchestration", "tech": "Gemini 3.5 Auto-Fallback Cascade & Tools"},
                {"name": "Output Layer", "tech": "Google Slides API, Native PPTX & PDF Generators"}
            ]
        }

    return spec
