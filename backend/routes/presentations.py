import logging
from flask import Blueprint, Response, current_app, g, request

from agents import registry
from agents.registry import ToolContext
from database import db
from models import BackgroundJob, Document, Presentation, PresentationVersion, Slide
from services import design_auditor, design_systems, exporter, gemini, google_auth, intelligence, jobs, slides
from services.google_auth import GoogleAuthExpired
from tools.draft import AUDIENCES, MAX_SLIDES, THEMES
from utils.http import fail, json_body, ok, require_auth

bp = Blueprint("presentations", __name__, url_prefix="/api")

_EXT = {"pptx": "pptx", "pdf": "pdf"}


def _own(pid):
    return Presentation.query.filter_by(id=pid, user_id=g.user.id).first()


def _scenes(p):
    """Positioned drawing primitives for the preview (same scene the PPTX/PDF writers use)."""
    try:
        from services.deck.adapter import build_scenes
        return build_scenes(p)
    except Exception:  # noqa: BLE001 - the preview must never break the page
        return [None] * len(p.slides)


@bp.get("/presentation/<pid>")
@require_auth
def get_presentation(pid):
    p = _own(pid)
    if not p:
        return fail("not_found", "Presentation not found.", 404)
    return ok({
        "id": p.id, "title": p.title, "status": p.status, "settings": p.settings,
        "google_url": p.google_url, "updated_at": p.updated_at.isoformat(),
        "slides": [{"position": s.position, "title": s.title, "content": s.content, "speaker_notes": s.speaker_notes, "scene": sc}
                   for s, sc in zip(sorted(p.slides, key=lambda s: s.position), _scenes(p))],
        "themes": {k: {"background": v[0], "title": v[1], "body": v[2], "font": v[3]} for k, v in slides.THEME_STYLES.items()},
    })


@bp.get("/presentation/<pid>/export")
@require_auth
def export_presentation(pid):
    """Export the published Google Slides file as PPTX or PDF through the Drive API."""
    p = _own(pid)
    if not p:
        return fail("not_found", "Presentation not found.", 404)
    fmt = request.args.get("format", "pptx").lower()
    if fmt not in _EXT:
        return fail("invalid_request", "format must be pptx or pdf.")
    if not p.google_presentation_id:
        return fail("not_published", "Publish this presentation to Google Slides before exporting it.", 409)
    creds = google_auth.credentials_for(g.user)
    if not creds:
        return fail("google_not_connected", "Connect your Google account to export.", 403)
    try:
        data = slides.export_file(slides.build_services(creds), p.google_presentation_id, fmt)
    except GoogleAuthExpired:
        google_auth.disconnect(g.user, revoke=False)
        return fail("google_reconnect", "Your Google access expired. Please reconnect Google.", 403)
    except slides.SlidesError as e:
        return fail("google_error", str(e), 502)
    name = "".join(ch for ch in p.title if ch.isalnum() or ch in " -_")[:60].strip() or "presentation"
    return Response(data, mimetype=slides.EXPORT_MIMES[fmt],
                    headers={"Content-Disposition": f'attachment; filename="{name}.{_EXT[fmt]}"'})


@bp.get("/design-systems")
def get_design_systems():
    """Returns the list of 10+ premium design systems for UI selection."""
    return ok(design_systems.list_design_systems())


