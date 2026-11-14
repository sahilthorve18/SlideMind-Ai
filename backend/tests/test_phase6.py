import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

os.environ["SLIDEMIND_SKIP_AUTOAPP"] = "1"

import pytest

from agents.registry import ToolContext
from app import create_app
from database import db
from models import BackgroundJob, Document, Presentation, ToolExecutionLog, User
from routes import conversations as conv_routes
from services import gemini, google_auth, jobs, slides
from sqlalchemy.pool import StaticPool
from services.google_auth import SCOPES
from tests.test_phase5 import FakeDrive, FakeSlidesAPI
from tests.test_phase5 import KEY


def make_app(**extra):
    cfg = {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "DEV_LOGIN_ENABLED": True,
           "RATELIMIT_ENABLED": False, "GEMINI_API_KEY": "k", "JOBS_INLINE": True, "TOKEN_ENCRYPTION_KEY": KEY,
           "GOOGLE_CLIENT_ID": "cid", "GOOGLE_CLIENT_SECRET": "cs", "GOOGLE_REDIRECT_URI": "http://api.test/cb",
           "SQLALCHEMY_ENGINE_OPTIONS": {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}}}
    cfg.update(extra)
    return create_app(cfg)


@pytest.fixture()
def app():
    a = make_app()
    yield a
    with a.app_context():
        db.drop_all()


def login(c, email="a@example.com"):
    r = c.post("/api/auth/dev-login", json={"email": email})
    return {"Authorization": "Bearer " + r.get_json()["data"]["token"]}


class ScriptedClient:
    """Fake Gemini client. Each step is a text reply, a list of (tool, args) or a callable returning either
    (callables let a step use ids that only exist at run time)."""

    def __init__(self, script):
        self.script, self.seen = list(script), []
        self.models = SimpleNamespace(generate_content=self._gen)

    def _gen(self, model, contents, config):
        self.seen.append(list(contents))
        step = self.script.pop(0)
        step = step() if callable(step) else step
        if isinstance(step, Exception):
            raise step
        if isinstance(step, str):
            return SimpleNamespace(function_calls=None, text=step)
        calls = [SimpleNamespace(name=n, args=a) for n, a in step]
        return SimpleNamespace(function_calls=calls, text=None, candidates=[SimpleNamespace(content="turn")])


def pid():
    return Presentation.query.order_by(Presentation.created_at.desc()).first().id


OUTLINE = {"title": "Solar Basics", "slides": [{"title": "Intro", "purpose": "hook"}, {"title": "Cost", "purpose": "prices"},
                                              {"title": "Wrap up", "purpose": "summary"}]}
CONTENT = {"slides": [{"slide_number": 2, "bullets": [{"text": "Panels got cheaper", "source_ids": []}]}]}
NOTES = {"notes": [{"slide_number": i, "text": f"Notes {i}"} for i in (1, 2, 3)]}


def happy_script():
    return [
        [("generate_slide_outline", {"topic": "solar", "slide_count": 3})],
        lambda: [("generate_slide_content", {"presentation_id": pid(), "slide_numbers": [2]})],
        lambda: [("apply_design_theme", {"presentation_id": pid(), "theme": "dark_blue"}),
                 ("add_speaker_notes", {"presentation_id": pid()})],
        lambda: [("verify_presentation", {"presentation_id": pid()})],
        "Deck ready. Slide 2 has an unsourced claim.",
    ]


def use_gemini(monkeypatch, script, json_queue=()):
    client = ScriptedClient(script)
    q = list(json_queue)
    client.json_prompts = []
    monkeypatch.setattr(gemini, "_client", lambda: client)
    monkeypatch.setattr(gemini, "generate_json",
                        lambda prompt, system=None, temperature=0.4: client.json_prompts.append(prompt) or q.pop(0))
    return client


GOOD = {"topic": "Solar energy basics", "slide_count": 3, "audience": "beginners", "theme": "dark_blue"}


# ---------------- validation ----------------

@pytest.mark.parametrize("override", [
    {"topic": "ab"}, {"topic": "x" * 501}, {"slide_count": 2}, {"slide_count": 41}, {"slide_count": "ten"}, {"slide_count": True},
    {"audience": "aliens"}, {"theme": "neon"}, {"citation_style": "Chicago"}, {"complexity": "godlike"},
    {"duration_minutes": 0}, {"publish": "yes"}, {"use_web_research": 1}, {"document_ids": "abc"},
])
def test_create_rejects_invalid_input(app, override):
    with app.test_client() as c:
        h = login(c)
        r = c.post("/api/presentation/create", json={**GOOD, **override}, headers=h)
        assert r.status_code == 400, override
    with app.app_context():
        assert BackgroundJob.query.count() == 0


