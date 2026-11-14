import re
from flask import Blueprint, current_app, g, request

from database import db
from agents.agent import run_agent, used_citations
from agents.registry import ToolContext
from models import Conversation, Message, Presentation, Document
from services import gemini, google_auth
from utils.http import clean_text, fail, ok, require_auth

bp = Blueprint("conversations", __name__, url_prefix="/api")


def _conv_dict(c: Conversation):
    return {
        "id": c.id,
        "title": c.title,
        "active_presentation_id": c.active_presentation_id,
        "updated_at": c.updated_at.isoformat(),
    }


def _is_creation_request(text: str, has_active_presentation: bool = False) -> tuple[bool, str, int]:
    """Detects if user is asking to create a presentation. Returns (is_request, topic, slide_count)."""
    low = text.lower().strip()

    # If the user is referring to an existing slide or asking for modifications, NEVER trigger a new creation job
    has_slide_target = bool(re.search(r"\b(slide\s*\d+|slides\s*\d+|first\s+slide|last\s+slide|next\s+slide|previous\s+slide|this\s+slide|these\s+slides|current\s+slide)\b", low))
    has_edit_verbs = bool(re.search(r"\b(edit|change|update|rewrite|modify|refine|adjust|tweak|fix|shorten|expand|simplify|format|rephrase|reword|improve|revise|enhance|restyle|reorganize)\b", low))
    has_edit_terms = bool(re.search(r"\b(bullet|bullets|bullet\s*points|headline|speaker\s*notes|diagram|chart|theme|style|color|layout|font|spacing)\b", low))
    has_deck_reference = bool(re.search(r"\b(in\s+this\s+presentation|in\s+this\s+deck|in\s+the\s+presentation|in\s+the\s+deck|to\s+this\s+deck|to\s+this\s+presentation|this\s+ppt|this\s+deck)\b", low))

    if has_slide_target or (has_edit_verbs and (has_edit_terms or has_deck_reference or has_active_presentation)):
        return False, "", 6

    if low.startswith(("edit", "change", "update", "why", "how", "what", "who", "when", "where", "can you explain", "rewrite", "replace", "delete", "add a slide", "add slide", "insert slide", "new slide", "make slide", "make the slide", "turn slide", "convert slide")):
        return False, "", 6

    # If there is already an active presentation in the conversation, only trigger creation if explicitly requesting a NEW/FRESH deck
    if has_active_presentation:
        is_explicit_new = bool(re.search(r"\b(new\s+(presentation|deck|ppt|slides)|another\s+(presentation|deck|ppt)|different\s+(presentation|deck|ppt)|fresh\s+(presentation|deck|ppt)|start\s+over)\b", low))
        if not is_explicit_new:
            return False, "", 6

    # 1. Explicit triggers including ppt, powerpoint, presentation, deck, slides
    creation_triggers = [
        "create a presentation", "create presentation", "make a presentation", "generate a presentation",
        "build a presentation", "design a presentation", "create a deck", "create slide deck", "make a deck",
        "generate a deck", "build a deck", "create a pitch deck", "create slides", "make slides", "generate slides",
        "presentation about", "presentation on", "presentation for", "deck about", "deck on", "deck for",
        "slides about", "slides on", "slides for", "create a ppt", "create ppt", "make a ppt", "make ppt",
        "generate a ppt", "generate ppt", "build a ppt", "build ppt", "ppt about", "ppt on", "ppt for",
        "give me a ppt", "give me a presentation", "give me slides", "create a powerpoint", "create powerpoint",
        "make a powerpoint", "make powerpoint", "powerpoint on", "powerpoint about", "powerpoint for"
    ]
    has_trigger = any(trig in low for trig in creation_triggers)

    # 2. Pattern based match: (action verb) ... (ppt / powerpoint / presentation / deck / slides)
    pattern = r"\b(create|generate|make|build|design|prepare|draft|give\s+me|need|want)\b.*?\b(ppt|ppts|powerpoint|power\s*point|presentation|presentations|deck|decks|slides)\b"
    has_pattern = bool(re.search(pattern, low))

    # 3. Direct topic pattern: "ppt on ...", "presentation for ..."
    direct_topic_pattern = r"^(ppt|powerpoint|presentation|deck|slides)\s+(on|about|for|regarding)\b"
    has_direct_topic = bool(re.search(direct_topic_pattern, low))

    if not (has_trigger or has_pattern or has_direct_topic):
        return False, "", 6

    slide_match = re.search(r"\b(\d{1,2})\s*[- ]?slides?\b", low)
    slide_count = int(slide_match.group(1)) if slide_match else 6
    slide_count = max(3, min(slide_count, 15))

    clean = re.sub(
        r"^(please\s+)?(can you\s+)?(i\s+want\s+(a\s+)?|i\s+need\s+(a\s+)?|build\s+me\s+(a\s+)?|make\s+me\s+(a\s+)?)?(create|generate|make|build|design|prepare|draft|give\s+me)\s+(a\s+|an\s+)?(new\s+)?(\d{1,2}\s*[- ]?slides?\s+)?(presentation|deck|slide deck|slides|ppt|ppts|powerpoint|power\s*point)\s+(about|on|for|in|regarding)?\s*",
        "", text, flags=re.IGNORECASE
    ).strip()

    clean = re.sub(r"^(ppt|powerpoint|presentation|deck|slides)\s+(about|on|for|in|regarding)\s*", "", clean, flags=re.IGNORECASE).strip()
    clean = clean.strip("\"' ")
    topic = clean if len(clean) >= 2 else text
    return True, topic, slide_count