@bp.get("/presentation/<pid>/download")
@require_auth
def download_presentation(pid):
    """Direct high-fidelity download of presentation as PPTX or PDF.
    Works for any presentation (draft or published) without requiring Google Drive."""
    p = _own(pid)
    if not p:
        return fail("not_found", "Presentation not found.", 404)
    fmt = request.args.get("format", "pptx").lower()
    if fmt not in ("pptx", "pdf"):
        return fail("invalid_request", "format must be pptx or pdf.")

    # If published and google connected, try Google export first unless native=1 is requested
    use_native = request.args.get("native") == "1" or not p.google_presentation_id
    if not use_native and p.google_presentation_id and google_auth.is_connected(g.user):
        try:
            creds = google_auth.credentials_for(g.user)
            if creds:
                data = slides.export_file(slides.build_services(creds), p.google_presentation_id, fmt)
                name = "".join(ch for ch in p.title if ch.isalnum() or ch in " -_")[:60].strip() or "presentation"
                return Response(data, mimetype=slides.EXPORT_MIMES[fmt],
                                headers={"Content-Disposition": f'attachment; filename="{name}.{_EXT[fmt]}"'})
        except Exception:
            pass  # Fallback to high-end native exporter

    # High-end native export
    if fmt == "pptx":
        data = exporter.export_pptx(p)
    else:
        data = exporter.export_pdf(p)

    name = "".join(ch for ch in p.title if ch.isalnum() or ch in " -_")[:60].strip() or "presentation"
    return Response(data, mimetype=slides.EXPORT_MIMES[fmt],
                    headers={"Content-Disposition": f'attachment; filename="{name}.{_EXT[fmt]}"'})


@bp.post("/presentation/<pid>/slide/<int:pos>/regenerate")
@require_auth
def regenerate_slide(pid, pos):
    """Regenerates a single slide's layout, design elements, and content without touching other slides."""
    p = _own(pid)
    if not p:
        return fail("not_found", "Presentation not found.", 404)
    target_slide = next((s for s in p.slides if s.position == pos), None)
    if not target_slide:
        return fail("not_found", f"Slide {pos} not found.", 404)

    data = request.get_json(silent=True) or {}
    instructions = data.get("instructions", "")
    requested_layout = data.get("layout")

    if (target_slide.content or {}).get("layout") == "composed":
        from services.deck import pipeline
        try:
            req_instructions = instructions
            if requested_layout:
                layout_map = {
                    "cards_hierarchy": "cards layout (3 or 4 cards with titles, badges, and body descriptions)",
                    "stats_kpi": "stat_row layout (prominent KPI numbers, labels, and notes)",
                    "problem_solution": "two-part comparison cards (Problem vs Solution)",
                    "process_steps": "steps layout (horizontal sequential steps)",
                    "process_diagram": "steps or diagram layout with connected nodes",
                    "quote_testimonial": "quote or callout layout with a highlighted message",
                    "timeline": "timeline layout with dates and milestone events",
                    "split_photo": "split screen with high impact photo and key insights",
                }
                layout_desc = layout_map.get(requested_layout, requested_layout)
                prefix = f"Transform this slide into a {layout_desc} layout."
                req_instructions = f"{prefix} {instructions}".strip() if instructions else prefix
            done, errs = pipeline.respec_slide(p, target_slide, req_instructions or "Make this slide clearer and more visual.")
        except gemini.GeminiError as e:
            return fail("ai_unavailable", str(e), 502)
        if not done:
            return fail("invalid_slide", "The new version of the slide did not pass the quality checks, so it was left unchanged.", 422, {"problems": errs})
        sc = _scenes(p)[pos - 1]
        return ok({"slide": {"position": pos, "title": target_slide.title, "content": target_slide.content,
                             "speaker_notes": target_slide.speaker_notes, "scene": sc}})

    topic = p.title
    total = len(p.slides)
    content = dict(target_slide.content or {})
    layout = requested_layout or content.get("layout", "cards_hierarchy")

    # If user provided instructions, refine via Gemini
    if instructions and current_app.config.get("GEMINI_API_KEY"):
        try:
            prompt = (
                f"Redesign and regenerate slide {pos} of '{topic}'.\nCurrent title: {target_slide.title}\n"
                f"Current bullets: {[b.get('text', '') for b in content.get('bullets', [])]}\n"
                f"User Instructions: {instructions[:400]}\n"
                f"Target Layout: {layout}\n"
                'Return JSON: {"title": str, "bullets": [{"text": str}], "layout": str}'
            )
            res = gemini.generate_json(prompt)
            if res.get("title"):
                target_slide.title = str(res["title"])[:255]
            if isinstance(res.get("bullets"), list):
                content["bullets"] = [{"text": str(b.get("text", ""))[:200], "source_ids": []} for b in res["bullets"] if b]
            if res.get("layout") in design_auditor.VALID_LAYOUTS:
                layout = res["layout"]
        except Exception:
            pass

    content["layout"] = layout
    target_slide.content = content

    db.session.commit()
    return ok({
        "slide": {
            "position": target_slide.position,
            "title": target_slide.title,
            "content": target_slide.content,
            "speaker_notes": target_slide.speaker_notes,
        }
    })


