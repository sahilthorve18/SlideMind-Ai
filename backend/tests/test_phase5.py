import os
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

os.environ["SLIDEMIND_SKIP_AUTOAPP"] = "1"

import httplib2
import pytest
from cryptography.fernet import Fernet
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from agents import registry
from agents.registry import ToolContext
from app import create_app
from database import db
from models import Presentation, User
from routes import conversations as conv_routes
from services import crypto, gemini, google_auth, slides
from services.google_auth import GoogleAuthExpired, SCOPES, SCOPE_DRIVE, SCOPE_SLIDES

KEY = Fernet.generate_key().decode()
ALL_SCOPES = sorted(SCOPES)
IDENTITY_ONLY = [s for s in SCOPES if s not in (SCOPE_SLIDES, SCOPE_DRIVE)]


def make_app(**extra):
    cfg = {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "DEV_LOGIN_ENABLED": True,
           "RATELIMIT_ENABLED": False, "GEMINI_API_KEY": "k", "GOOGLE_CLIENT_ID": "cid.apps.googleusercontent.com",
           "GOOGLE_CLIENT_SECRET": "csecret", "GOOGLE_REDIRECT_URI": "http://api.test/api/auth/google/callback",
           "FRONTEND_URL": "http://front.test", "TOKEN_ENCRYPTION_KEY": KEY}
    cfg.update(extra)
    return create_app(cfg)


@pytest.fixture()
def app():
    a = make_app()
    yield a
    with a.app_context():
        db.drop_all()


def info(**kw):
    base = {"sub": "g-1", "email": "sahil@example.com", "email_verified": True, "name": "Sahil", "picture": "http://p",
            "refresh_token": "REFRESH-SECRET", "scopes": ALL_SCOPES}
    base.update(kw)
    return base


def fragment(resp):
    loc = resp.headers["Location"]
    assert loc.startswith("http://front.test/#")
    return {k: v[0] for k, v in parse_qs(urlparse(loc).fragment).items()}


# ---------------- OAuth ----------------

def test_state_is_signed_tamper_proof_and_expires(app):
    with app.app_context():
        s = google_auth.new_state()
        assert google_auth.verify_state(s)
        assert not google_auth.verify_state(s + "x") and not google_auth.verify_state("") and not google_auth.verify_state("garbage")
        google_auth.STATE_MAX_AGE, old = -1, google_auth.STATE_MAX_AGE
        try:
            assert not google_auth.verify_state(s)
        finally:
            google_auth.STATE_MAX_AGE = old


def test_start_returns_consent_url_with_offline_access_and_scopes(app):
    with app.test_client() as c:
        d = c.post("/api/auth/google").get_json()["data"]
    q = parse_qs(urlparse(d["auth_url"]).query)
    assert q["client_id"] == ["cid.apps.googleusercontent.com"] and q["access_type"] == ["offline"]
    assert q["redirect_uri"] == ["http://api.test/api/auth/google/callback"] and q["state"] == [d["state"]]
    assert {SCOPE_SLIDES, SCOPE_DRIVE} <= set(q["scope"][0].split())
    assert "client_secret" not in d["auth_url"]


def test_start_unconfigured_is_503():
    a = make_app(GOOGLE_CLIENT_ID="")
    with a.test_client() as c:
        assert c.post("/api/auth/google").status_code == 503


def test_callback_creates_user_encrypts_token_and_returns_only_our_token(app, monkeypatch):
    monkeypatch.setattr(google_auth, "exchange_code", lambda code: info())
    with app.test_client() as c:
        state = google_auth.new_state() if False else c.post("/api/auth/google").get_json()["data"]["state"]
        r = c.get(f"/api/auth/google/callback?code=abc&state={state}")
        assert r.status_code == 302
        frag = fragment(r)
        assert frag["state"] == state and "REFRESH-SECRET" not in r.headers["Location"]
        me = c.get("/api/auth/me", headers={"Authorization": "Bearer " + frag["token"]}).get_json()["data"]
        assert me["email"] == "sahil@example.com" and me["google_connected"] is True
    with app.app_context():
        u = User.query.filter_by(email="sahil@example.com").one()
        assert u.google_refresh_token_enc and u.google_refresh_token_enc != "REFRESH-SECRET"
        assert "REFRESH-SECRET" not in u.google_refresh_token_enc
        assert crypto.decrypt(u.google_refresh_token_enc) == "REFRESH-SECRET"


