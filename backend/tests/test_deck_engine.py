"""Fact-first deck pipeline, composition engine and exporters. Gemini is scripted: no network, no fake product copy."""
import io
import re

import pytest
from pptx import Presentation as Pptx
from pptx.util import Pt

from database import db
from models import Presentation
from services import gemini
from services.deck import validators
from services.deck.blocks import normalize_block
from services.deck.solver import build_scene
from services.deck.tokens import COMP
from services.design_systems import DESIGN_SYSTEMS
from tests.test_phase6 import GOOD, app, login  # noqa: F401  (app fixture)

FACTS = [
    {"id": "F1", "claim": "Staff report a fault, which opens a ticket.", "number": None, "source": "user", "kind": "state"},
    {"id": "F2", "claim": "An admin assigns the ticket to a technician.", "number": None, "source": "user", "kind": "state"},
    {"id": "F3", "claim": "The technician repairs the equipment and marks it resolved.", "number": None, "source": "user", "kind": "state"},
    {"id": "F4", "claim": "Staff verify the fix before the ticket is closed; a rejected fix returns to in progress.", "number": None, "source": "user", "kind": "state"},
    {"id": "F5", "claim": "There are three roles: staff, technician and admin.", "number": "3", "source": "user", "kind": "role"},
]
TOPIC = "CampusCare ticketing for the CS lab equipment with staff, technician and admin roles"


def fake_json(prompt, system=None, temperature=0.4, model=None, images=None):
    if "Extract the atomic facts" in prompt:
        return {"facts": FACTS, "gaps": []}
    if "Plan a" in prompt:
        return {"deck_title": "CampusCare: lab faults get fixed on a tracked path", "tagline": "One ticket path from report to verified fix",
                "archetype": "project_review", "slides": [
                    {"n": 1, "role": "title", "message": "CampusCare tracks every lab fault", "shape": "idea", "fact_ids": ["F1"], "visual": "none"},
                    {"n": 2, "role": "content", "message": "Every fault follows one tracked path to a verified fix", "shape": "states", "fact_ids": ["F1", "F2", "F3", "F4"], "visual": "diagram"},
                    {"n": 3, "role": "content", "message": "Three roles share clear responsibilities", "shape": "cards", "fact_ids": ["F5"], "visual": "cards"},
                    {"n": 4, "role": "closing", "message": "Staff confirmation is what closes a ticket", "shape": "idea", "fact_ids": ["F4"], "visual": "none"}]}
    if "Write the slide specs" in prompt:
        out = []
        for n in map(int, re.findall(r"SLIDE (\d+) role", prompt)):
            if n == 1:
                out.append({"n": 1, "kind": "title", "title": "CampusCare tracks every lab fault", "tagline": "One ticket path from report to verified fix", "blocks": [], "visual_plan": "none", "notes": "Intro."})
            elif n == 2:
                out.append({"n": 2, "kind": "content", "title": "Every fault follows one tracked path to a verified fix", "kicker": "Lifecycle", "visual_plan": "diagram", "notes": "Walk the states.",
                            "blocks": [{"type": "diagram", "nodes": [{"id": "o", "label": "Open"}, {"id": "a", "label": "Assigned"}, {"id": "i", "label": "In progress"}, {"id": "r", "label": "Resolved"}, {"id": "c", "label": "Closed"}],
                                        "edges": [{"from": "o", "to": "a"}, {"from": "a", "to": "i"}, {"from": "i", "to": "r"}, {"from": "r", "to": "c", "label": "verified"}, {"from": "r", "to": "i", "label": "rejected"}]}]})
            elif n == 3:
                out.append({"n": 3, "kind": "content", "title": "Three roles share clear responsibilities", "kicker": "Roles", "visual_plan": "cards", "notes": "Roles.",
                            "blocks": [{"type": "cards", "items": [{"title": "Staff", "body": "Report faults and verify fixes."}, {"title": "Technician", "body": "Repair and mark resolved."}, {"title": "Admin", "body": "Assign tickets."}]}]})
            else:
                out.append({"n": 4, "kind": "content", "title": "Staff confirmation is what closes a ticket", "kicker": "Next", "visual_plan": "none", "notes": "Close.",
                            "blocks": [{"type": "callout", "text": "A ticket closes only after staff verify the fix."}]})
        return {"slides": out}
    raise AssertionError("unexpected prompt: " + prompt[:80])


