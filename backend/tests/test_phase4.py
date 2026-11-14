import io
import math
import os
from types import SimpleNamespace

os.environ["SLIDEMIND_SKIP_AUTOAPP"] = "1"

import pytest

from agents import agent, registry
from agents.registry import ToolContext
from app import create_app
from database import db
from models import Presentation, ToolExecutionLog, User
from rag import embed
from services import gemini
from tests.test_phase3 import fake_embed, make_pdf, upload, login  # reuse helpers

EXPECTED_TOOLS = {
    "search_knowledge_base", "web_research", "extract_document", "generate_slide_outline", "generate_slide_content",
    "create_google_slides", "add_slide", "delete_slide", "edit_existing_slide", "apply_design_theme", "generate_diagram",
    "generate_chart", "add_speaker_notes", "verify_presentation", "generate_references", "calculate_presentation_duration",
}


@pytest.fixture()
def app(monkeypatch):
    monkeypatch.setattr(embed, "embed_texts", fake_embed)
    a = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "DEV_LOGIN_ENABLED": True,
                    "RATELIMIT_ENABLED": False, "GEMINI_API_KEY": "test-key"})
    yield a
    with a.app_context():
        db.drop_all()


@pytest.fixture()
def ctx(app):
    with app.app_context():
        u = User(email="t@example.com")
        db.session.add(u)
        db.session.commit()
        yield ToolContext(user_id=u.id)


def fake_json(responses):
    """Monkeypatch helper: returns queued dicts from gemini.generate_json."""
    queue = list(responses)
    return lambda prompt, system=None, temperature=0.4: queue.pop(0)


OUTLINE = {"title": "Solar Basics", "slides": [{"title": "Intro", "purpose": "hook"}, {"title": "Cost", "purpose": "prices"},
                                              {"title": "Wrap up", "purpose": "summary"}]}


def make_deck(ctx, monkeypatch):
    monkeypatch.setattr(gemini, "generate_json", fake_json([OUTLINE]))
    r = registry.execute("generate_slide_outline", {"topic": "solar", "slide_count": 3}, ctx)
    assert r["ok"], r
    return r["presentation_id"]


# ---- registry ----

def test_all_16_tools_registered_with_valid_gemini_declarations():
    assert set(registry.REGISTRY) == EXPECTED_TOOLS
    assert len(registry.declarations()) == 16


def test_unknown_tool_and_bad_args_fail_gracefully_and_log(ctx):
    assert registry.execute("nope", {}, ctx)["ok"] is False
    r = registry.execute("search_knowledge_base", {}, ctx)
    assert r["ok"] is False and "query" in r["error"]
    r = registry.execute("add_slide", {"presentation_id": "x", "title": 5}, ctx)
    assert r["ok"] is False
    assert ToolExecutionLog.query.filter_by(user_id=ctx.user_id, status="error").count() == 3
    assert [c["status"] for c in ctx.calls] == ["error"] * 3


def test_google_tool_blocked_without_connection(ctx, monkeypatch):
    pid = make_deck(ctx, monkeypatch)
    r = registry.execute("create_google_slides", {"presentation_id": pid}, ctx)
    assert r["ok"] is False and "Google" in r["error"] and "http" not in str(r)
    ctx.google_connected = True  # flag set but no stored grant: still refuses rather than faking a link
    r = registry.execute("create_google_slides", {"presentation_id": pid}, ctx)
    assert r["ok"] is False and "not available" in r["error"] and "docs.google.com" not in str(r)


# ---- draft tools ----