@pytest.mark.parametrize("query,expected", [
    ("error=access_denied", "google_denied"), ("code=abc&state=forged", "invalid_state"), ("state=x", "invalid_state"),
])
def test_callback_rejects_bad_requests(app, monkeypatch, query, expected):
    monkeypatch.setattr(google_auth, "exchange_code", lambda code: info())
    with app.test_client() as c:
        assert fragment(c.get("/api/auth/google/callback?" + query)) == {"error": expected}
    with app.app_context():
        assert User.query.count() == 0


def test_callback_rejects_unverified_email_and_failed_exchange(app, monkeypatch):
    with app.test_client() as c:
        state = c.post("/api/auth/google").get_json()["data"]["state"]
        monkeypatch.setattr(google_auth, "exchange_code", lambda code: info(email_verified=False))
        assert fragment(c.get(f"/api/auth/google/callback?code=a&state={state}")) == {"error": "email_unverified"}

        def boom(code):
            raise google_auth.GoogleAuthError("x")
        monkeypatch.setattr(google_auth, "exchange_code", boom)
        frag = fragment(c.get(f"/api/auth/google/callback?code=a&state={state}"))
        assert frag.get("error") == "google_failed"
    with app.app_context():
        assert User.query.count() == 0


def test_missing_slides_scope_means_not_connected(app, monkeypatch):
    monkeypatch.setattr(google_auth, "exchange_code", lambda code: info(scopes=IDENTITY_ONLY))
    with app.test_client() as c:
        state = c.post("/api/auth/google").get_json()["data"]["state"]
        frag = fragment(c.get(f"/api/auth/google/callback?code=a&state={state}"))
        me = c.get("/api/auth/me", headers={"Authorization": "Bearer " + frag["token"]}).get_json()["data"]
        assert me["google_connected"] is False


def test_existing_email_account_is_linked_not_duplicated(app, monkeypatch):
    monkeypatch.setattr(google_auth, "exchange_code", lambda code: info())
    with app.test_client() as c:
        c.post("/api/auth/dev-login", json={"email": "sahil@example.com"})
        state = c.post("/api/auth/google").get_json()["data"]["state"]
        c.get(f"/api/auth/google/callback?code=a&state={state}")
    with app.app_context():
        assert User.query.count() == 1 and User.query.first().google_sub == "g-1"


def test_disconnect_revokes_and_clears(app, monkeypatch):
    revoked = []
    monkeypatch.setattr(google_auth.requests, "post", lambda url, params=None, timeout=None: revoked.append(params))
    monkeypatch.setattr(google_auth, "exchange_code", lambda code: info())
    with app.test_client() as c:
        state = c.post("/api/auth/google").get_json()["data"]["state"]
        h = {"Authorization": "Bearer " + fragment(c.get(f"/api/auth/google/callback?code=a&state={state}"))["token"]}
        assert c.post("/api/auth/google/disconnect", headers=h).get_json()["data"]["google_connected"] is False
    assert revoked == [{"token": "REFRESH-SECRET"}]
    with app.app_context():
        u = User.query.first()
        assert u.google_refresh_token_enc is None and google_auth.credentials_for(u) is None