# ---------------------------------------------------------------------------
# Visual Asset Editor Endpoints (Find Better Visual, Replace, Remove, Diagram)
# ---------------------------------------------------------------------------

@bp.get("/presentation/<pid>/slide/<int:pos>/visual/candidates")
@require_auth
def get_visual_candidates(pid, pos):
    """Find a Better Visual: generates visual brief and returns ranked image candidates."""
    from services.deck import image_search

    p = _own(pid)
    if not p:
        return fail("not_found", "Presentation not found.", 404)
    target_slide = next((s for s in p.slides if s.position == pos), None)
    if not target_slide:
        return fail("not_found", f"Slide {pos} not found.", 404)

    brief = image_search.VisualBrief(
        slide_title=target_slide.title or f"Slide {pos}",
        main_message=target_slide.title or f"Slide {pos}",
        key_concepts=(target_slide.title or p.title).split()[:6],
        search_keywords=[target_slide.title, p.title],
    )

    candidates = image_search.retrieve_image_candidates(
        brief,
        already_used_urls=set(),
        limit_per_provider=4,
        user_id=g.user.id,
    )

    return ok({
        "slide_position": pos,
        "brief": image_search.asdict(brief),
        "candidates": [c.to_dict() for c in candidates[:10]],
    })


@bp.post("/presentation/<pid>/slide/<int:pos>/visual/select")
@require_auth
def select_slide_visual(pid, pos):
    """Select or Replace Image on slide with a chosen visual candidate."""
    p = _own(pid)
    if not p:
        return fail("not_found", "Presentation not found.", 404)
    target_slide = next((s for s in p.slides if s.position == pos), None)
    if not target_slide:
        return fail("not_found", f"Slide {pos} not found.", 404)

    data = request.get_json(silent=True) or {}
    image_data = data.get("image")
    if not image_data or not isinstance(image_data, dict) or not image_data.get("url"):
        return fail("invalid_request", "A valid image object with 'url' is required.", 400)

    content = dict(target_slide.content or {})
    content["image"] = image_data
    # If currently in text-only layout, elevate to split_screen
    if content.get("layout") not in ("split_screen", "full_bleed_hero", "image_gallery"):
        content["layout"] = "split_screen"

    target_slide.content = content
    db.session.commit()

    return ok({
        "position": target_slide.position,
        "content": target_slide.content,
    })


@bp.post("/presentation/<pid>/slide/<int:pos>/visual/remove")
@require_auth
def remove_slide_visual(pid, pos):
    """Remove visual asset from a slide."""
    p = _own(pid)
    if not p:
        return fail("not_found", "Presentation not found.", 404)
    target_slide = next((s for s in p.slides if s.position == pos), None)
    if not target_slide:
        return fail("not_found", f"Slide {pos} not found.", 404)

    content = dict(target_slide.content or {})
    if "image" in content:
        del content["image"]
    if content.get("layout") == "split_screen":
        content["layout"] = "cards_hierarchy"

    target_slide.content = content
    db.session.commit()

    return ok({
        "position": target_slide.position,
        "content": target_slide.content,
    })


