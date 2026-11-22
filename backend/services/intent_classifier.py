"""Intent classification service for SlideMind AI chat.

Reliably categorizes user messages into one of:
1. INTENT_NORMAL_CHAT: greetings, general questions, explanations of concepts,
   chit-chat, and requests to explain/summarize an existing presentation.
2. INTENT_CREATE_PRESENTATION: requests to build a brand new presentation from scratch.
3. INTENT_EDIT_PRESENTATION: explicit instructions to modify/update an existing active presentation.
4. INTENT_AMBIGUOUS: statements where the user's intent to explain vs modify is unclear.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from services import gemini

log = logging.getLogger(__name__)

INTENT_NORMAL_CHAT = "normal_chat"
INTENT_CREATE_PRESENTATION = "create_presentation"
INTENT_EDIT_PRESENTATION = "edit_presentation"
INTENT_AMBIGUOUS = "ambiguous"


@dataclass
class IntentResult:
    intent: str
    confidence: float = 1.0
    topic: str = ""
    slide_count: int = 6
    clarification: str = ""
    details: dict = field(default_factory=dict)


# Common greetings and conversational patterns (always normal chat)
GREETINGS_PATTERN = re.compile(
    r"^(hi+|hey+|hello+|howdy|yo|greetings|good\s+(morning|afternoon|evening|night|day)|what\'?s\s+up|sup|hlo|hii+)\b",
    re.IGNORECASE,
)

CONVERSATIONAL_QUESTIONS = re.compile(
    r"^(how\s+are\s+you|how\s+are\s+things|how\'?s\s+it\s+going|what\s+can\s+you\s+do|who\s+are\s+you|"
    r"what\s+is\s+slidemind|tell\s+me\s+about\s+yourself|what\s+do\s+you\s+do|can\s+you\s+help\s+me)\b",
    re.IGNORECASE,
)

GRATITUDE_CLOSINGS = re.compile(
    r"^(thanks?(\s+you)?|thank\s+you(\s+so\s+much)?|great(\s+job)?|awesome|cool|ok|okay|bye|goodbye|see\s+ya|"
    r"sounds\s+good|perfect|nice|wonderful|cheers)\b",
    re.IGNORECASE,
)

# Inquiries asking for explanations or summaries of the presentation (read-only, NOT an edit)
PRESENTATION_EXPLANATION_PATTERN = re.compile(
    r"^(can\s+you\s+|please\s+)?(explain|summarize|tell\s+me\s+about|walk\s+me\s+through|what\s+is|what\s+are|"
    r"describe|review|break\s+down|give\s+me\s+an?\s+overview\s+of)\s+"
    r"(my|this|the|our)?\s*(presentation|deck|ppt|slides?)\b|"
    r"^what\s+(is|does|are)\s+(on\s+)?slide\s*\d+\b|"
    r"^what\s+is\s+(this|my|the)\s+(presentation|deck|ppt)\s+about\b|"
    r"^explain\s+slide\s*\d+\b|"
    r"^tell\s+me\s+about\s+slide\s*\d+\b",
    re.IGNORECASE,
)

# General concept explanation patterns without presentation references
GENERAL_EXPLANATION_PATTERN = re.compile(
    r"^(explain|tell\s+me\s+about|what\s+is|what\s+are|how\s+does|how\s+do|define|describe|why\s+is)\s+"
    r"(?!.*?\b(presentation|deck|ppt|slides?)\b).*",
    re.IGNORECASE,
)

# Creation triggers
CREATION_TRIGGERS = [
    "create a presentation", "create presentation", "make a presentation", "generate a presentation",
    "build a presentation", "design a presentation", "create a deck", "create slide deck", "make a deck",
    "generate a deck", "build a deck", "create a pitch deck", "create slides", "make slides", "generate slides",
    "presentation about", "presentation on", "presentation for", "deck about", "deck on", "deck for",
    "slides about", "slides on", "slides for", "create a ppt", "create ppt", "make a ppt", "make ppt",
    "generate a ppt", "generate ppt", "build a ppt", "build ppt", "ppt about", "ppt on", "ppt for",
    "give me a ppt", "give me a presentation", "give me slides", "create a powerpoint", "create powerpoint",
    "make a powerpoint", "make powerpoint", "powerpoint on", "powerpoint about", "powerpoint for",
]

CREATION_VERB_NOUN_PATTERN = re.compile(
    r"\b(create|generate|make|build|design|prepare|draft|give\s+me)\b.*?\b(ppt|ppts|powerpoint|power\s*point|presentation|presentations|deck|decks|slides)\b",
    re.IGNORECASE,
)

CREATION_DIRECT_TOPIC_PATTERN = re.compile(
    r"^(ppt|powerpoint|presentation|deck|slides)\s+(on|about|for|regarding)\b",
    re.IGNORECASE,
)

# Explicit presentation edit patterns (modifications to slides, layout, theme, content)
EDIT_IMPERATIVE_VERBS = (
    r"(change|update|edit|rewrite|modify|replace|swap|fix|adjust|shorten|expand|"
    r"rephrase|reword|improve|revise|enhance|restyle|reorganize|reorder|move|delete|remove|drop|cut)"
)

EDIT_TARGETS = (
    r"(slide\s*\d+|slides\s*\d+|first\s+slide|last\s+slide|next\s+slide|previous\s+slide|"
    r"this\s+slide|current\s+slide|title|headline|subtitle|image|photo|picture|graphic|"
    r"visual|bullet|bullets|bullet\s*points?|speaker\s*notes?|notes|theme|style|color|"
    r"layout|font|spacing|diagram|chart|header|footer)"
)

EDIT_ADD_SLIDE_PATTERN = re.compile(
    r"\b(add|insert|create|include|append)\s+(a\s+)?(new\s+)?("
    r"conclusion|summary|intro|introduction|agenda|next\s+steps|closing|final|extra|additional|"
    r"qa|q&a|timeline|case\s+study|market|pricing|team|overview)?\s*slide\b|"
    r"\b(add|insert)\s+slide\s*\d*\b",
    re.IGNORECASE,
)

EDIT_ACTION_PATTERN = re.compile(
    rf"\b{EDIT_IMPERATIVE_VERBS}\b.*?\b{EDIT_TARGETS}\b|"
    rf"\b{EDIT_TARGETS}\b.*?\b{EDIT_IMPERATIVE_VERBS}\b|"
    r"\bmake\s+(the\s+)?presentation\s+(more\s+)?(professional|concise|modern|executive|clean|engaging|dark|light|colorful)\b|"
    r"\bchange\s+(the\s+)?theme\b|"
    r"\bapply\s+(the\s+)?(theme|design\s+system)\b",
    re.IGNORECASE,
)

AMBIGUOUS_CRITIQUE_PATTERN = re.compile(
    r"\b(slide\s*\d+|the\s+presentation|this\s+deck|the\s+slides?)\b.*?\b(is\s+too|seems\s+too|feels\s+too|looks\s+too|"
    r"a\s+bit\s+too|not\s+good|a\s+little|confusing|boring|weak|crowded|wordy|cluttered|messy)\b",
    re.IGNORECASE,
)


def extract_creation_details(text: str) -> tuple[str, int]:
    """Extracts topic and slide count from a creation prompt."""
    low = text.lower().strip()
    slide_match = re.search(r"\b(\d{1,2})\s*[- ]?slides?\b", low)
    slide_count = int(slide_match.group(1)) if slide_match else 6
    slide_count = max(3, min(slide_count, 15))

    clean = re.sub(
        r"^(please\s+)?(can\s+you\s+)?(i\s+want\s+(a\s+)?|i\s+need\s+(a\s+)?|build\s+me\s+(a\s+)?|make\s+me\s+(a\s+)?)?"
        r"(create|generate|make|build|design|prepare|draft|give\s+me)\s+(a\s+|an\s+)?(new\s+)?"
        r"(\d{1,2}\s*[- ]?slides?\s+)?(presentation|deck|slide\s+deck|slides|ppt|ppts|powerpoint|power\s*point)\s+"
        r"(about|on|for|in|regarding)?\s*",
        "", text, flags=re.IGNORECASE
    ).strip()

    clean = re.sub(r"^(ppt|powerpoint|presentation|deck|slides)\s+(about|on|for|in|regarding)\s*", "", clean, flags=re.IGNORECASE).strip()
    clean = clean.strip("\"' ")
    topic = clean if len(clean) >= 2 else text
    return topic, slide_count


def classify_by_rules(text: str, has_active_presentation: bool = False) -> Optional[IntentResult]:
    """Deterministic rule-based intent classifier. Returns IntentResult or None if uncertain."""
    raw = text.strip()
    low = raw.lower()

    if not raw:
        return IntentResult(INTENT_NORMAL_CHAT, confidence=1.0)

    # 1. Greetings and pleasantries
    if GREETINGS_PATTERN.match(raw) or CONVERSATIONAL_QUESTIONS.match(raw) or GRATITUDE_CLOSINGS.match(raw):
        # Unless the user explicitly tagged on a presentation creation command in the same sentence
        if not CREATION_VERB_NOUN_PATTERN.search(low):
            return IntentResult(INTENT_NORMAL_CHAT, confidence=1.0)

    # 2. Informational questions about presentations (read-only, NOT an edit)
    # Examples: "explain my presentation", "summarize this deck", "what is on slide 2?"
    if PRESENTATION_EXPLANATION_PATTERN.search(low):
        # Explicit check: user is asking to explain or describe, NOT to change
        if not re.search(r"\b(change|update|edit|rewrite|replace|add|delete|remove)\b", low):
            return IntentResult(INTENT_NORMAL_CHAT, confidence=1.0)

    # 3. General knowledge questions (e.g. "explain artificial intelligence", "tell me about python")
    if GENERAL_EXPLANATION_PATTERN.match(raw) and not any(trig in low for trig in CREATION_TRIGGERS):
        return IntentResult(INTENT_NORMAL_CHAT, confidence=1.0)

    # 4. Check for presentation creation requests
    has_creation_trigger = any(trig in low for trig in CREATION_TRIGGERS)
    has_creation_pattern = bool(CREATION_VERB_NOUN_PATTERN.search(low) or CREATION_DIRECT_TOPIC_PATTERN.search(low))

    # Guard: if the user mentions specific existing slides or edit targets, it's NOT a new creation
    has_slide_target = bool(re.search(
        r"\b(slide\s*\d+|slides\s*\d+|first\s+slide|last\s+slide|this\s+slide|current\s+slide)\b",
        low,
    ))

    # Guard: if user says "add a conclusion slide", "add slide 3", that is an edit, not full deck creation
    is_add_slide = bool(EDIT_ADD_SLIDE_PATTERN.search(low))

    if (has_creation_trigger or has_creation_pattern) and not has_slide_target and not is_add_slide:
        # If there is an active presentation, only trigger creation if explicitly requesting a NEW/FRESH deck
        if has_active_presentation:
            is_explicit_new = bool(re.search(
                r"\b(new\s+(presentation|deck|ppt|slides)|another\s+(presentation|deck|ppt)|different\s+(presentation|deck|ppt)|fresh\s+(presentation|deck|ppt)|start\s+over)\b",
                low,
            ))
            if is_explicit_new:
                topic, slide_count = extract_creation_details(raw)
                return IntentResult(INTENT_CREATE_PRESENTATION, confidence=1.0, topic=topic, slide_count=slide_count)
        else:
            topic, slide_count = extract_creation_details(raw)
            return IntentResult(INTENT_CREATE_PRESENTATION, confidence=1.0, topic=topic, slide_count=slide_count)

    # 5. Check for presentation editing requests (ONLY if there is an active presentation)
    if is_add_slide or EDIT_ACTION_PATTERN.search(low):
        if has_active_presentation:
            return IntentResult(INTENT_EDIT_PRESENTATION, confidence=0.95)
        else:
            # User wants to edit but no active presentation exists
            return IntentResult(
                INTENT_NORMAL_CHAT,
                confidence=0.9,
                clarification="You don't have an active presentation open to edit. Would you like to create one first?",
            )

    # 6. Check for ambiguous critique / feedback
    if AMBIGUOUS_CRITIQUE_PATTERN.search(low) and has_active_presentation:
        return IntentResult(
            INTENT_AMBIGUOUS,
            confidence=0.85,
            clarification=(
                "Would you like me to explain and suggest improvements in chat, "
                "or should I directly update your presentation with changes?"
            ),
        )

    # Default for conversational text without presentation edit/create cues
    if not has_active_presentation:
        return IntentResult(INTENT_NORMAL_CHAT, confidence=0.9)

    return None


def classify_with_gemini(text: str, has_active_presentation: bool = False, active_title: str = "") -> Optional[IntentResult]:
    """Uses Gemini structured output to classify ambiguous or complex user requests."""
    if not gemini.is_configured():
        return None

    prompt = f"""You are an intent classifier for SlideMind AI, a presentation generation studio.