@pytest.fixture
def scripted(monkeypatch):
    monkeypatch.setattr(gemini, "generate_json", fake_json)
    from services.deck import visuals
    monkeypatch.setattr(visuals, "pick_image", lambda *a, **k: None)


def run_job(app, c, h, **over):
    import time
    r = c.post("/api/presentation/create", json={**GOOD, "topic": TOPIC, "slide_count": 4, "use_web_research": False, **over}, headers=h)
    assert r.status_code == 202
    jid = r.get_json()["data"]["job_id"]
    for _ in range(50):
        st = c.get(f"/api/presentation/status?job_id={jid}", headers=h).get_json()["data"]
        if st["status"] in ("done", "failed"):
            return st
        time.sleep(0.1)
    return st


def test_job_builds_deck_from_fact_sheet(app, scripted):
    with app.test_client() as c:
        h = login(c)
        st = run_job(app, c, h)
        assert st["status"] == "done", st
        assert [e["tool"] for e in st["log"] if e["status"] == "success"][:4] == ["search_knowledge_base", "fact_sheet", "storyline", "slide_specs"]
        det = c.get(f"/api/presentation/{st['result']['presentation_id']}", headers=h).get_json()["data"]
        assert det["settings"]["pipeline"] == "composed-v1" and len(det["settings"]["facts"]) == 5
        assert det["slides"][0]["scene"]["kind"] == "title"
        assert all(s["scene"] and s["scene"]["items"] for s in det["slides"])
        # a real lifecycle diagram with named states, not a bullet list
        types = {p["k"] for p in det["slides"][1]["scene"]["items"]}
        assert "line" in types
        texts = " ".join(p.get("text", "") for p in det["slides"][1]["scene"]["items"] if p["k"] == "text")
        assert "In progress" in texts and "Resolved" in texts and "rejected" in texts
        assert "purpose" not in str(det["slides"][0]["content"].get("spec"))


def test_pipeline_failure_is_reported_safely(app, monkeypatch):
    def boom(*a, **k):
        raise gemini.GeminiError("Could not reach the AI service.")
    monkeypatch.setattr(gemini, "generate_json", boom)
    with app.test_client() as c:
        h = login(c)
        st = run_job(app, c, h)
        assert st["status"] == "failed" and st["error"] == "Could not reach the AI service." and st["result"] is None


def test_validators_reject_invented_numbers_and_filler():
    facts = FACTS
    ok = {"kind": "content", "title": "Three roles share clear responsibilities", "blocks": [{"type": "cards", "items": [{"title": "Staff", "body": "Report"}, {"title": "Admin", "body": "Assign"}]}]}
    assert validators.validate_slide(ok, facts, TOPIC) == []
    bad = {"kind": "content", "title": "Throughput improves dramatically for everyone", "blocks": [{"type": "stat_row", "items": [
        {"value": "10x", "label": "Acceleration"}, {"value": "99.4%", "label": "Precision"}]}]}
    errs = " ".join(validators.validate_slide(bad, facts, TOPIC))
    assert "not found in the fact sheet" in errs and "filler" in errs
    phase = {"kind": "content", "title": "The rollout has distinct stages ahead", "blocks": [{"type": "cards", "items": [{"title": "Phase 1", "body": "x"}, {"title": "Phase 2", "body": "y"}]}]}
    assert "auto-generated label" in " ".join(validators.validate_slide(phase, facts, TOPIC))
    planning = {"kind": "content", "title": "Explains the workflow of tickets", "blocks": [{"type": "callout", "text": "Slide goal: explain"}]}
    assert "planning" in " ".join(validators.validate_slide(planning, facts, TOPIC))