@bp.post("/presentation/<pid>/slide/<int:pos>/visual/switch-diagram")
@require_auth
def switch_slide_to_diagram(pid, pos):
    """Switch to Diagram: transforms slide into an architecture or process diagram."""
    p = _own(pid)
    if not p:
        return fail("not_found", "Presentation not found.", 404)
    target_slide = next((s for s in p.slides if s.position == pos), None)
    if not target_slide:
        return fail("not_found", f"Slide {pos} not found.", 404)

    content = dict(target_slide.content or {})
    bullets = content.get("bullets", [])
    bullet_texts = [b.get("text", "") if isinstance(b, dict) else str(b) for b in bullets]

    steps = []
    for si, text in enumerate(bullet_texts[:4], start=1):
        parts = text.split(":", 1) if ":" in text else text.split(" - ", 1)
        step_name = parts[0].strip() if len(parts) > 1 else f"Stage {si}"
        step_detail = parts[1].strip() if len(parts) > 1 else parts[0].strip()
        steps.append({
            "step_number": si,
            "title": step_name[:50],
            "description": step_detail[:140],
        })

    content["layout"] = "process_diagram"
    content["process_steps"] = steps
    if "image" in content:
        del content["image"]

    target_slide.content = content
    db.session.commit()

    return ok({
        "position": target_slide.position,
        "content": target_slide.content,
    })


@bp.get("/presentation/<pid>/audit")
@require_auth
def audit_presentation(pid):
    """Runs automated design quality pre-flight audit on presentation."""
    p = _own(pid)
    if not p:
        return fail("not_found", "Presentation not found.", 404)
    report = design_auditor.audit_presentation_design(p)
    return ok(report)


@bp.post("/presentation/<pid>/audit/auto-correct")
@require_auth
def auto_correct_presentation(pid):
    """Automatically applies design corrections and layout enhancements."""
    p = _own(pid)
    if not p:
        return fail("not_found", "Presentation not found.", 404)
    result = design_auditor.auto_correct_presentation_design(p)
    return ok(result)


@bp.get("/presentations")
@require_auth
def list_presentations():
    rows = Presentation.query.filter_by(user_id=g.user.id).order_by(Presentation.updated_at.desc()).limit(100).all()
    return ok([{"id": p.id, "title": p.title, "status": p.status, "slide_count": len(p.slides), "google_url": p.google_url,
                "theme": (p.settings or {}).get("theme"), "updated_at": p.updated_at.isoformat()} for p in rows])


def _validate_params():
    data, err = json_body({"topic": str})
    if err:
        return None, None, err
    topic = data["topic"].strip()
    if not 3 <= len(topic) <= 500:
        return None, None, fail("invalid_request", "Topic must be 3-500 characters.")

    def pick(key, allowed, default):
        v = data.get(key, default)
        if isinstance(v, str):
            v_norm = v.strip().lower().replace(" ", "_").replace("-", "_")
            if v_norm in allowed:
                return v_norm
            try:
                from services.design_systems import LEGACY_THEME_MAP
                if v_norm in LEGACY_THEME_MAP and LEGACY_THEME_MAP[v_norm] in allowed:
                    return LEGACY_THEME_MAP[v_norm]
            except Exception:
                pass
        return v if v in allowed else None

    def num(key, lo, hi, default):
        v = data.get(key, default)
        return v if (v is None and default is None) or (isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi) else "bad"

    slide_count, duration = num("slide_count", 3, MAX_SLIDES, 10), num("duration_minutes", 1, 180, None)
    p = {"topic": topic, "slide_count": slide_count, "duration_minutes": duration,
         "audience": pick("audience", AUDIENCES, "college_students"), "theme": pick("theme", THEMES, "modern_light"),
         "citation_style": pick("citation_style", ("APA", "MLA", "IEEE", "none"), "APA"),
         "complexity": pick("complexity", ("basic", "intermediate", "advanced"), "intermediate"),
         "language": str(data.get("language") or "English").strip()[:40],
         "use_web_research": data.get("use_web_research", False), "publish": data.get("publish", False)}
    for k, v in p.items():
        if v is None and k != "duration_minutes" or v == "bad":
            return None, None, fail("invalid_request", f"Invalid value for '{k}'.")
    if not isinstance(p["use_web_research"], bool) or not isinstance(p["publish"], bool):
        return None, None, fail("invalid_request", "use_web_research and publish must be true or false.")

    ids = data.get("document_ids", [])
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids) or len(ids) > 10:
        return None, None, fail("invalid_request", "document_ids must be a list of up to 10 ids.")
    docs = Document.query.filter(Document.user_id == g.user.id, Document.status == "indexed", Document.id.in_(ids)).all() if ids else []
    if len(docs) != len(set(ids)):
        return None, None, fail("not_found", "One or more documents were not found.", 404)
    p["document_ids"] = [d.id for d in docs]
    return p, [d.filename for d in docs], None