def test_crypto_wrong_key_returns_none(app):
    with app.app_context():
        tok = crypto.encrypt("secret")
        app.config["TOKEN_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
        assert crypto.decrypt(tok) is None


# ---------------- request builders ----------------

def test_first_slide_uses_title_layout_and_body_slides_use_placeholders():
    reqs, ids, nr = slides.slide_requests(0, {"title": "Solar", "bullets": ["Sub"], "layout": "title_bullets"}, "modern_dark")
    cs = reqs[0]["createSlide"]
    assert cs["slideLayoutReference"]["predefinedLayout"] == "TITLE_SLIDE" and cs["insertionIndex"] == 0
    assert {m["layoutPlaceholder"]["type"] for m in cs["placeholderIdMappings"]} == {"CENTERED_TITLE", "SUBTITLE"}
    reqs, ids, nr = slides.slide_requests(2, {"title": "Cost", "bullets": ["a", "b"], "layout": "title_bullets"}, "dark_blue")
    assert reqs[0]["createSlide"]["slideLayoutReference"]["predefinedLayout"] == "TITLE_AND_BODY"
    inserts = {r["insertText"]["objectId"]: r["insertText"]["text"] for r in reqs if "insertText" in r}
    assert inserts[ids["title"]] == "Cost" and inserts[ids["body"]] == "a\nb"
    bg = next(r for r in reqs if "updatePageProperties" in r)["updatePageProperties"]
    assert bg["objectId"] == ids["slide"] and bg["pageProperties"]["pageBackgroundFill"]["solidFill"]["color"]["rgbColor"]["blue"] == 0.28
    assert nr == []


def test_unrendered_elements_are_reported_not_hidden():
    _, _, nr = slides.slide_requests(1, {"title": "Chart", "bullets": [], "layout": "chart"}, "minimal")
    assert nr == [{"slide": 2, "what": "chart", "reason": "chart rendering is not implemented yet"}]
    _, _, nr = slides.slide_requests(1, {"title": "D", "bullets": ["x"], "layout": "diagram"}, "minimal")
    assert nr[0]["what"] == "diagram"


def test_table_requests_and_validation():
    reqs = slides.table_requests("slide1", [["", "A", "B"], ["Cost", "1", "2"]], "tbl_12345")
    assert reqs[0]["createTable"]["rows"] == 2 and reqs[0]["createTable"]["columns"] == 3
    assert sum("insertText" in r for r in reqs) == 5  # empty cell skipped
    with pytest.raises(slides.SlidesError):
        slides.table_requests("s", [["a", "b"], ["c"]])
    with pytest.raises(slides.SlidesError):
        slides.table_requests("s", [])


def test_notes_text_appends_sources():
    t = slides.notes_text({"notes": "Say hi", "sources": [{"filename": "energy.pdf", "page_number": 2},
                                                          {"filename": "IEA", "url": "https://iea.org/x"}]})
    assert t.startswith("Say hi") and "- energy.pdf, p.2" in t and "- IEA (https://iea.org/x)" in t
    assert slides.notes_text({}) == ""


# ---------------- fake Google services ----------------

class Req:
    def __init__(self, fn):
        self.fn = fn

    def execute(self):
        return self.fn()


class FakeSlidesAPI:
    def __init__(self):
        self.log, self.slide_ids = [], []

    def presentations(self):
        return self

    def create(self, body):
        self.log.append(("create", body))
        return Req(lambda: {"presentationId": "gid123", "slides": [{"objectId": "default_slide"}]})

    def batchUpdate(self, presentationId, body):
        self.log.append(("batch", body["requests"]))
        self.slide_ids += [r["createSlide"]["objectId"] for r in body["requests"] if "createSlide" in r]
        return Req(lambda: {})

    def get(self, presentationId, fields):
        self.log.append(("get", fields))
        return Req(lambda: {"slides": [{"objectId": o, "slideProperties": {"notesPage": {"notesProperties": {
            "speakerNotesObjectId": "notes_" + o}}}} for o in self.slide_ids]})


class FakeDrive:
    def __init__(self, data=b"PKfile"):
        self.data, self.calls = data, []

    def files(self):
        return self

    def export_media(self, fileId, mimeType):
        self.calls.append((fileId, mimeType))
        return Req(lambda: self.data)


DRAFT = {"title": "Solar", "theme": "dark_blue", "slides": [
    {"title": "Solar", "bullets": [], "layout": "title_bullets", "notes": "Welcome", "sources": []},
    {"title": "Cost", "bullets": ["Cheap"], "layout": "title_bullets", "notes": None,
     "sources": [{"filename": "energy.pdf", "page_number": 2}]},
    {"title": "Trend", "bullets": [], "layout": "chart", "notes": None, "sources": []}]}


def test_publish_draft_sequence_and_notes():
    api = FakeSlidesAPI()
    res = slides.publish_draft(slides.Services(slides=api, drive=FakeDrive()), DRAFT)
    kinds = [k for k, _ in api.log]
    assert kinds == ["create", "batch", "get", "batch"]
    main = api.log[1][1]
    creates = [r for r in main if "createSlide" in r]
    assert len(creates) == 3 and main[-1] == {"deleteObject": {"objectId": "default_slide"}}  # starter slide removed last
    assert len({r["createSlide"]["objectId"] for r in creates}) == 3
    notes = {r["insertText"]["objectId"]: r["insertText"]["text"] for r in api.log[3][1]}
    assert set(notes) == {"notes_" + api.slide_ids[0], "notes_" + api.slide_ids[1]}  # slide 3 has no notes/sources
    assert "Sources:\n- energy.pdf, p.2" in notes["notes_" + api.slide_ids[1]]
    assert res["url"] == "https://docs.google.com/presentation/d/gid123/edit" and res["notes_written"] == 2
    assert res["not_rendered"][0]["what"] == "chart" and res["slide_object_ids"] == api.slide_ids


def test_execute_retries_transient_then_succeeds(monkeypatch):
    monkeypatch.setattr(slides.time, "sleep", lambda s: None)
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise HttpError(httplib2.Response({"status": 503}), b"")
        return {"ok": 1}
    assert slides._execute(Req(flaky)) == {"ok": 1} and len(calls) == 3


@pytest.mark.parametrize("exc,expected", [
    (HttpError(httplib2.Response({"status": 403}), b""), slides.SlidesError),
    (HttpError(httplib2.Response({"status": 404}), b""), slides.SlidesError),
    (HttpError(httplib2.Response({"status": 401}), b""), GoogleAuthExpired),
    (RefreshError("invalid_grant"), GoogleAuthExpired),
])
def test_execute_maps_errors(monkeypatch, exc, expected):
    monkeypatch.setattr(slides.time, "sleep", lambda s: None)

    def fail():
        raise exc
    with pytest.raises(expected) as e:
        slides._execute(Req(fail))
    assert "invalid_grant" not in str(e.value)  # no raw upstream detail leaks


def test_export_file_validates():
    assert slides.export_file(slides.Services(None, FakeDrive(b"%PDF")), "gid", "pdf") == b"%PDF"
    with pytest.raises(slides.SlidesError):
        slides.export_file(slides.Services(None, FakeDrive()), "gid", "exe")
    with pytest.raises(slides.SlidesError):
        slides.export_file(slides.Services(None, FakeDrive(b"")), "gid", "pdf")


# ---------------- publish tool + export route ----------------

OUTLINE = {"title": "Solar Basics", "slides": [{"title": "Intro", "purpose": "x"}, {"title": "Cost", "purpose": "y"},
                                              {"title": "Wrap", "purpose": "z"}]}


def connected_user(app):
    u = User(email="u@example.com")
    db.session.add(u)
    db.session.flush()
    google_auth.store_grant(u, "R-TOKEN", ALL_SCOPES)
    db.session.commit()
    return u


def deck(ctx, monkeypatch):
    queue = [OUTLINE]
    monkeypatch.setattr(gemini, "generate_json", lambda prompt, system=None, temperature=0.4: queue.pop(0))
    return registry.execute("generate_slide_outline", {"topic": "solar", "slide_count": 3}, ctx)["presentation_id"]


def test_create_google_slides_publishes_and_records_ids(app, monkeypatch):
    with app.app_context():
        u = connected_user(app)
        ctx = ToolContext(user_id=u.id, google_connected=True)
        pid = deck(ctx, monkeypatch)
        api = FakeSlidesAPI()
        monkeypatch.setattr(slides, "build_services", lambda creds: slides.Services(api, FakeDrive()))
        r = registry.execute("create_google_slides", {"presentation_id": pid}, ctx)
        assert r["ok"] and r["url"] == "https://docs.google.com/presentation/d/gid123/edit" and r["slides"] == 3
        p = db.session.get(Presentation, pid)
        assert p.google_presentation_id == "gid123" and p.status == "published"
        assert [s.google_object_id for s in p.slides] == api.slide_ids
        n_calls = len(api.log)
        again = registry.execute("create_google_slides", {"presentation_id": pid}, ctx)
        assert again["already_published"] and len(api.log) == n_calls  # no duplicate file created
        edit = registry.execute("edit_existing_slide", {"presentation_id": pid, "slide_number": 2, "title": "Costs"}, ctx)
        assert edit["google_synced"] is False and "NOT yet" in edit["warning"]


def test_create_google_slides_failure_modes_do_not_fake_success(app, monkeypatch):
    with app.app_context():
        u = connected_user(app)
        ctx = ToolContext(user_id=u.id, google_connected=True)
        pid = deck(ctx, monkeypatch)

        def refused(creds):
            raise slides.SlidesError("Google refused the request (403).")
        monkeypatch.setattr(slides, "build_services", refused)
        r = registry.execute("create_google_slides", {"presentation_id": pid}, ctx)
        assert r["ok"] is False and "403" in r["error"]
        assert db.session.get(Presentation, pid).google_presentation_id is None

        def expired(creds):
            raise GoogleAuthExpired("x")
        monkeypatch.setattr(slides, "build_services", expired)
        r = registry.execute("create_google_slides", {"presentation_id": pid}, ctx)
        assert r["ok"] is False and "reconnect" in r["error"].lower()
        assert google_auth.is_connected(db.session.get(User, u.id)) is False  # dead grant cleared


def test_export_endpoint(app, monkeypatch):
    drive = FakeDrive(b"PK-pptx-bytes")
    monkeypatch.setattr(slides, "build_services", lambda creds: slides.Services(FakeSlidesAPI(), drive))
    monkeypatch.setattr(gemini, "generate_json", lambda *a, **k: OUTLINE)
    with app.test_client() as c:
        # sign in through the Google flow so the grant is real
        monkeypatch.setattr(google_auth, "exchange_code", lambda code: info())
        state = c.post("/api/auth/google").get_json()["data"]["state"]
        h = {"Authorization": "Bearer " + fragment(c.get(f"/api/auth/google/callback?code=a&state={state}"))["token"]}
        with app.app_context():
            u = User.query.first()
            ctx = ToolContext(user_id=u.id, google_connected=True)
            pid = registry.execute("generate_slide_outline", {"topic": "solar", "slide_count": 3}, ctx)["presentation_id"]
        assert c.get(f"/api/presentation/{pid}/export", headers=h).status_code == 409  # not published yet
        with app.app_context():
            registry.execute("create_google_slides", {"presentation_id": pid}, ctx)
        r = c.get(f"/api/presentation/{pid}/export?format=pptx", headers=h)
        assert r.status_code == 200 and r.data == b"PK-pptx-bytes" and "Solar Basics.pptx" in r.headers["Content-Disposition"]
        assert drive.calls[-1] == ("gid123", slides.PPTX_MIME)
        assert c.get(f"/api/presentation/{pid}/export?format=exe", headers=h).status_code == 400
        det = c.get(f"/api/presentation/{pid}", headers=h).get_json()["data"]
        assert det["google_url"].endswith("/gid123/edit") and len(det["slides"]) == 3
        # another user cannot read or export it
        c.post("/api/auth/dev-login", json={"email": "other@example.com"})
        h2 = {"Authorization": "Bearer " + c.post("/api/auth/dev-login", json={"email": "other@example.com"}).get_json()["data"]["token"]}
        assert c.get(f"/api/presentation/{pid}", headers=h2).status_code == 404
        assert c.get(f"/api/presentation/{pid}/export", headers=h2).status_code == 404


def test_chat_marks_google_connected_on_tool_context(app, monkeypatch):
    seen = {}
    monkeypatch.setattr(conv_routes, "run_agent", lambda history, ctx, active=None, **kw: seen.update(g=ctx.google_connected) or "ok")
    monkeypatch.setattr(google_auth, "exchange_code", lambda code: info())
    with app.test_client() as c:
        state = c.post("/api/auth/google").get_json()["data"]["state"]
        h = {"Authorization": "Bearer " + fragment(c.get(f"/api/auth/google/callback?code=a&state={state}"))["token"]}
        c.post("/api/chat", json={"message": "hi"}, headers=h)
        assert seen["g"] is True
        h2 = {"Authorization": "Bearer " + c.post("/api/auth/dev-login", json={"email": "x@example.com"}).get_json()["data"]["token"]}
        c.post("/api/chat", json={"message": "hi"}, headers=h2)
        assert seen["g"] is False
