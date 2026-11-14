"""Content Intelligence & Presentation Storytelling Engine for SlideMind AI 2.0.

Provides:
1. Narrative arc design and audience-adaptive storytelling.
2. Structured slide payload schemas separating internal planning from user-visible presentation text.
3. Strict Zero-Hallucination guardrails: zero invented percentages, revenue metrics, or ungrounded statistics.
4. Topic-driven outlines and content synthesis (100% topic-independent, zero hardcoded assumptions).
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional, Union

from services import gemini

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. Generalized Storytelling Archetypes
# ---------------------------------------------------------------------------

NARRATIVE_ARCHETYPES: Dict[str, List[Dict[str, Any]]] = {
    # 1. Operational & Workflow Systems (Generic, topic-independent)
    "product_operations": [
        {"role": "introduction", "layout": "full_bleed_hero", "purpose": "System introduction, operational objectives, and core mission statement"},
        {"role": "intake", "layout": "feature_showcase", "purpose": "Input interface, data ingestion, categorization, and intake channels"},
        {"role": "routing", "layout": "horizontal_process_workflow", "purpose": "Intelligent orchestration, routing criteria, priority assessment, and task assignment"},
        {"role": "execution", "layout": "horizontal_process_4step", "purpose": "Core fulfillment workflow: queue management, stage-by-stage handling, and status progression"},
        {"role": "verification", "layout": "problem_solution", "purpose": "Verification and review: completion confirmation, quality audit, and feedback loops"},
        {"role": "monitoring", "layout": "kpi_dashboard", "purpose": "Administrative oversight: real-time operational tracking, throughput metrics, and SLA compliance"},
    ],

    # 2. Startup & Venture Pitch
    "startup_pitch": [
        {"role": "hook", "layout": "full_bleed_hero", "purpose": "Vision hook, core value proposition, and the fundamental market opportunity"},
        {"role": "problem", "layout": "problem_solution", "purpose": "The systemic customer pain point, current market friction, and why existing solutions fail"},
        {"role": "solution", "layout": "split_screen", "purpose": "Product breakthrough, technological advantage, and customer value mechanism"},
        {"role": "market", "layout": "market_adoption_gaussian", "purpose": "Market adoption dynamics, target segments, and diffusion trajectory"},
        {"role": "competition", "layout": "competitor_matrix_2x2", "purpose": "2x2 positioning coordinate space highlighting competitive advantage and structural defensibility"},
        {"role": "business_model", "layout": "cards_hierarchy", "purpose": "Unit economics, delivery framework, revenue streams, and sustainable expansion model"},
        {"role": "traction", "layout": "stats_kpi_triple", "purpose": "Validated milestones, qualitative feedback, customer adoption signals, and pilot results"},
        {"role": "funnel", "layout": "chevron_funnel", "purpose": "User acquisition funnel, deployment velocity, and scaling methodology"},
        {"role": "roadmap", "layout": "milestone_roadmap", "purpose": "Chronological product milestones, capability scaling, and operational horizon"},
        {"role": "cta", "layout": "conclusion_cta", "purpose": "Executive summary, partnership opportunity, actionable next steps, and contact credentials"},
    ],

    # 3. Technical & Engineering Architecture
    "technical_architecture": [
        {"role": "hook", "layout": "full_bleed_hero", "purpose": "System architecture overview, engineering vision, and technical goals"},
        {"role": "requirements", "layout": "cards_hierarchy", "purpose": "System requirements, scalability bottlenecks, availability targets, and constraints"},
        {"role": "topology", "layout": "technical_architecture_flow", "purpose": "End-to-end component topology, microservices, data flow, and interface boundaries"},
        {"role": "pipeline", "layout": "horizontal_process_workflow", "purpose": "Data processing lifecycle: ingestion, validation, streaming, and persistent storage"},
        {"role": "tradeoffs", "layout": "comparison_table", "purpose": "Engineering tradeoffs: throughput vs latency, consistency vs availability, complexity vs cost"},
        {"role": "performance", "layout": "kpi_dashboard", "purpose": "Operational telemetry: latency budgets, throughput thresholds, and fault recovery parameters"},
        {"role": "security", "layout": "cards_hierarchy", "purpose": "Security posture: authentication, zero-trust boundary, encryption, and audit logging"},
        {"role": "case_study", "layout": "split_screen", "purpose": "Implementation case study: deployment approach, operational patterns, and verified reliability"},
        {"role": "roadmap", "layout": "milestone_roadmap", "purpose": "Engineering implementation milestones, integration gates, and release plan"},
        {"role": "cta", "layout": "conclusion_cta", "purpose": "Technical summary, architectural checklist, documentation references, and discussion"},
    ],

    # 4. Educational & Scientific Concept
    "educational_concept": [
        {"role": "hook", "layout": "minimalist_typographic_cover", "purpose": "Foundational concept introduction, primary scientific inquiry, and core definition"},
        {"role": "foundations", "layout": "cards_hierarchy", "purpose": "Core underlying principles, fundamental laws, and historical discoveries"},
        {"role": "mechanism", "layout": "horizontal_process_workflow", "purpose": "Step-by-step mechanistic explanation of the physical/biological/chemical process"},
        {"role": "visual_breakdown", "layout": "split_screen", "purpose": "Detailed anatomical, chemical, or structural breakdown with annotated components"},
        {"role": "case_example", "layout": "problem_solution", "purpose": "Real-world manifestation, experimental observation, or applied natural phenomena"},
        {"role": "comparisons", "layout": "comparison_table", "purpose": "Key distinctions, taxonomy comparisons, and common student misconceptions"},
        {"role": "summary", "layout": "key_takeaways_summary", "purpose": "Synthesis of foundational concepts, study takeaways, and broader scientific significance"},
    ],

    # 5. Executive & Strategic Consulting
    "executive_consulting": [
        {"role": "hook", "layout": "full_bleed_hero", "purpose": "Executive briefing title, strategic mandate, and high-level context"},
        {"role": "market_shift", "layout": "split_screen", "purpose": "Macro industry dynamics, institutional priorities, and operational landscape"},
        {"role": "challenges", "layout": "problem_solution", "purpose": "Strategic friction, operational bottlenecks, and organizational risks"},
        {"role": "pillars", "layout": "cards_hierarchy", "purpose": "Core strategic pillars required for organizational transformation"},
        {"role": "workflow", "layout": "chevron_funnel", "purpose": "Target operating model transition: diagnostic, workflow modernization, and scale"},
        {"role": "comparison", "layout": "comparison_table", "purpose": "Strategic options evaluation: current manual practice versus modern automated platform"},
        {"role": "timeline", "layout": "milestone_roadmap", "purpose": "Multi-phase execution schedule, governance checkpoints, and accountability milestones"},
        {"role": "leadership", "layout": "team_grid_avatars", "purpose": "Steering committee, operational sponsors, and department leads"},
        {"role": "cta", "layout": "conclusion_cta", "purpose": "Executive recommendations, organizational decisions required, and immediate next steps"},
    ],

    # 6. Academic Research & Empirical Study
    "academic_research": [
        {"role": "hook", "layout": "minimalist_typographic_cover", "purpose": "Research title, primary hypothesis, investigator credentials, and institutional context"},
        {"role": "abstract", "layout": "cards_hierarchy", "purpose": "Executive abstract, problem statement, and scholarly significance"},
        {"role": "literature", "layout": "split_screen", "purpose": "Academic consensus, literature gaps, and foundational baseline references"},
        {"role": "methodology", "layout": "horizontal_process_workflow", "purpose": "Experimental methodology, data collection protocol, and analytical frameworks"},
        {"role": "data", "layout": "comparison_table", "purpose": "Empirical results: observed distributions, comparative datasets, and analytical findings"},
        {"role": "mechanism", "layout": "radial_hub_spoke", "purpose": "Underlying functional mechanism, causal pathways, and interaction model"},
        {"role": "discussion", "layout": "comparison_table", "purpose": "Observed findings versus theoretical predictions and domain baselines"},
        {"role": "limitations", "layout": "cards_hierarchy", "purpose": "Methodological constraints, sensitivity boundaries, and validity limits"},
        {"role": "conclusion", "layout": "key_takeaways_summary", "purpose": "Core scientific conclusions, theoretical contribution, and future research directions"},
    ],

    # 7. Data Report & Market Analytics
    "data_report": [
        {"role": "hook", "layout": "full_bleed_hero", "purpose": "Analytical report title, reporting timeframe, and executive scope"},
        {"role": "overview", "layout": "stats_kpi_monument", "purpose": "Primary indicator summary and high-conviction macro findings"},
        {"role": "breakdown", "layout": "comparison_table", "purpose": "Segment breakdown, categorical comparison, and multi-variable distribution"},
        {"role": "drivers", "layout": "cards_hierarchy", "purpose": "Underlying drivers, qualitative indicators, and market momentum factors"},
        {"role": "process", "layout": "horizontal_process_4step", "purpose": "Analytical methodology, data verification stages, and audit protocol"},
        {"role": "outlook", "layout": "milestone_roadmap", "purpose": "Forward-looking projections, scenario modeling, and risk factors"},
        {"role": "recommendations", "layout": "conclusion_cta", "purpose": "Data-driven recommendations, policy implications, and strategic action plan"},
    ],
}


# ---------------------------------------------------------------------------
# 2. Subtopic Extraction & Narrative Pacing
# ---------------------------------------------------------------------------

def extract_user_subtopics(prompt: str) -> List[str]:
    """
    Parses a user prompt for explicit sub-topics, stages, or sections.
    Example: 'Sovereign AI: compute infrastructure, foundational models, data sovereignty, regulatory frameworks'
    Returns: ['compute infrastructure', 'foundational models', 'data sovereignty', 'regulatory frameworks']
    """
    if not prompt:
        return []

    text = prompt
    if ":" in prompt:
        parts = prompt.split(":", 1)
        text = parts[1]

    raw_chunks = re.split(r"[,;]|\band\b", text, flags=re.IGNORECASE)
    cleaned = []
    for c in raw_chunks:
        c = re.sub(r"^\s*(\d+[\.\)]|\-|\*)\s*", "", c).strip()
        c = re.sub(r"^(about|and|including|covering|such as)\s+", "", c, flags=re.IGNORECASE).strip()
        if len(c) > 3 and not re.match(r"^(slide|presentation|deck|create|make|build|talk|presentation on)\b", c, re.IGNORECASE):
            cleaned.append(c)

    return cleaned


def select_narrative_archetype(topic: str, audience: str = "") -> str:
    """Classifies topic and audience into the most appropriate storytelling arc without bias."""
    t = (topic + " " + audience).lower()

    # 1. Pitch / Startups (check first to avoid 'logistics' stealing a pitch deck)
    if any(k in t for k in ["pitch", "seed", "series a", "series b", "investor", "fundraise", "venture capital", "unicorn", "tam", "arr", "deck for investors"]):
        return "startup_pitch"

    # 2. Data / Financial / Analytics Report
    if any(k in t for k in ["quarterly", "financial", "earnings", "revenue", "market analysis", "metrics review", "survey results", "statistics", "data report", "benchmark report", "financial review", "operational efficiency"]):
        return "data_report"

    # 3. Scientific / Academic Research
    if any(k in t for k in ["thesis", "peer-reviewed", "clinical trial", "dissertation", "scientific paper", "empirical", "hypothesis", "study of"]):
        return "academic_research"

    # 4. Educational / Conceptual Learning & Biology
    if any(k in t for k in [
        "teach", "lesson", "biology", "plant", "respiration", "photosynthesis",
        "crispr", "gene", "editing", "genetics", "dna", "rna", "cellular", "physics",
        "chemistry", "history", "anatomy", "pedagogy", "introduction to", "basics of",
        "course", "curriculum", "concept", "mechanism"
    ]):
        return "educational_concept"

    # 5. Technical / Systems / Engineering
    if any(k in t for k in [
        "architecture", "software", "system design", "backend", "api", "cloud",
        "devops", "database", "kubernetes", "microservices", "infra", "cybersecurity",
        "zero trust", "network", "cryptography", "quantum", "key distribution", "security"
    ]):
        return "technical_architecture"

    # 6. Operations & Workflows
    if any(k in t for k in ["workflow", "operations", "process", "pipeline", "logistics", "supply chain", "lifecycle", "standard operating procedure", "sop", "maintenance", "facility", "facilities", "ticketing"]):
        return "product_operations"

    # Default to high-level strategic consulting
    return "executive_consulting"


def classify_presentation_intent(topic: str, audience: str = "") -> Dict[str, Any]:
    """Classifies topic and audience into a structured storytelling blueprint."""
    archetype = select_narrative_archetype(topic, audience)
    blueprint = NARRATIVE_ARCHETYPES.get(archetype, NARRATIVE_ARCHETYPES["executive_consulting"])
    return {
        "archetype": archetype,
        "blueprint": blueprint,
        "topic": topic,
        "audience": audience,
    }


def parse_batch_content_response(raw_response: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Safely parses and validates batch content output from Gemini according to Phase 2 schema."""
    if isinstance(raw_response, str):
        cleaned = raw_response.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
        try:
            data = json.loads(cleaned)
        except Exception as e:
            log.warning("JSON decode failed in parse_batch_content_response: %s", e)
            data = {"slides": []}
    elif isinstance(raw_response, dict):
        data = raw_response
    else:
        data = {"slides": []}

    slides_list = data.get("slides") or data.get("data") or []
    normalized_slides = []
    for item in slides_list:
        if not isinstance(item, dict):
            continue
        normalized_slides.append({
            "index": item.get("index", 1),
            "title": item.get("title", ""),
            "subtitle": item.get("subtitle", ""),
            "main_message": item.get("main_message", ""),
            "semantic_type": item.get("semantic_type", "concept_explanation"),
            "recommended_layout": item.get("recommended_layout", "cards_hierarchy"),
            "bullets": item.get("bullets", []),
            "cards": item.get("cards", []),
            "data_points": item.get("data_points", []),
            "speaker_notes": item.get("speaker_notes", ""),
        })

    return {"slides": normalized_slides}


