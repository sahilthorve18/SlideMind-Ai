"""Rehearsal endpoints for SlideMind AI."""
from flask import Blueprint, g

from models import Presentation
from services import rehearsal
from utils.http import fail, json_body, ok, require_auth

bp = Blueprint("rehearsal", __name__, url_prefix="/api")


def _own(pid):
    return Presentation.query.filter_by(id=pid, user_id=g.user.id).first()


@bp.post("/rehearsal")
@require_auth
def practice_slide():
    data, err = json_body({"presentation_id": str, "slide_position": int, "transcript": str, "duration_seconds": int})
    if err:
        return err
    p = _own(data["presentation_id"])
    if not p:
        return fail("not_found", "Presentation not found.", 404)
    pos = data["slide_position"]
    if not 1 <= pos <= len(p.slides):
        return fail("invalid_request", f"slide_position must be between 1 and {len(p.slides)}.")
    s = sorted(p.slides, key=lambda x: x.position)[pos - 1]
    bullets = [b.get("text", "") for b in ((s.content or {}).get("bullets", []))]
    res = rehearsal.analyze_slide_rehearsal(
        slide_title=s.title,
        bullets=bullets,
        speaker_notes=s.speaker_notes or "",
        transcript=data["transcript"],
        duration_seconds=data["duration_seconds"],
    )
    return ok(res)


@bp.post("/rehearsal/deck")
@require_auth
def practice_deck():
    data, err = json_body({"presentation_id": str, "runs": list})
    if err:
        return err
    p = _own(data["presentation_id"])
    if not p:
        return fail("not_found", "Presentation not found.", 404)
    res = rehearsal.analyze_deck_rehearsal(p, data["runs"])
    return ok(res)