def test_create_preconditions(app, monkeypatch):
    with app.test_client() as c:
        assert c.post("/api/presentation/create", json=GOOD).status_code == 401
        h = login(c)
        assert c.post("/api/presentation/create", json={**GOOD, "publish": True}, headers=h).status_code == 403
        assert c.post("/api/presentation/create", json={**GOOD, "document_ids": ["nope"]}, headers=h).status_code == 404
        # another user's document is not usable
        with app.app_context():
            other = User(email="o@example.com")
            db.session.add(other)
            db.session.flush()
            d = Document(user_id=other.id, filename="x.pdf", file_type="pdf", size_bytes=1, content_hash="h", status="indexed")
            db.session.add(d)
            db.session.commit()
            did = d.id
        assert c.post("/api/presentation/create", json={**GOOD, "document_ids": [did]}, headers=h).status_code == 404
    keyless = make_app(GEMINI_API_KEY="")
    with keyless.test_client() as c:
        assert c.post("/api/presentation/create", json=GOOD, headers=login(c)).status_code == 503


# ---------------- end to end ----------------





def test_selected_documents_restrict_search_and_extraction(app):
    from agents import registry
    from rag import embed, store
    from tests.test_phase3 import fake_embed, make_pdf
    embed_orig = embed.embed_texts
    embed.embed_texts = fake_embed
    try:
        with app.app_context():
            u = User(email="d@example.com")
            db.session.add(u)
            db.session.commit()
            a, _ = store.index_document(u.id, "a.pdf", make_pdf())
            b, _ = store.index_document(u.id, "b.txt", b"battery storage notes for the grid")
            ctx = ToolContext(user_id=u.id, overrides={"document_ids": [a.id]})
            r = registry.execute("search_knowledge_base", {"query": "battery storage grid", "k": 10, "document_ids": [b.id]}, ctx)
            assert {x["filename"] for x in r["results"]} == {"a.pdf"}  # model asked for b.txt: still confined to a.pdf
            assert registry.execute("extract_document", {"document_id": b.id}, ctx)["ok"] is False
            assert [d["filename"] for d in registry.execute("extract_document", {}, ctx)["documents"]] == ["a.pdf"]
    finally:
        embed.embed_texts = embed_orig








# ---------------- concurrency, staleness, isolation ----------------

def test_one_active_job_per_user_and_stale_jobs_are_reaped(app, monkeypatch):
    use_gemini(monkeypatch, ["Nothing built."])
    with app.test_client() as c:
        h = login(c)
        with app.app_context():
            u = User.query.first()
            j = BackgroundJob(user_id=u.id, kind=jobs.KIND, status="running", progress=40, payload={"log": []})
            db.session.add(j)
            db.session.commit()
            jid = j.id
        r = c.post("/api/presentation/create", json=GOOD, headers=h)
        assert r.status_code == 409 and r.get_json()["error"]["details"]["job_id"] == jid
        with app.app_context():  # worker died: no heartbeat for longer than the stale window
            j = db.session.get(BackgroundJob, jid)
            j.updated_at = datetime.now(timezone.utc) - timedelta(seconds=jobs.STALE_SECONDS + 60)
            db.session.commit()
        st = c.get(f"/api/presentation/status?job_id={jid}", headers=h).get_json()["data"]
        assert st["status"] == "failed" and "interrupted" in st["error"]
        assert c.post("/api/presentation/create", json=GOOD, headers=h).status_code == 202  # now allowed again


def test_status_is_private_to_owner(app, monkeypatch):
    use_gemini(monkeypatch, ["x"])
    with app.test_client() as c:
        h1, h2 = login(c), login(c, "b@example.com")
        jid = c.post("/api/presentation/create", json=GOOD, headers=h1).get_json()["data"]["job_id"]
        assert c.get(f"/api/presentation/status?job_id={jid}", headers=h2).status_code == 404
        assert c.get("/api/presentation/status", headers=h1).status_code == 404


def test_progress_never_goes_backwards(app):
    with app.app_context():
        u = User(email="p@example.com")
        db.session.add(u)
        db.session.flush()
        j = BackgroundJob(user_id=u.id, kind=jobs.KIND, status="running", progress=5, payload={"log": []})
        db.session.add(j)
        db.session.commit()
        jobs._record(j.id, "generate_slide_content", "success")
        jobs._record(j.id, "search_knowledge_base", "success")
        jobs._record(j.id, "create_google_slides", "error")  # failed step does not advance progress
        j = db.session.get(BackgroundJob, j.id)
        assert j.progress == 60 and [e["status"] for e in j.payload["log"]] == ["success", "success", "error"]