def test_outline_then_edit_flow_preserves_other_slides(ctx, monkeypatch):
    pid = make_deck(ctx, monkeypatch)
    monkeypatch.setattr(gemini, "generate_json", fake_json([{"slides": [
        {"slide_number": 2, "bullets": [{"text": "Panels cost $1/W", "source_ids": ["S1", "BOGUS"]},
                                          {"text": "Framing point", "source_ids": []}]}]}]))
    r = registry.execute("generate_slide_content", {"presentation_id": pid, "slide_numbers": [2],
                                                     "sources": [{"id": "S1", "text": "Panels cost $1/W in 2024."}]}, ctx)
    assert r["ok"] and r["slides_written"] == [2] and r["bullets_without_source"] == 1
    p = db.session.get(Presentation, pid)
    b = p.slides[1].content["bullets"]
    assert b[0]["source_ids"] == ["S1"]  # invented source id dropped
    assert p.slides[0].content["bullets"] == [] and p.slides[2].content["bullets"] == []

    assert registry.execute("edit_existing_slide", {"presentation_id": pid, "slide_number": 2, "title": "Costs"}, ctx)["ok"]
    assert registry.execute("add_slide", {"presentation_id": pid, "title": "Extra", "position": 2}, ctx)["slide_count"] == 4
    assert [s.title for s in db.session.get(Presentation, pid).slides] == ["Intro", "Extra", "Costs", "Wrap up"]
    assert registry.execute("delete_slide", {"presentation_id": pid, "slide_number": 2}, ctx)["slide_count"] == 3
    assert [s.position for s in db.session.get(Presentation, pid).slides] == [1, 2, 3]
    assert registry.execute("apply_design_theme", {"presentation_id": pid, "theme": "Dark Blue"}, ctx)["theme"] == "dark_blue"
    assert registry.execute("apply_design_theme", {"presentation_id": pid, "theme": "neon"}, ctx)["ok"] is False
    assert registry.execute("edit_existing_slide", {"presentation_id": pid, "slide_number": 9, "title": "x"}, ctx)["ok"] is False


def test_user_cannot_touch_another_users_presentation(ctx, app, monkeypatch):
    pid = make_deck(ctx, monkeypatch)
    other = User(email="o@example.com")
    db.session.add(other)
    db.session.commit()
    r = registry.execute("delete_slide", {"presentation_id": pid, "slide_number": 1}, ToolContext(user_id=other.id))
    assert r["ok"] is False and "not found" in r["error"].lower()


def test_chart_requires_source_and_valid_data(ctx, monkeypatch):
    pid = make_deck(ctx, monkeypatch)
    base = {"presentation_id": pid, "slide_number": 2, "chart_type": "bar", "title": "T", "labels": ["a", "b"], "values": [1, 2]}
    assert registry.execute("generate_chart", base, ctx)["ok"] is False  # no source_ref
    assert registry.execute("generate_chart", {**base, "source_ref": 1, "values": [1]}, ctx)["ok"] is False
    assert registry.execute("generate_chart", {**base, "source_ref": 1}, ctx)["ok"] is True


def test_verify_references_duration(ctx, monkeypatch):
    pid = make_deck(ctx, monkeypatch)
    ctx.add_citation(source_type="document", filename="energy.pdf", page_number=1, section_heading=None, url=None, document_id="d")
    monkeypatch.setattr(gemini, "generate_json", fake_json([{"slides": [
        {"slide_number": 2, "bullets": [{"text": "x " * 100, "source_ids": ["S1"]}]}]}]))
    registry.execute("generate_slide_content", {"presentation_id": pid, "slide_numbers": [2],
                     "sources": [{"id": "S1", "text": "fact", "citation_ref": 1}]}, ctx)
    v = registry.execute("verify_presentation", {"presentation_id": pid}, ctx)
    types_ = {i["type"] for i in v["issues"]}
    assert {"overflow", "missing_notes"} <= types_ and v["blocking_issues"] >= 1
    refs = registry.execute("generate_references", {"presentation_id": pid, "style": "ieee"}, ctx)
    assert refs["references"] == ["[1] energy.pdf. (Uploaded document)"]
    d = registry.execute("calculate_presentation_duration", {"presentation_id": pid}, ctx)
    assert d["total_minutes"] > 0 and d["slides_estimated_without_notes"] == 3


def test_search_tool_returns_refs_and_is_user_scoped(app):
    from rag import store
    with app.app_context():
        a, b = User(email="a@x.com"), User(email="b@x.com")
        db.session.add_all([a, b])
        db.session.commit()
        store.index_document(a.id, "energy.pdf", make_pdf())
        ca, cb = ToolContext(user_id=a.id), ToolContext(user_id=b.id)
        r = registry.execute("search_knowledge_base", {"query": "battery storage grid", "k": 1}, ca)
        assert r["results"][0]["ref"] == 1 and r["results"][0]["page"] == 2 and ca.citations[0]["filename"] == "energy.pdf"
        assert registry.execute("search_knowledge_base", {"query": "battery"}, cb)["results"] == []


# ---- agent loop with a fake Gemini client (real SDK types for tool responses) ----

