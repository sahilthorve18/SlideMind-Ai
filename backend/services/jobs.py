"""Background generation jobs with persistent status.

A job row (BackgroundJob) is the source of truth: the HTTP request returns immediately with a
job id and clients poll it. Work runs in a daemon thread (or inline in tests). Because free-tier
hosts can restart or sleep mid-job, a job that stops reporting is declared failed on read
instead of staying "running" forever.
"""
import logging
import threading
from datetime import datetime, timezone

from agents import registry
from agents.agent import run_agent
from agents.registry import ToolContext
from database import db
from models import BackgroundJob, Conversation, Message, Presentation, User
from services import design_auditor, gemini, google_auth

log = logging.getLogger(__name__)

KIND = "generate_presentation"
KIND_EDIT = "edit_presentation"
KINDS = (KIND, KIND_EDIT)
ACTIVE = ("queued", "running")
STALE_SECONDS = 600
JOB_MAX_STEPS = 25
MAX_CONCURRENT_JOBS = 2


class JobCapacityExceeded(Exception):
    """Raised when active background generation jobs reach the host's concurrency capacity."""
    pass

# Rough progress by the stage a tool belongs to; progress never goes backwards.
STAGES = {
    "search_knowledge_base": (15, "Searching your documents"), "extract_document": (15, "Reading your document"),
    "web_research": (22, "Researching the web"), "fact_sheet": (35, "Building the fact sheet"),
    "storyline": (45, "Planning the storyline"), "slide_specs": (65, "Designing each slide"), "visuals": (80, "Choosing relevant visuals"), "generate_slide_outline": (35, "Writing the outline"),
    "generate_slide_content": (60, "Writing slide content"), "add_speaker_notes": (70, "Adding speaker notes"),
    "update_slide_notes": (70, "Updating speaker notes"), "get_presentation": (30, "Inspecting presentation structure"),
    "generate_diagram": (72, "Drawing a diagram"), "generate_chart": (72, "Adding a chart"),
    "apply_design_theme": (75, "Applying the theme"), "edit_existing_slide": (80, "Improving a slide"),
    "auto_populate_visuals": (82, "Selecting and placing visuals"),
    "add_slide": (80, "Adding a slide"), "delete_slide": (80, "Removing a slide"),
    "reorder_slides": (80, "Reorganizing slides"),
    "verify_presentation": (85, "Checking quality"), "generate_references": (88, "Building references"),
    "calculate_presentation_duration": (90, "Estimating duration"), "create_google_slides": (96, "Publishing to Google Slides"),
}


def _now():
    return datetime.now(timezone.utc)


def build_task_prompt(p: dict, doc_names: list[str]) -> str:
    lines = [
        "Create a complete presentation autonomously with these settings. Do not ask the user questions; use sensible choices.",
        f"- Topic: {p['topic']}",
        f"- Slides: exactly {p['slide_count']}",
        f"- Audience: {p['audience']}",
        f"- Language: {p['language']}",
        f"- Complexity: {p['complexity']}",
        f"- Citation style: {p['citation_style']}",
        f"- Theme: apply '{p['theme']}' with apply_design_theme",
    ]
    if p.get("duration_minutes"):
        lines.append(f"- Target duration: {p['duration_minutes']} minutes (check with calculate_presentation_duration)")
    if p["document_ids"]:
        lines.append("- Base the content on these uploaded documents (search/extract them first): "
                     + ", ".join(f"{n} (id {i})" for i, n in zip(p["document_ids"], doc_names)))
    else:
        lines.append("- No documents were selected; do not search the user's documents unless the topic clearly needs them.")
    lines.append("- Web research: " + ("allowed and encouraged for recent facts" if p["use_web_research"] else "NOT allowed; do not call web_research"))
    lines.append("- Publish to Google Slides at the end: " + ("yes, call create_google_slides" if p["publish"] else "no, keep it as a draft"))
    lines.append(
        "Process: gather material, outline, write content with sources, add speaker notes, add a diagram or chart ONLY where real "
        "data or a real mechanism supports it, run verify_presentation and fix blocking problems with targeted edits (do not regenerate "
        "everything), generate references, then finish with a 3-4 line summary that states what is unsupported or missing.")
    return "\n".join(lines)