@bp.post("/presentation/create")
@require_auth
def create_presentation():
    """Starts generation as a background job and returns immediately; poll /presentation/status."""
    if getattr(g.user, "is_guest", False):
        limit = current_app.config.get("GUEST_MAX_PRESENTATIONS", 3)
        count = Presentation.query.filter_by(user_id=g.user.id).count()
        if count >= limit:
            return fail("guest_limit_reached",
                        f"Guest accounts are limited to {limit} presentations. Sign in with Google to create unlimited presentations.",
                        403, {"limit": limit, "count": count})
    params, doc_names, err = _validate_params()
    if err:
        return err
    if not current_app.config.get("GEMINI_API_KEY"):
        return fail("ai_not_configured", "The AI service is not configured on this server (missing GEMINI_API_KEY).", 503)
    if params["publish"] and not google_auth.is_connected(g.user):
        return fail("google_not_connected", "Connect your Google account first, or turn off publishing and keep a draft.", 403)
    running = jobs.active_job_for(g.user.id)
    if running:
        return fail("job_in_progress", "A presentation is already being generated. Wait for it to finish.", 409,
                    {"job_id": running.id})
    try:
        job = jobs.start_generation(current_app._get_current_object(), g.user.id, params, doc_names)
    except jobs.JobCapacityExceeded as e:
        return fail("engine_busy", str(e), 503)
    return ok(jobs.job_dict(job), 202)


@bp.get("/presentation/status")
@bp.get("/presentation/status/<job_id>")
@require_auth
def presentation_status(job_id=None):
    if not job_id:
        job_id = request.args.get("job_id", "")
    job = BackgroundJob.query.filter_by(id=job_id, user_id=g.user.id).first() if job_id else None
    if not job:
        return fail("not_found", "Job not found.", 404)
    return ok(jobs.job_dict(jobs.reap_if_stale(job)))


@bp.get("/presentation/status/stream")
def presentation_status_stream():
    """Server-Sent Events (SSE) stream for real-time presentation generation progress.
    Eliminates repetitive HTTP polling and provides instantaneous stage updates.
    """
    import json
    import time
    from flask import Response
    from utils.http import _serializer, TOKEN_MAX_AGE

    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else request.args.get("token", "")
    if not token:
        return fail("unauthorized", "Missing credentials.", 401)
    try:
        payload = _serializer().loads(token, max_age=TOKEN_MAX_AGE)
        user_id = payload.get("uid")
    except Exception:
        return fail("unauthorized", "Invalid or expired session.", 401)

    job_id = request.args.get("job_id", "")
    if not job_id:
        return fail("invalid_request", "job_id is required.", 400)

    job = BackgroundJob.query.filter_by(id=job_id, user_id=user_id).first()
    if not job:
        return fail("not_found", "Job not found.", 404)

    def event_stream():
        last_progress = -1
        last_status = None
        max_loops = 300  # 150 seconds timeout guard
        loops = 0
        while loops < max_loops:
            loops += 1
            db.session.expire_all()
            current_job = db.session.get(BackgroundJob, job_id)
            if not current_job:
                break

            j_dict = jobs.job_dict(jobs.reap_if_stale(current_job))
            if j_dict["progress"] != last_progress or j_dict["status"] != last_status:
                last_progress = j_dict["progress"]
                last_status = j_dict["status"]
                yield f"data: {json.dumps(j_dict)}\n\n"

            if j_dict["status"] in ("done", "failed"):
                break

            time.sleep(0.5)

    resp = Response(event_stream(), mimetype="text/event-stream")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"
    resp.headers["Connection"] = "keep-alive"
    return resp


