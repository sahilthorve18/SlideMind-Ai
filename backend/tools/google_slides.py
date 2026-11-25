"""Tool 6: create_google_slides. Publishes a saved draft to the user's own Google Drive."""
from agents.registry import ToolError, tool
from database import db
from models import PresentationVersion, User
from services import google_auth, slides
from services.google_auth import GoogleAuthExpired
from tools.draft import get_presentation


def to_draft(p) -> dict:
    from services.deck.adapter import build_scenes

    out = []
    for s in sorted(p.slides, key=lambda s: s.position):
        c = s.content or {}
        srcs = {}
        for b in c.get("bullets", []):
            for sid in b.get("source_ids", []):
                meta = (c.get("sources") or {}).get(sid) or {}
                key = meta.get("url") or meta.get("filename") or sid
                srcs.setdefault(key, meta)
        out.append({"title": s.title, "bullets": [b["text"] for b in c.get("bullets", [])], "layout": c.get("layout"),
                    "notes": s.speaker_notes, "sources": list(srcs.values())})
    return {
        "title": p.title,
        "theme": (p.settings or {}).get("theme", "modern_light"),
        "slides": out,
        "scenes": build_scenes(p),
    }


@tool("create_google_slides",
      "Publish the draft presentation to the user's Google Drive as a richly formatted Google Slides file (matching the preview's "
      "cards, diagrams, charts, typography, and visuals) and return its real link. Requires a connected Google account.",
      {"presentation_id": {"type": "string"}}, ["presentation_id"], requires_google=True)
def create_google_slides(ctx, a):
    p = get_presentation(ctx, a["presentation_id"])
    if ctx.overrides.get("publish") is False:
        raise ToolError("Publishing to Google Slides was not requested for this task; leave it as a draft.")
    if p.google_presentation_id:
        return {"already_published": True, "url": p.google_url,
                "warning": "This draft was already published. Changes made to the draft after publishing are not synced to Google yet."}
    if not p.slides:
        raise ToolError("The draft has no slides.")
    user = db.session.get(User, ctx.user_id)
    creds = google_auth.credentials_for(user)
    if not creds:
        raise ToolError("Google access is not available; ask the user to reconnect their Google account.")
    try:
        res = slides.publish_draft(slides.build_services(creds), to_draft(p))
    except GoogleAuthExpired:
        google_auth.disconnect(user, revoke=False)
        raise ToolError("Google access was revoked or expired. Ask the user to reconnect their Google account.")
    except slides.SlidesError as e:
        raise ToolError(str(e))

    p.google_presentation_id, p.google_url, p.status = res["presentation_id"], res["url"], "published"
    for s, oid in zip(sorted(p.slides, key=lambda s: s.position), res["slide_object_ids"]):
        s.google_object_id = oid
    n = len(p.versions) + 1
    db.session.add(PresentationVersion(presentation_id=p.id, version_number=n, reason="published to Google Slides",
                                       snapshot={"google_presentation_id": res["presentation_id"], "slides": len(p.slides)}))
    db.session.commit()
    out = {"url": res["url"], "slides": len(p.slides), "notes_written": res["notes_written"]}
    if res["not_rendered"]:
        out["not_rendered"] = res["not_rendered"]
        out["warning"] = "Some elements were not rendered in Google Slides; tell the user exactly which."
    return out