@bp.get("/history")
@require_auth
def history():
    convs = (
        Conversation.query.filter_by(user_id=g.user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
        .all()
    )
    return ok([_conv_dict(c) for c in convs])


@bp.post("/conversations")
@require_auth
def create_conversation():
    c = Conversation(user_id=g.user.id)
    db.session.add(c)
    db.session.commit()
    return ok(_conv_dict(c), 201)


@bp.get("/conversations/<conv_id>")
@require_auth
def get_conversation(conv_id):
    c = Conversation.query.filter_by(id=conv_id, user_id=g.user.id).first()
    if not c:
        return fail("not_found", "Conversation not found.", 404)
    data = _conv_dict(c)
    data["messages"] = [
        {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat(),
         "citations": (m.meta or {}).get("citations", []),
         "tool_calls": (m.meta or {}).get("tool_calls", []),
         "presentation_id": (m.meta or {}).get("presentation_id"),
         "job_id": (m.meta or {}).get("job_id")}
        for m in c.messages
    ]
    # Check if there is an active background job for this conversation
    from services import jobs
    running_job = jobs.active_job_for(g.user.id, conversation_id=c.id)
    if not running_job:
        running_job = jobs.active_job_for(g.user.id)
        if running_job and (running_job.payload or {}).get("conversation_id") != c.id:
            running_job = None
    if running_job:
        data["active_job"] = jobs.job_dict(running_job)
    return ok(data)


@bp.delete("/conversations/<conv_id>")
@require_auth
def delete_conversation(conv_id):
    c = Conversation.query.filter_by(id=conv_id, user_id=g.user.id).first()
    if not c:
        return fail("not_found", "Conversation not found.", 404)
    db.session.delete(c)
    db.session.commit()
    return ok({"deleted": conv_id})


@bp.post("/chat")
@require_auth
def chat():
    """Persists the user's message and runs the Gemini tool-calling agent on the recent history.
    Errors are reported honestly; no reply is ever fabricated."""
    data = request.get_json(silent=True) or {}
    raw_text = data.get("message")
    conv_id = data.get("conversation_id")
    if not isinstance(raw_text, str) or not clean_text(raw_text):
        return fail("invalid_request", "A non-empty 'message' is required.")

    # Extract clean style & deep research preferences, stripping ugly bracketed prefixes if present
    style = data.get("style")
    deep_research = bool(data.get("deep_research", False))
    density = data.get("density", "detailed")

    clean_msg = raw_text.strip()
    style_match = re.search(r'\[Style:\s*([^\]]+)\]', clean_msg, re.IGNORECASE)
    if style_match:
        if not style:
            style = style_match.group(1).strip()
        clean_msg = re.sub(r'\[Style:\s*[^\]]+\]', '', clean_msg, flags=re.IGNORECASE).strip()

    if re.search(r'\[Deep Research\]', clean_msg, re.IGNORECASE):
        deep_research = True
        clean_msg = re.sub(r'\[Deep Research\]', '', clean_msg, flags=re.IGNORECASE).strip()

    text = clean_msg if clean_msg else clean_text(raw_text)

    c = Conversation.query.filter_by(id=conv_id, user_id=g.user.id).first() if conv_id else None
    if conv_id and not c:
        return fail("not_found", "Conversation not found.", 404)
    if not c:
        c = Conversation(user_id=g.user.id)
        db.session.add(c)
        db.session.flush()

    pres_id = data.get("presentation_id")
    if pres_id is not None:
        if isinstance(pres_id, str) and Presentation.query.filter_by(id=pres_id, user_id=g.user.id).first():
            c.active_presentation_id = pres_id
    db.session.add(Message(conversation_id=c.id, role="user", content=text))
    if c.title == "New chat":
        c.title = text[:60]
    db.session.commit()

    from services import jobs
    running = jobs.active_job_for(g.user.id)
    if running:
        return fail("job_in_progress", "A request is already in progress. Please wait for it to finish.", 409,
                    {"job_id": running.id, "conversation_id": c.id})

    is_create, topic, slide_count = _is_creation_request(text, has_active_presentation=bool(c.active_presentation_id or pres_id))
    if is_create:
        if getattr(g.user, "is_guest", False):
            limit = current_app.config.get("GUEST_MAX_PRESENTATIONS", 3)
            count = Presentation.query.filter_by(user_id=g.user.id).count()
            if count >= limit:
                return fail("guest_limit_reached",
                            f"Guest accounts are limited to {limit} presentations. Sign in with Google to create unlimited presentations.",
                            403, {"limit": limit, "count": count, "conversation_id": c.id})

        doc_ids = data.get("document_ids", [])
        if not isinstance(doc_ids, list):
            doc_ids = []
        docs = Document.query.filter(Document.user_id == g.user.id, Document.status == "indexed", Document.id.in_(doc_ids)).all() if doc_ids else []
        doc_names = [d.filename for d in docs]

        params = {
            "topic": topic,
            "slide_count": slide_count,
            "duration_minutes": None,
            "audience": "college_students",
            "theme": style or "modern_light",
            "citation_style": "APA",
            "complexity": "intermediate",
            "language": "English",
            "use_web_research": deep_research,
            "publish": False,
            "document_ids": [d.id for d in docs]
        }
        job = jobs.start_generation(current_app._get_current_object(), g.user.id, params, doc_names, conversation_id=c.id)
        reply = f"Generating a {slide_count}-slide presentation on **{topic}**..."
        return ok({
            "conversation_id": c.id,
            "job_id": job.id,
            "status": "generating",
            "reply": reply,
            "active_presentation_id": c.active_presentation_id
        }, 202)

    has_active_pres = bool(c.active_presentation_id or pres_id)
    if has_active_pres:
        job = jobs.start_edit(
            current_app._get_current_object(),
            g.user.id,
            conversation_id=c.id,
            presentation_id=c.active_presentation_id,
            message=text,
            style=style,
            deep_research=deep_research,
            density=density,
            run_agent_fn=run_agent,
        )
        reply = (job.result.get("summary") if (job.result and job.status == "done") else "Updating your presentation with requested changes...")
        return ok({
            "conversation_id": c.id,
            "job_id": job.id,
            "status": "generating",
            "reply": reply,
            "active_presentation_id": c.active_presentation_id
        }, 200)

    limit = current_app.config["CHAT_HISTORY_LIMIT"]
    recent = (
        Message.query.filter(Message.conversation_id == c.id, Message.role.in_(["user", "assistant"]))
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in reversed(recent)]
    ctx = ToolContext(
        user_id=g.user.id,
        conversation_id=c.id,
        google_connected=google_auth.is_connected(g.user),
        presentation_id=c.active_presentation_id,
    )
    try:
        reply = run_agent(history, ctx, c.active_presentation_id, preferred_style=style, deep_research=deep_research, density=density)
    except gemini.GeminiNotConfigured:
        return fail("ai_not_configured", "The AI service is not configured on this server (missing GEMINI_API_KEY).", 503, {"conversation_id": c.id})
    except gemini.GeminiRateLimitError as e:
        return fail("rate_limit_exceeded", str(e), 429, {"conversation_id": c.id, "retry_after": 60})
    except gemini.GeminiError as e:
        return fail("ai_unavailable", str(e), 502, {"conversation_id": c.id})
    except Exception as e:
        current_app.logger.exception("Unexpected error in chat endpoint")
        return fail("internal_error", "An unexpected error occurred. Please try again.", 500, {"conversation_id": c.id})

    active_pid = ctx.presentation_id or c.active_presentation_id
    if active_pid:
        if c.active_presentation_id != active_pid:
            c.active_presentation_id = active_pid
        try:
            p = db.session.get(Presentation, active_pid)
            if p and p.slides:
                from datetime import datetime, timezone
                p.updated_at = datetime.now(timezone.utc)
                from services import design_auditor
                design_auditor.auto_correct_presentation_design(p)
                from services import visual_intelligence
                visual_intelligence.auto_populate_presentation_visuals(p, user_id=g.user.id, force_update=True)
                db.session.commit()
        except Exception as e:
            current_app.logger.warning("Auto visual population in chat: %s", e)

    citations = used_citations(reply, ctx.citations)
    msg = Message(
        conversation_id=c.id,
        role="assistant",
        content=reply,
        meta={"citations": citations, "tool_calls": ctx.calls, "presentation_id": active_pid},
    )
    db.session.add(msg)
    db.session.commit()
    db.session.refresh(c)
    return ok({
        "conversation_id": c.id,
        "reply": reply,
        "message_id": msg.id,
        "citations": citations,
        "tool_calls": ctx.calls,
        "active_presentation_id": active_pid,
    })