def test_task_prompt_reflects_settings():
    base = {"topic": "T", "slide_count": 5, "audience": "researchers", "language": "Hindi", "complexity": "advanced",
            "citation_style": "IEEE", "theme": "minimal", "duration_minutes": 12, "document_ids": ["d1"],
            "use_web_research": True, "publish": True}
    p = jobs.build_task_prompt(base, ["energy.pdf"])
    for needle in ("Hindi", "advanced", "IEEE", "'minimal'", "12 minutes", "energy.pdf (id d1)", "encouraged", "create_google_slides"):
        assert needle in p
    q = jobs.build_task_prompt({**base, "document_ids": [], "use_web_research": False, "publish": False}, [])
    assert "NOT allowed" in q and "keep it as a draft" in q and "No documents were selected" in q


# ---------------- workspace actions ----------------

def make_pres(app, email="a@example.com"):
    with app.app_context():
        u = User.query.filter_by(email=email).first()
        ctx = ToolContext(user_id=u.id)
        q = [OUTLINE]
        import services.gemini as g
        orig = g.generate_json
        g.generate_json = lambda *a, **k: q.pop(0)
        try:
            from agents import registry
            return registry.execute("generate_slide_outline", {"topic": "solar", "slide_count": 3}, ctx)["presentation_id"]
        finally:
            g.generate_json = orig


def test_theme_publish_and_edit_in_chat(app, monkeypatch):
    with app.test_client() as c:
        h, h2 = login(c), login(c, "b@example.com")
        p = make_pres(app)
        assert c.post(f"/api/presentation/{p}/theme", json={"theme": "Dark Blue"}, headers=h).get_json()["data"]["theme"] == "dark_blue"
        assert c.post(f"/api/presentation/{p}/theme", json={"theme": "neon"}, headers=h).status_code == 400
        assert c.post(f"/api/presentation/{p}/theme", json={"theme": "minimal"}, headers=h2).status_code == 404
        assert c.post(f"/api/presentation/{p}/publish", headers=h).status_code == 403  # Google not connected
        with app.app_context():
            google_auth.store_grant(User.query.filter_by(email="a@example.com").first(), "R", sorted(SCOPES))
            db.session.commit()
        monkeypatch.setattr(slides, "build_services", lambda creds: slides.Services(FakeSlidesAPI(), FakeDrive()))
        r = c.post(f"/api/presentation/{p}/publish", headers=h)
        assert r.status_code == 200 and r.get_json()["data"]["url"].endswith("/gid123/edit")
        assert c.post(f"/api/presentation/{p}/publish", headers=h2).status_code == 404

        seen = {}
        monkeypatch.setattr(conv_routes, "run_agent", lambda history, ctx, active=None, **kw: seen.update(active=active) or "ok")
        assert c.post("/api/chat", json={"message": "make slide 2 simpler", "presentation_id": p}, headers=h).status_code == 200
        assert seen["active"] == p
        seen.clear()
        assert c.post("/api/chat", json={"message": "hi", "presentation_id": p}, headers=h2).status_code == 200
        assert seen["active"] is None  # another user's presentation is never attached to this chat
        assert c.post("/api/chat", json={"message": "hi", "presentation_id": "nope"}, headers=h).status_code == 200  # unknown id is ignored, not an error


def test_chat_edit_background_job_synchronization(app, monkeypatch):
    with app.test_client() as c:
        h = login(c)
        p = make_pres(app)

        # Start conversation
        res = c.post("/api/conversations", headers=h).get_json()["data"]
        cid = res["id"]

        # User tells the AI some changes on their presentation
        monkeypatch.setattr(conv_routes, "run_agent", lambda history, ctx, active=None, **kw: "Changed slide 2 to blue.")
        chat_res = c.post("/api/chat", json={
            "conversation_id": cid,
            "message": "Change slide 2 to blue",
            "presentation_id": p,
        }, headers=h).get_json()["data"]

        # Verify job_id is returned
        assert "job_id" in chat_res
        job_id = chat_res["job_id"]
        assert chat_res["active_presentation_id"] == p

        # Verify job status endpoint works for edit jobs
        status_res = c.get(f"/api/presentation/status?job_id={job_id}", headers=h).get_json()["data"]
        assert status_res["job_id"] == job_id
        assert status_res["kind"] == "edit_presentation"

        # Verify get_conversation returns completed messages with presentation_id
        conv_res = c.get(f"/api/conversations/{cid}", headers=h).get_json()["data"]
        msgs = conv_res["messages"]
        assert any(m["role"] == "user" and "Change slide 2 to blue" in m["content"] for m in msgs)
        assert any(m["role"] == "assistant" and "Changed slide 2 to blue" in m["content"] for m in msgs)