def reap_if_stale(job: BackgroundJob) -> BackgroundJob:
    if job.status in ACTIVE:
        updated = job.updated_at if job.updated_at.tzinfo else job.updated_at.replace(tzinfo=timezone.utc)
        if (_now() - updated).total_seconds() > STALE_SECONDS:
            job.status, job.error = "failed", "Generation was interrupted (the server restarted or timed out). Please start it again."
            db.session.commit()
    return job


def active_job_for(user_id: str, conversation_id: str | None = None) -> BackgroundJob | None:
    jobs_query = BackgroundJob.query.filter(
        BackgroundJob.user_id == user_id,
        BackgroundJob.kind.in_(KINDS),
        BackgroundJob.status.in_(ACTIVE)
    ).order_by(BackgroundJob.created_at.desc()).all()
    for j in jobs_query:
        if reap_if_stale(j).status in ACTIVE:
            if conversation_id:
                if (j.payload or {}).get("conversation_id") == conversation_id:
                    return j
            else:
                return j
    return None


def start_generation(app, user_id: str, params: dict, doc_names: list[str], conversation_id: str | None = None) -> BackgroundJob:
    if not app.config.get("JOBS_INLINE", False) and not app.config.get("TESTING", False):
        running = BackgroundJob.query.filter(BackgroundJob.status.in_(ACTIVE)).count()
        if running >= MAX_CONCURRENT_JOBS:
            raise JobCapacityExceeded("SlideMind is currently processing presentations at full capacity. Please try again in a moment.")
    payload = {"params": params, "doc_names": doc_names, "log": []}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    job = BackgroundJob(user_id=user_id, kind=KIND, status="queued", progress=0, payload=payload)
    db.session.add(job)
    db.session.commit()
    if app.config.get("JOBS_INLINE"):
        _run(app, job.id)
    else:
        threading.Thread(target=_run, args=(app, job.id), daemon=True, name=f"gen-{job.id[:8]}").start()
    return job


def start_edit(
    app,
    user_id: str,
    conversation_id: str,
    presentation_id: str | None,
    message: str,
    style: str | None = None,
    deep_research: bool = False,
    density: str = "detailed",
    run_agent_fn = None,
) -> BackgroundJob:
    payload = {
        "conversation_id": conversation_id,
        "presentation_id": presentation_id,
        "message": message,
        "style": style,
        "deep_research": deep_research,
        "density": density,
        "log": [
            {
                "t": _now().isoformat(timespec="seconds"),
                "tool": "analyzing",
                "label": "Analyzing presentation changes",
                "status": "success",
            }
        ],
    }
    job = BackgroundJob(user_id=user_id, kind=KIND_EDIT, status="queued", progress=15, payload=payload)
    db.session.add(job)
    db.session.commit()
    if app.config.get("JOBS_INLINE"):
        _run_edit(app, job.id, run_agent_fn=run_agent_fn)
    else:
        threading.Thread(
            target=_run_edit,
            args=(app, job.id, run_agent_fn),
            daemon=True,
            name=f"edit-{job.id[:8]}",
        ).start()
    return job


def _fail(job: BackgroundJob, message: str):
    db.session.rollback()
    job = db.session.get(BackgroundJob, job.id)
    if not job:
        return
    job.status, job.error = "failed", message
    conv_id = (job.payload or {}).get("conversation_id")
    if conv_id:
        try:
            c = db.session.get(Conversation, conv_id)
            if c:
                prefix = "Could not apply changes" if job.kind == KIND_EDIT else "Presentation generation failed"
                msg = Message(
                    conversation_id=c.id,
                    role="assistant",
                    content=f"{prefix}: {message}",
                    meta={"error": message, "job_id": job.id}
                )
                db.session.add(msg)
        except Exception as e:
            log.warning("Could not append failure message to conversation %s: %s", conv_id, e)
    db.session.commit()