def test_blocks_without_required_data_are_dropped_not_filled():
    assert normalize_block({"type": "stat_row", "items": [{"value": "5"}]}) is None
    assert normalize_block({"type": "chart", "labels": ["a", "b"], "series": [{"values": [1]}]}) is None
    assert normalize_block({"type": "diagram", "nodes": [{"label": "only one"}]}) is None
    assert normalize_block({"type": "timeline", "items": [{"title": "x"}]}) is None


SPEC = [
    {"kind": "title", "title": "A deck about lifecycle tickets", "tagline": "Short line", "blocks": []},
    {"kind": "content", "title": "Every fault follows one tracked path", "kicker": "Flow", "blocks": [
        {"type": "diagram", "nodes": [{"id": "a", "label": "Open"}, {"id": "b", "label": "Closed"}], "edges": [{"from": "a", "to": "b"}]},
        {"type": "callout", "text": "Staff confirm the fix."}]},
    {"kind": "content", "title": "Pilot results by weekday are clear", "blocks": [
        {"type": "chart", "kind": "bar", "labels": ["Mon", "Tue", "Wed"], "series": [{"name": "h", "values": [9, 7, 6]}]},
        {"type": "stat_row", "items": [{"value": "6h", "label": "Best"}, {"value": "9h", "label": "Worst"}]}]},
    {"kind": "content", "title": "Rollout happens in four dated steps", "blocks": [
        {"type": "timeline", "items": [{"when": "W1", "title": "Pilot"}, {"when": "W3", "title": "Fixes"}, {"when": "W6", "title": "All labs"}]}]},
]


def test_every_design_system_has_composition_rules_and_they_differ():
    assert set(DESIGN_SYSTEMS) <= set(COMP), "every design system needs composition tokens"
    sigs = {}
    for name in DESIGN_SYSTEMS:
        sc = build_scene(SPEC[1], name, 1, 4, "Deck")
        radius = {round(p.get("r", 0), 2) for p in sc["items"] if p["k"] == "rect" and p.get("r") is not None}
        sigs[name] = (COMP[name].title_place, COMP[name].card_style, COMP[name].image_style, max(radius), sc["transition"])
    assert len(set(sigs.values())) >= 10, sigs  # structurally different, not just recoloured
    assert len({v[0] for v in sigs.values()}) >= 3  # several title placements in use


def test_text_never_below_minimum_sizes():
    for name in DESIGN_SYSTEMS:
        for i, sp in enumerate(SPEC):
            sc = build_scene(sp, name, i, 4, "Deck")
            for p in sc["items"]:
                if p["k"] == "text" and not re.fullmatch(r"[\d/ ]+|[“]|\d+", p["text"].strip()):
                    assert p["size"] >= 12, (name, p["text"], p["size"])


def test_exports_are_native_and_animated(app, scripted):
    with app.test_client() as c:
        h = login(c)
        st = run_job(app, c, h)
        pid = st["result"]["presentation_id"]
        r = c.get(f"/api/presentation/{pid}/download?format=pptx", headers=h) if False else None
    with app.app_context():
        from services import exporter
        p = db.session.get(Presentation, pid)
        data = exporter.export_pptx(p)
        prs = Pptx(io.BytesIO(data))
        assert len(prs.slides) == 4
        xml = prs.slides[1]._element.xml
        assert "<p:transition" in xml and "<p:timing" in xml and 'filter="' in xml
        assert prs.slides[1].notes_slide.notes_text_frame.text
        pdf = exporter.export_pdf(p)
        assert pdf.startswith(b"%PDF") and len(pdf) > 3000