@bp.post("/presentation/<pid>/publish")
@require_auth
def publish_presentation(pid):
    if not _own(pid):
        return fail("not_found", "Presentation not found.", 404)
    if not google_auth.is_connected(g.user):
        return fail("google_not_connected", "Connect your Google account to publish.", 403)
    res = registry.execute("create_google_slides", {"presentation_id": pid}, ToolContext(user_id=g.user.id, google_connected=True))
    if not res.get("ok"):
        return fail("publish_failed", res.get("error", "Publishing failed."), 502)
    return ok(res)


@bp.post("/presentation/<pid>/theme")
@require_auth
def set_theme(pid):
    data, err = json_body({"theme": str})
    if err:
        return err
    if not _own(pid):
        return fail("not_found", "Presentation not found.", 404)
    res = registry.execute("apply_design_theme", {"presentation_id": pid, "theme": data["theme"]}, ToolContext(user_id=g.user.id))
    if not res.get("ok"):
        return fail("invalid_request", res.get("error", "Could not apply theme."))
    return ok(res)


@bp.get("/presentation/<pid>/intelligence")
@require_auth
def get_intelligence(pid):
    p = _own(pid)
    if not p:
        return fail("not_found", "Presentation not found.", 404)
    target_dur = request.args.get("target_duration", type=int)
    aud = request.args.get("audience", type=str)
    report = intelligence.analyze_presentation(p, target_duration=target_dur, audience=aud)
    return ok(report)


@bp.post("/presentation/<pid>/intelligence/fix")
@require_auth
def fix_intelligence(pid):
    p = _own(pid)
    if not p:
        return fail("not_found", "Presentation not found.", 404)
    data, err = json_body({"action_type": str})
    if err:
        return err
    act = data["action_type"]
    allowed_actions = ("generate_missing_notes", "trim_overflow", "auto_balance")
    if act not in allowed_actions:
        return fail("invalid_request", f"action_type must be one of {list(allowed_actions)}.")
    slide_pos = data.get("slide_position")
    if slide_pos is not None and (not isinstance(slide_pos, int) or slide_pos < 1):
        return fail("invalid_request", "slide_position must be a positive integer.")
    res = intelligence.auto_fix_presentation(p, act, slide_position=slide_pos)
    report = intelligence.analyze_presentation(p)
    return ok({"fix_result": res, "intelligence": report})


def _sync_google_if_needed(p: Presentation, user):
    """If presentation is published and Google account is connected, sync the latest draft."""
    if not p.google_presentation_id or not google_auth.is_connected(user):
        return {"synced": False, "reason": "not_published_or_not_connected"}
    creds = google_auth.credentials_for(user)
    if not creds:
        return {"synced": False, "reason": "credentials_unavailable"}
    try:
        from tools.google_slides import to_draft
        res = slides.sync_presentation(slides.build_services(creds), p.google_presentation_id, to_draft(p))
        for s, oid in zip(sorted(p.slides, key=lambda s: s.position), res.get("slide_object_ids", [])):
            s.google_object_id = oid
        db.session.commit()
        return {"synced": True, "url": res["url"], "not_rendered": res.get("not_rendered", [])}
    except Exception as e:
        logging.getLogger(__name__).warning("Google sync failed for presentation %s: %s", p.id, e)
        return {"synced": False, "error": str(e)}