def _record(job_id: str, tool: str, status: str):
    job = db.session.get(BackgroundJob, job_id)
    if not job:
        return
    stage, label = STAGES.get(tool, (job.progress, tool.replace("_", " ")))
    payload = dict(job.payload or {})
    payload["log"] = [*payload.get("log", []), {"t": _now().isoformat(timespec="seconds"), "tool": tool,
                                                  "label": label, "status": status}]
    job.payload = payload
    if status == "success":
        job.progress = min(max(job.progress, stage), 99)
    db.session.commit()  # also bumps updated_at: the heartbeat the stale check relies on


def _checkpoint(job_id: str, key: str, value):
    """Saves intermediate pipeline artifacts (facts, storyline, specs) for checkpointing and recovery."""
    try:
        job = db.session.get(BackgroundJob, job_id)
        if job:
            payload = dict(job.payload or {})
            payload[f"checkpoint_{key}"] = value
            job.payload = payload
            db.session.commit()
    except Exception as e:
        log.debug("Checkpoint failed for job %s: %s", job_id, e)


def _run(app, job_id: str):
    with app.app_context():
        job = db.session.get(BackgroundJob, job_id)
        try:
            job.status, job.progress = "running", 5
            db.session.commit()
            params, doc_names = job.payload["params"], job.payload.get("doc_names", [])
            user = db.session.get(User, job.user_id)
            ctx = ToolContext(user_id=job.user_id, google_connected=google_auth.is_connected(user))
            ctx.on_call = lambda name, status: _record(job_id, name, status)
            ctx.checkpoint = lambda key, val: _checkpoint(job_id, key, val)
            ctx.overrides = {k: params.get(k) for k in ("slide_count", "audience", "language", "duration_minutes", "citation_style",
                                                         "complexity", "theme", "use_web_research", "publish", "document_ids")}

            from services.deck import pipeline
            progress = lambda name, status: _record(job_id, name, status)  # noqa: E731
            p, deck_warnings = pipeline.generate_deck(ctx, params, progress)
            pid = p.id
            reply = "Created '%s' with %d slides." % (p.title, len(p.slides))
            if deck_warnings:
                reply += " Notes: " + " ".join(deck_warnings[:4])
            ctx.on_call = None  # the pipeline's own final check is not a user-visible step
            if params.get("publish"):
                registry.execute("create_google_slides", {"presentation_id": pid}, ctx)
            check = registry.execute("verify_presentation", {"presentation_id": pid}, ctx)
            job = db.session.get(BackgroundJob, job_id)
            job.result = {"presentation_id": pid, "title": p.title, "slide_count": len(p.slides), "summary": reply,
                          "google_url": p.google_url, "published": bool(p.google_presentation_id),
                          "issues": check.get("issues", []), "blocking_issues": check.get("blocking_issues", 0),
                          "overall_score": check.get("overall_score"), "grade": check.get("grade"),
                          "citations": ctx.citations[:30], "tool_calls": ctx.calls, "warnings": deck_warnings}
            job.status, job.progress = "done", 100

            # Synchronize to chat conversation if initiated from chat
            conv_id = (job.payload or {}).get("conversation_id")
            if conv_id:
                try:
                    c = db.session.get(Conversation, conv_id)
                    if c:
                        c.active_presentation_id = pid
                        msg = Message(
                            conversation_id=c.id,
                            role="assistant",
                            content=reply,
                            meta={
                                "presentation_id": pid,
                                "citations": ctx.citations[:30],
                                "tool_calls": ctx.calls,
                                "job_id": job_id,
                            }
                        )
                        db.session.add(msg)
                except Exception as e:
                    log.warning("Could not sync job result to conversation %s: %s", conv_id, e)

            db.session.commit()
        except gemini.GeminiNotConfigured:
            _fail(job, "The AI service is not configured on this server (missing GEMINI_API_KEY).")
        except gemini.GeminiError as e:
            _fail(job, str(e))
        except Exception:
            log.exception("Generation job %s crashed", job_id)
            _fail(job, "Generation failed unexpectedly. Please try again.")