Analyze the user's message and categorize it into exactly one of these intents:

1. 'normal_chat':
   - Greetings, casual chat, small talk, gratitude.
   - General domain questions (e.g., 'explain AI', 'tell me about Python').
   - Informational questions about the presentation (e.g., 'explain my presentation', 'summarize this deck', 'what is on slide 2?').
   - Questions asking for advice, feedback, or ideas without requesting an actual change to the slides.

2. 'create_presentation':
   - Explicit instructions to generate a brand new slide deck (e.g., 'Create a 10-slide presentation about artificial intelligence', 'Make a PowerPoint about climate change').

3. 'edit_presentation':
   - Explicit instructions to update, modify, add slides to, delete slides from, or restyle an existing presentation.
   - ONLY valid if an active presentation exists.

4. 'ambiguous':
   - Ambiguous critique where it is unclear whether the user wants advice/explanation in chat or an actual edit to the presentation.

Context:
- Active presentation exists: {has_active_presentation}
- Active presentation title: "{active_title or 'None'}"
- User message: "{text}"

Return JSON matching this schema:
{{
  "intent": "normal_chat" | "create_presentation" | "edit_presentation" | "ambiguous",
  "confidence": 0.0 to 1.0,
  "topic": "string (only if create_presentation)",
  "slide_count": integer (only if create_presentation, default 6),
  "clarification": "string (only if ambiguous)"
}}"""

    try:
        data = gemini.generate_json(
            prompt=prompt,
            system="You are a strict, precise intent classifier. Return valid JSON only.",
            temperature=0.1,
        )
        intent = data.get("intent", INTENT_NORMAL_CHAT)
        if intent not in (INTENT_NORMAL_CHAT, INTENT_CREATE_PRESENTATION, INTENT_EDIT_PRESENTATION, INTENT_AMBIGUOUS):
            intent = INTENT_NORMAL_CHAT

        if intent == INTENT_EDIT_PRESENTATION and not has_active_presentation:
            intent = INTENT_NORMAL_CHAT

        return IntentResult(
            intent=intent,
            confidence=float(data.get("confidence", 0.9)),
            topic=str(data.get("topic", "")),
            slide_count=int(data.get("slide_count", 6) or 6),
            clarification=str(data.get("clarification", "")),
            details=data,
        )
    except Exception as e:
        log.warning("AI intent classification fallback due to error: %s", e)
        return None


def classify_chat_intent(
    text: str,
    has_active_presentation: bool = False,
    active_title: str = "",
) -> IntentResult:
    """Classifies user chat intent using deterministic rules first, falling back to Gemini if ambiguous.
    
    Guarantees:
    - Normal chat messages ('Hi', 'Hello', 'Explain AI', 'Explain my presentation') are NEVER classified as edits.
    - Presentation edit is ONLY triggered when user explicitly requests modifications AND an active presentation exists.
    - Presentation creation is ONLY triggered on real creation requests.
    """
    rule_result = classify_by_rules(text, has_active_presentation=has_active_presentation)
    if rule_result is not None and rule_result.confidence >= 0.9:
        return rule_result

    # If rules are uncertain and Gemini is configured, use AI classification
    if gemini.is_configured():
        ai_result = classify_with_gemini(text, has_active_presentation=has_active_presentation, active_title=active_title)
        if ai_result is not None:
            return ai_result

    # Fallback to rule result if available, or default safely to normal chat
    if rule_result is not None:
        return rule_result

    return IntentResult(INTENT_NORMAL_CHAT, confidence=0.8)