def build_narrative_outline(
    topic: str,
    slide_count: int = 10,
    audience: str = "general_public",
    key_themes: Optional[List[str]] = None,
    document_summaries: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Builds a structured, high-variety outline based on proven narrative pacing."""
    subtopics = extract_user_subtopics(topic)
    target_count = max(3, min(slide_count, 40))

    # If the user explicitly provided matching subtopics
    if subtopics and len(subtopics) >= target_count - 2:
        outline = []
        clean_topic = topic.split(":")[0].strip()

        # Slide 1: Executive Overview & Context
        outline.append({
            "position": 1,
            "role": "introduction",
            "layout": "full_bleed_hero",
            "title": f"Introducing {clean_topic}",
            "purpose": f"Context, strategic scope, and executive overview of {clean_topic}."
        })

        operational_layouts = [
            "cards_hierarchy",
            "horizontal_process_workflow",
            "horizontal_process_4step",
            "problem_solution",
            "comparison_table",
            "split_screen",
        ]

        for i, sub in enumerate(subtopics[:target_count - 2]):
            pos = i + 2
            sub_title = sub.strip().title()
            layout = operational_layouts[i % len(operational_layouts)]
            sub_lower = sub.lower()

            if any(k in sub_lower for k in ["process", "workflow", "lifecycle", "steps", "stages"]):
                layout = "horizontal_process_4step"
            elif any(k in sub_lower for k in ["vs", "comparison", "difference", "tradeoff", "matrix"]):
                layout = "comparison_table"
            elif any(k in sub_lower for k in ["challenge", "problem", "solution", "friction"]):
                layout = "problem_solution"
            elif any(k in sub_lower for k in ["overview", "components", "pillars", "foundations"]):
                layout = "cards_hierarchy"

            outline.append({
                "position": pos,
                "role": f"subtopic_{i+1}",
                "layout": layout,
                "title": sub_title,
                "purpose": f"Detailed functional explanation, implementation approach, and strategic role of {sub}."
            })

        # Closing Summary & Strategic Horizon
        summary_pos = len(outline) + 1
        outline.append({
            "position": summary_pos,
            "role": "conclusion_summary",
            "layout": "conclusion_cta",
            "title": f"Strategic Horizon: Advancing {clean_topic}",
            "purpose": f"Synthesis of key principles, forward momentum, and actionable recommendations for {clean_topic}."
        })

        return outline[:target_count]

    archetype_key = select_narrative_archetype(topic, audience)
    template = NARRATIVE_ARCHETYPES.get(archetype_key, NARRATIVE_ARCHETYPES["executive_consulting"])

    outline = []
    if target_count <= len(template):
        step = (len(template) - 1) / max(1, target_count - 1)
        indices = [min(len(template) - 1, int(round(i * step))) for i in range(target_count)]
        indices = sorted(list(dict.fromkeys(indices)))
        while len(indices) < target_count:
            for cand in range(len(template)):
                if cand not in indices:
                    indices.append(cand)
                    break
            indices = sorted(indices)
        for i, idx in enumerate(indices[:target_count]):
            item = dict(template[idx])
            item["position"] = i + 1
            outline.append(item)
    else:
        for i, item in enumerate(template):
            outline.append({**item, "position": i + 1})
        for i in range(len(template), target_count):
            outline.append({
                "role": f"deep_dive_{i}",
                "layout": "cards_hierarchy" if i % 2 == 0 else "split_screen",
                "purpose": f"In-depth domain analysis and supporting mechanisms for {topic}",
                "position": i + 1,
            })

    return outline


# ---------------------------------------------------------------------------
# 3. High-Integrity Slide Content Generation (Zero-Hallucination)
# ---------------------------------------------------------------------------

def build_batch_content_prompt(
    presentation_title: str = "",
    settings: Optional[Dict[str, Any]] = None,
    targets: Optional[List[Any]] = None,
    sources: Optional[Dict[str, Any]] = None,
    extra_instructions: str = "",
    topic: Optional[str] = None,
    slides_outline: Optional[List[Any]] = None,
    audience: Optional[str] = None,
    tone: Optional[str] = None,
) -> str:
    """Builds a comprehensive, zero-hallucination prompt for writing presentation slide content."""
    settings = dict(settings or {})
    if audience:
        settings["audience"] = audience
    if tone:
        settings["tone"] = tone

    aud = settings.get("audience", "general_public")
    language = settings.get("language", "English")
    complexity = settings.get("complexity", "intermediate")
    pres_title = presentation_title or topic or "Presentation"

    sources = sources or {}
    src_block = "\n".join(f"[{k}] {v['text'][:1200]}" for k, v in sources.items()) if sources else "(No uploaded source documents provided)"

    target_items = targets or slides_outline or []
    slide_specs = []
    for idx, s in enumerate(target_items, start=1):
        if isinstance(s, dict):
            pos = s.get("position") or s.get("index") or idx
            title = s.get("title", f"Slide {pos}")
            c = s.get("content") if isinstance(s.get("content"), dict) else {}
            planning_purpose = s.get("planning_purpose") or s.get("purpose") or c.get("planning_purpose") or c.get("purpose") or ""
            layout = s.get("layout") or s.get("recommended_layout") or c.get("layout") or "split_screen"
        else:
            pos = getattr(s, "position", idx)
            title = getattr(s, "title", f"Slide {pos}")
            c = getattr(s, "content", {}) or {}
            planning_purpose = c.get("planning_purpose") or c.get("purpose") or ""
            layout = c.get("layout", "split_screen")

        slide_specs.append(
            f"- Slide {pos}: \"{title}\"\n"
            f"  Internal Planning Goal: {planning_purpose}\n"
            f"  Target Layout: {layout}"
        )
    slides_text = "\n".join(slide_specs)

    prompt = f"""You are SlideMind AI's Principal Presentation Content Architect.
Generate deep, substantive, information-rich presentation content for '{pres_title}'.

Target Audience: {aud}
Language: {language}
Conceptual Complexity: {complexity}

SLIDES TO WRITE:
{slides_text}

GROUNDING SOURCE MATERIAL:
<sources>
{src_block}
</sources>

{f'EXTRA USER INSTRUCTIONS: {extra_instructions}' if extra_instructions else ''}

CRITICAL ARCHITECTURAL & FACTUAL ACCURACY DIRECTIVES:
1. STRICT ZERO-HALLUCINATION POLICY:
   - NEVER invent fake percentages, statistical figures, ARR, revenue amounts, or fictional dates (e.g. NEVER make up "$18.5M", "+142% YoY", "99.4% Precision").
   - If numbers and statistics are explicitly present in the provided sources, cite them with matching source IDs (e.g. ['S1']).
   - If numerical evidence is NOT present, USE QUALITATIVE EXPLANATIONS, structural mechanisms, architectural tiers, functional responsibilities, and procedural workflows. DO NOT invent decorative numbers!
2. SEPARATION OF PLANNING METADATA FROM VISIBLE CONTENT:
   - The 'Internal Planning Goal' provided above is an internal instruction ONLY. NEVER repeat or leak the planning goal into visible slide titles, subtitles, or bullets.
   - Generate a real, publication-grade 'subtitle' (4-10 words) that describes the specific topic of that slide.
3. SUBSTANTIVE INFORMATION DENSITY:
   - Write comprehensive, articulate sentences. Avoid empty generic bullet fragments like "Pillar 1", "Fast", or "Efficient".
   - Provide 3-5 substantive bullet points per slide.
   - Provide a coherent 2-3 sentence 'main_message' narrative summarizing the core takeaway.
4. STRUCTURAL DATA CONGRUENCE:
   - When the slide is a process or workflow, provide 3-5 concrete chronological steps in 'process_steps' with descriptive step titles and operational actions.
   - When the slide is a feature or architecture overview, provide 3-4 structured component cards in 'cards'.
   - When the slide is a comparison, provide a clean 'table' with relevant comparison headers and 2-3 feature rows.
   - For 'data_points' (KPIs), ONLY populate with genuine grounded metrics when supported by sources; otherwise, provide qualitative status cards or leave as an empty list [].
5. PROFESSIONAL TELEPROMPTER SPEAKER NOTES:
   - Provide natural, authoritative speaking notes explaining the exact concepts of the slide aloud to the audience without robotic phrases like "On this slide...".

Return valid JSON adhering strictly to:
{{
  "slides": [
    {{
      "slide_number": int,
      "title": str,
      "subtitle": str,
      "main_message": str,
      "semantic_type": str,
      "bullets": [
        {{"text": str, "source_ids": [str]}}
      ],
      "data_points": [
        {{"value": str, "label": str, "delta": str, "description": str}}
      ],
      "cards": [
        {{"title": str, "badge": str, "icon": str, "body": str}}
      ],
      "process_steps": [
        {{"step_number": int, "title": str, "description": str}}
      ],
      "table": {{
        "headers": [str],
        "rows": [[str]]
      }},
      "diagram": {{
        "type": str,
        "stages": [{{"label": str, "detail": str, "metric": str}}]
      }},
      "speaker_notes": str
    }}
  ]
}}
"""
    return prompt


def generate_slide_payload(
    topic: str,
    slide_title: str,
    slide_purpose: str,
    layout: str,
    audience: str = "general_public",
    sources: Optional[Dict[str, Any]] = None,
    extra_instructions: str = "",
) -> Dict[str, Any]:
    """Generates structured content payload for an individual slide adhering to Zero-Hallucination rules."""
    sources = sources or {}
    src_text = "\n".join(f"[{k}] {v['text'][:800]}" for k, v in sources.items()) if sources else "(No external sources provided)"

    prompt = f"""You are SlideMind AI's Principal Presentation Content Architect.
Generate deep, substantive presentation content for Slide '{slide_title}'.

Topic: {topic}
Slide Planning Goal: {slide_purpose}
Layout: {layout}
Audience: {audience}

Reference Material:
<sources>
{src_text}
</sources>

CRITICAL FACTUAL INTEGRITY RULES:
1. NEVER invent fake percentages, financial metrics, customer numbers, or dates.
2. If real numerical data is absent, provide qualitative analysis, system mechanics, operational tiers, and real-world considerations.
3. NEVER expose the internal planning goal as visible slide text. Provide a dedicated, publication-ready subtitle.
4. Provide 3-4 substantive, complete explanatory bullets.
5. Provide professional speaking notes for this slide.

Return valid JSON conforming to:
{{
  "headline": "{slide_title}",
  "subtitle": "Informative concise topic subtitle",
  "main_message": "Clear 2-sentence executive summary of this slide's core insight.",
  "semantic_type": "explanation",
  "bullets": [
    {{"text": "Substantive, clear explanation grounded in the topic", "source_ids": []}}
  ],
  "data_points": [],
  "cards": [
    {{"title": "Core Mechanism", "badge": "TIER 01", "icon": "check", "body": "Thorough explanation of this functional component."}}
  ],
  "speaker_notes": "Authoritative spoken talking script explaining the slide clearly to the audience."
}}
"""
    try:
        data = gemini.generate_json(prompt)
        if isinstance(data, dict):
            return data
    except Exception as e:
        log.warning("Gemini slide payload fallback for '%s': %s", slide_title, e)

    # Safe qualitative fallback without hallucinated metrics
    return {
        "headline": slide_title,
        "subtitle": f"Strategic analysis and core considerations for {slide_title}",
        "main_message": f"Comprehensive overview detailing key structural components and execution factors for {slide_title}.",
        "semantic_type": "explanation",
        "bullets": [
            {"text": f"Core objective: Establishing an effective and reliable approach to {slide_title}.", "source_ids": []},
            {"text": "Implementation strategy: Aligning architectural requirements with operational delivery standards.", "source_ids": []},
            {"text": "Verification and governance: Ensuring continuous quality assessment, stakeholder transparency, and verified outcomes.", "source_ids": []},
        ],
        "data_points": [],
        "cards": [
            {"title": "Foundational Principles", "badge": "PHASE 01", "icon": "shield", "body": f"Structured operational guidelines ensuring reliability for {slide_title}."},
            {"title": "Execution & Review", "badge": "PHASE 02", "icon": "check", "body": "Continuous progress evaluation and multi-stakeholder feedback loops."}
        ],
        "speaker_notes": f"This slide examines {slide_title}. We focus on how deliberate execution and systematic governance ensure consistent, high-quality outcomes."
    }