def _run_edit(app, job_id: str, run_agent_fn=None):
    with app.app_context():
        job = db.session.get(BackgroundJob, job_id)
        if not job:
            return
        try:
            job.status, job.progress = "running", 20
            db.session.commit()
            payload = dict(job.payload or {})
            conv_id = payload.get("conversation_id")
            pres_id = payload.get("presentation_id")
            style = payload.get("style")
            deep_research = bool(payload.get("deep_research", False))
            density = payload.get("density", "detailed")
            user = db.session.get(User, job.user_id)
            c = db.session.get(Conversation, conv_id) if conv_id else None

            limit = app.config.get("CHAT_HISTORY_LIMIT", 20)
            recent = (
                Message.query.filter(Message.conversation_id == conv_id, Message.role.in_(["user", "assistant"]))
                .order_by(Message.created_at.desc())
                .limit(limit)
                .all()
            )
            history = [{"role": m.role, "content": m.content} for m in reversed(recent)]

            ctx = ToolContext(
                user_id=job.user_id,
                conversation_id=conv_id,
                google_connected=google_auth.is_connected(user),
                presentation_id=pres_id,
            )
            ctx.on_call = lambda name, status: _record(job_id, name, status)

            runner = run_agent_fn or run_agent
            reply = runner(
                history,
                ctx,
                pres_id,
                preferred_style=style,
                deep_research=deep_research,
                density=density,
            )

            active_pid = ctx.presentation_id or (c.active_presentation_id if c else None) or pres_id
            if active_pid and c and c.active_presentation_id != active_pid:
                c.active_presentation_id = active_pid

            if active_pid:
                try:
                    p = db.session.get(Presentation, active_pid)
                    if p and p.slides:
                        from datetime import datetime, timezone
                        p.updated_at = datetime.now(timezone.utc)
                        from services import design_auditor
                        design_auditor.auto_correct_presentation_design(p)
                        db.session.commit()
                except Exception as e:
                    log.warning("Design auto-correction in chat edit job: %s", e)

            from agents.agent import used_citations
            citations = used_citations(reply, ctx.citations)
            msg = Message(
                conversation_id=conv_id,
                role="assistant",
                content=reply,
                meta={
                    "citations": citations,
                    "tool_calls": ctx.calls,
                    "presentation_id": active_pid,
                    "job_id": job_id,
                },
            )
            db.session.add(msg)

            job = db.session.get(BackgroundJob, job_id)
            job.result = {
                "presentation_id": active_pid,
                "summary": reply,
                "citations": citations,
                "tool_calls": ctx.calls,
                "message_id": msg.id,
            }
            job.status, job.progress = "done", 100
            db.session.commit()
        except gemini.GeminiNotConfigured:
            _fail(job, "The AI service is not configured on this server (missing GEMINI_API_KEY).")
        except gemini.GeminiRateLimitError as e:
            _fail(job, f"AI rate limit reached: {str(e)}")
        except gemini.GeminiError as e:
            _fail(job, f"AI service error: {str(e)}")
        except Exception as e:
            log.exception("Chat edit job %s crashed: %s", job_id, e)
            _fail(job, "Failed to apply changes. Please try again.")


def job_dict(job: BackgroundJob) -> dict:
    return {"job_id": job.id, "kind": job.kind, "status": job.status, "progress": job.progress, "error": job.error,
            "log": (job.payload or {}).get("log", []), "result": job.result,
            "created_at": job.created_at.isoformat(), "updated_at": job.updated_at.isoformat()}