@bp.post("/presentation/edit")
@require_auth
def edit_presentation():
    data, err = json_body({"presentation_id": str})
    if err:
        return err
    pid = data["presentation_id"]
    p = _own(pid)
    if not p:
        return fail("not_found", "Presentation not found.", 404)

    action = data.get("action", "edit_slide")
    should_sync = data.get("sync", True)
    modified = False

    if action == "edit_slide":
        pos = data.get("slide_position")
        if not pos or not isinstance(pos, int) or not 1 <= pos <= len(p.slides):
            return fail("invalid_request", f"slide_position must be between 1 and {len(p.slides)}.")
        s = sorted(p.slides, key=lambda x: x.position)[pos - 1]
        content = dict(s.content or {})
        spec = dict(content.get("spec") or {})

        if "title" in data and isinstance(data["title"], str):
            s.title = data["title"].strip()[:512]
            if spec:
                spec["title"] = s.title
            modified = True

        if "speaker_notes" in data and isinstance(data["speaker_notes"], str):
            s.speaker_notes = data["speaker_notes"].strip()
            if spec:
                spec["notes"] = s.speaker_notes
            modified = True

        if "tagline" in data and isinstance(data["tagline"], str):
            content["tagline"] = data["tagline"].strip()[:255]
            if spec:
                spec["tagline"] = content["tagline"]
            modified = True

        if "layout" in data and data["layout"] in ("title_bullets", "title_only", "two_column", "comparison_table", "chart", "diagram", "section_header", "composed"):
            content["layout"] = data["layout"]
            modified = True

        if "blocks" in data and isinstance(data["blocks"], list):
            from services.deck.blocks import normalize_blocks
            spec["blocks"] = normalize_blocks(data["blocks"])
            content["spec"] = spec
            content["layout"] = "composed"
            modified = True
        elif "bullets" in data and isinstance(data["bullets"], list):
            bullets_list = [str(t).strip()[:300] for t in data["bullets"][:10]]
            old_sources = {b.get("text", ""): b.get("source_ids", []) for b in content.get("bullets", []) if isinstance(b, dict)}
            content["bullets"] = [{"text": t, "source_ids": old_sources.get(t, [])} for t in bullets_list]
            if spec:
                blocks = list(spec.get("blocks") or [])
                updated_bullet_block = False
                for b in blocks:
                    if isinstance(b, dict) and b.get("type") == "bullets":
                        b["items"] = bullets_list
                        updated_bullet_block = True
                        break
                if not updated_bullet_block:
                    blocks.append({"type": "bullets", "items": bullets_list})
                spec["blocks"] = blocks
                content["spec"] = spec
            modified = True

        if spec:
            content["spec"] = spec
        s.content = content

    elif action == "add_slide":
        if len(p.slides) >= 40:
            return fail("invalid_request", "Presentation cannot exceed 40 slides.")
        pos = data.get("slide_position", len(p.slides) + 1)
        pos = min(max(int(pos), 1), len(p.slides) + 1)
        for s in p.slides:
            if s.position >= pos:
                s.position += 1
        title = str(data.get("title", f"New Slide {pos}")).strip()[:512]
        bullets = [{"text": str(b).strip()[:300], "source_ids": []} for b in data.get("bullets", [])[:6]]
        notes = str(data.get("speaker_notes", "")).strip()
        bullet_texts = [b["text"] for b in bullets] if bullets else ["Key takeaway 1", "Key takeaway 2", "Key takeaway 3"]
        new_content = {
            "layout": "composed",
            "spec": {
                "kind": "content",
                "title": title,
                "notes": notes,
                "blocks": [{"type": "bullets", "items": bullet_texts}],
            },
            "bullets": bullets or [{"text": t, "source_ids": []} for t in bullet_texts],
        }
        new_s = Slide(presentation_id=p.id, position=pos, title=title,
                      content=new_content, speaker_notes=notes)
        db.session.add(new_s)
        db.session.flush()
        db.session.refresh(p)
        for i, s in enumerate(sorted(p.slides, key=lambda x: x.position), start=1):
            s.position = i
        db.session.flush()
        modified = True

    elif action == "duplicate_slide":
        if len(p.slides) >= 40:
            return fail("invalid_request", "Presentation cannot exceed 40 slides.")
        pos = data.get("slide_position")
        slides = sorted(p.slides, key=lambda x: x.position)
        if not isinstance(pos, int) or not (1 <= pos <= len(slides)):
            return fail("invalid_request", f"slide_position must be between 1 and {len(slides)}.")
        orig = slides[pos - 1]
        for s in slides[pos:]:
            s.position += 1
        new_s = Slide(
            presentation_id=p.id,
            position=pos + 1,
            title=f"{orig.title} (Copy)"[:512],
            content=dict(orig.content or {}),
            speaker_notes=orig.speaker_notes,
        )
        db.session.add(new_s)
        db.session.flush()
        db.session.refresh(p)
        for i, s in enumerate(sorted(p.slides, key=lambda x: x.position), start=1):
            s.position = i
        db.session.flush()
        modified = True

    elif action == "reorder_slide":
        from_pos = data.get("from_position")
        to_pos = data.get("to_position")
        slides = sorted(p.slides, key=lambda x: x.position)
        if not isinstance(from_pos, int) or not isinstance(to_pos, int) or not (1 <= from_pos <= len(slides) and 1 <= to_pos <= len(slides)):
            return fail("invalid_request", f"from_position and to_position must be between 1 and {len(slides)}.")
        if from_pos != to_pos:
            target = slides.pop(from_pos - 1)
            slides.insert(to_pos - 1, target)
            for i, s in enumerate(slides, start=1):
                s.position = i
            db.session.flush()
            modified = True

    elif action == "delete_slide":
        if len(p.slides) <= 1:
            return fail("invalid_request", "Cannot delete the last slide.")
        pos = data.get("slide_position")
        if not pos or not isinstance(pos, int) or not 1 <= pos <= len(p.slides):
            return fail("invalid_request", f"slide_position must be between 1 and {len(p.slides)}.")
        target = sorted(p.slides, key=lambda x: x.position)[pos - 1]
        db.session.delete(target)
        db.session.flush()
        db.session.refresh(p)
        for i, s in enumerate(sorted(p.slides, key=lambda x: x.position), start=1):
            s.position = i
        db.session.flush()
        modified = True

    elif action == "update_title":
        new_title = str(data.get("title", "")).strip()
        if not (1 <= len(new_title) <= 255):
            return fail("invalid_request", "Title must be 1-255 characters.")
        p.title = new_title
        modified = True

    else:
        return fail("invalid_request", f"Unknown action '{action}'.")

    if modified:
        n = len(p.versions) + 1
        db.session.add(PresentationVersion(
            presentation_id=p.id, version_number=n, reason=f"edit: {action}",
            snapshot={"title": p.title, "slides": len(p.slides)}))
        db.session.commit()

    sync_result = _sync_google_if_needed(p, g.user) if should_sync else {"synced": False}

    return ok({
        "presentation_id": p.id,
        "title": p.title,
        "slide_count": len(p.slides),
        "slides": [{"position": s.position, "title": s.title, "content": s.content, "speaker_notes": s.speaker_notes, "scene": sc}
                   for s, sc in zip(sorted(p.slides, key=lambda s: s.position), _scenes(p))],
        "google_url": p.google_url,
        "google_sync": sync_result,
    })


@bp.post("/presentation/<pid>/sync")
@require_auth
def sync_presentation(pid):
    p = _own(pid)
    if not p:
        return fail("not_found", "Presentation not found.", 404)
    if not p.google_presentation_id:
        return fail("not_published", "Presentation is not published to Google Slides yet.", 409)
    if not google_auth.is_connected(g.user):
        return fail("google_not_connected", "Google account is not connected.", 403)
    sync_result = _sync_google_if_needed(p, g.user)
    if not sync_result.get("synced"):
        return fail("sync_failed", sync_result.get("error", "Google sync failed."), 502)
    return ok({"presentation_id": p.id, "google_url": p.google_url, "sync": sync_result})