def test_chart_is_a_native_powerpoint_chart():
    from services.deck.render_pptx import scenes_to_pptx
    scenes = [build_scene(SPEC[2], "swiss_minimal", 2, 4, "Deck")]
    prs = Pptx(io.BytesIO(scenes_to_pptx(scenes, "t")))
    assert any(getattr(sh, "has_chart", False) and sh.has_chart for sh in prs.slides[0].shapes)


def test_body_text_at_least_18pt_in_exported_files():
    from services.deck.render_pptx import scenes_to_pptx
    scenes = [build_scene(sp, "swiss_minimal", i, 4, "Deck") for i, sp in enumerate(SPEC)]
    prs = Pptx(io.BytesIO(scenes_to_pptx(scenes, "t")))

    def walk(shapes):
        for sh in shapes:
            if sh.shape_type == 6:
                yield from walk(sh.shapes)
            else:
                yield sh
    for s in prs.slides:
        for sh in walk(s.shapes):
            if sh.has_text_frame and sh.text_frame.text.strip():
                for para in sh.text_frame.paragraphs:
                    for r in para.runs:
                        if len(r.text) > 60:  # long running text is body copy
                            assert r.font.size >= Pt(18), r.text


def test_regenerate_composed_slide_keeps_validation(app, scripted, monkeypatch):
    with app.test_client() as c:
        h = login(c)
        pid = run_job(app, c, h)["result"]["presentation_id"]
        good = {"slides": [{"n": 3, "kind": "content", "title": "Three roles share clear responsibilities", "kicker": "Roles", "visual_plan": "cards", "notes": "n",
                            "blocks": [{"type": "steps", "items": [{"title": "Staff reports", "body": "Opens a ticket."}, {"title": "Admin assigns", "body": "Picks a technician."}]}]}]}
        monkeypatch.setattr(gemini, "generate_json", lambda *a, **k: good)
        r = c.post(f"/api/presentation/{pid}/slide/3/regenerate", json={"instructions": "show as steps"}, headers=h)
        assert r.status_code == 200 and r.get_json()["data"]["slide"]["content"]["spec"]["blocks"][0]["type"] == "steps"
        bad = {"slides": [{"n": 3, "kind": "content", "title": "Speed improves by a wide margin overall", "blocks": [{"type": "stat_row", "items": [
            {"value": "10x", "label": "Faster"}, {"value": "99.4%", "label": "Precise"}]}]}]}
        monkeypatch.setattr(gemini, "generate_json", lambda *a, **k: bad)
        r = c.post(f"/api/presentation/{pid}/slide/3/regenerate", json={"instructions": "add stats"}, headers=h)
        assert r.status_code == 422  # invented numbers are refused; the slide stays as it was
        det = c.get(f"/api/presentation/{pid}", headers=h).get_json()["data"]
        assert det["slides"][2]["content"]["spec"]["blocks"][0]["type"] == "steps"


def test_chat_tool_edit_existing_slide_updates_composed_spec(app, scripted):
    """Verify that editing slide title or bullets via draft tools synchronizes the composed spec."""
    with app.test_client() as c:
        h = login(c)
        pid = run_job(app, c, h)["result"]["presentation_id"]
        with app.app_context():
            from tools import draft
            from agents.registry import ToolContext
            from models import Presentation
            p = Presentation.query.get(pid)
            ctx = ToolContext(user_id=p.user_id)
            draft.edit_existing_slide(ctx, {
                "presentation_id": pid,
                "slide_number": 3,
                "title": "Updated Title for Slide 3",
                "bullets": ["Brand new verified bullet point A", "Brand new verified bullet point B"]
            })
            slide_3 = next(s for s in p.slides if s.position == 3)
            assert slide_3.title == "Updated Title for Slide 3"
            assert slide_3.content["spec"]["title"] == "Updated Title for Slide 3"
            bullet_block = next((b for b in slide_3.content["spec"]["blocks"] if b["type"] == "bullets"), None)
            assert bullet_block is not None
            assert "Brand new verified bullet point A" in bullet_block["items"]