class FakeClient:
    def __init__(self, script):
        self.script, self.seen = list(script), []
        self.models = SimpleNamespace(generate_content=self._gen)

    def _gen(self, model, contents, config):
        self.seen.append(list(contents))
        step = self.script.pop(0)
        if isinstance(step, str):
            return SimpleNamespace(function_calls=None, text=step)
        calls = [SimpleNamespace(name=n, args=a) for n, a in step]
        return SimpleNamespace(function_calls=calls, text=None, candidates=[SimpleNamespace(content=f"model-turn:{calls[0].name}")])


def test_agent_chooses_tools_dynamically_and_feeds_results_back(app, monkeypatch):
    from rag import store
    with app.app_context():
        u = User(email="a@x.com")
        db.session.add(u)
        db.session.commit()
        store.index_document(u.id, "energy.pdf", make_pdf())
        client = FakeClient([[("search_knowledge_base", {"query": "solar cost"})], "Solar cost fell [1]."])
        monkeypatch.setattr(gemini, "_client", lambda: client)
        ctx = ToolContext(user_id=u.id)
        reply = agent.run_agent([{"role": "user", "content": "How has solar cost changed?"}], ctx)
        assert reply == "Solar cost fell [1]."
        assert [c["name"] for c in ctx.calls] == ["search_knowledge_base"]  # no fixed pipeline: only what the model asked for
        fr = client.seen[1][-1].parts[0].function_response
        assert fr.name == "search_knowledge_base" and fr.response["results"][0]["filename"] == "energy.pdf"
        assert [c["n"] for c in agent.used_citations(reply, ctx.citations)] == [1]
        assert agent.used_citations("No refs here", ctx.citations) == []


def test_agent_survives_failing_tool_and_unknown_tool(app, monkeypatch):
    with app.app_context():
        u = User(email="a@x.com")
        db.session.add(u)
        db.session.commit()
        client = FakeClient([[("delete_slide", {"presentation_id": "missing", "slide_number": 1}), ("hack_system", {})],
                             "I couldn't find that presentation."])
        monkeypatch.setattr(gemini, "_client", lambda: client)
        ctx = ToolContext(user_id=u.id)
        assert agent.run_agent([{"role": "user", "content": "delete slide 1"}], ctx) == "I couldn't find that presentation."
        assert [c["status"] for c in ctx.calls] == ["error", "error"]


def test_agent_step_budget_forces_final_answer(app, monkeypatch):
    with app.app_context():
        u = User(email="a@x.com")
        db.session.add(u)
        db.session.commit()
        client = FakeClient([[("extract_document", {})]] * agent.MAX_STEPS + ["Here is where I got to."])
        monkeypatch.setattr(gemini, "_client", lambda: client)
        assert agent.run_agent([{"role": "user", "content": "go"}], ToolContext(user_id=u.id)) == "Here is where I got to."


def test_system_prompt_lists_documents_and_active_draft(app, monkeypatch):
    from rag import store
    with app.app_context():
        u = User(email="a@x.com")
        db.session.add(u)
        db.session.commit()
        assert "not uploaded any documents" in agent.build_system_prompt(u.id, None)
        store.index_document(u.id, "energy.pdf", make_pdf())
        p = Presentation(user_id=u.id, title="Deck", settings={"theme": "minimal"})
        db.session.add(p)
        db.session.commit()
        s = agent.build_system_prompt(u.id, p.id)
        assert "energy.pdf" in s and "Active draft presentation: 'Deck'" in s


# ---- chat endpoint integration ----

def test_chat_endpoint_returns_tool_calls_and_active_presentation(app, monkeypatch):
    monkeypatch.setattr(gemini, "generate_json", fake_json([OUTLINE]))
    client = FakeClient([[("generate_slide_outline", {"topic": "solar", "slide_count": 3})], "Draft ready."])
    monkeypatch.setattr(gemini, "_client", lambda: client)
    with app.test_client() as c:
        h = login(c)
        d = c.post("/api/chat", json={"message": "Make a 3 slide deck on solar"}, headers=h).get_json()["data"]
        assert d["reply"] == "Draft ready." and d["tool_calls"][0]["name"] == "generate_slide_outline"
        assert d["active_presentation_id"]
        conv = c.get(f"/api/conversations/{d['conversation_id']}", headers=h).get_json()["data"]
        assert conv["messages"][-1]["tool_calls"][0]["status"] == "success"
