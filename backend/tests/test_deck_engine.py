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


def test_chat_tool_chart_and_diagram_edits_update_composed_spec(app, scripted, monkeypatch):
    """Verify that generate_diagram and generate_chart update the slide's composed spec."""
    with app.test_client() as c:
        h = login(c)
        pid = run_job(app, c, h)["result"]["presentation_id"]
        with app.app_context():
            from tools import draft
            from agents.registry import ToolContext
            p = db.session.get(Presentation, pid)
            ctx = ToolContext(user_id=p.user_id)

            # 1. Diagram edit updates composed spec blocks
            monkeypatch.setattr(
                gemini,
                "generate_json",
                lambda *a, **k: {
                    "nodes": [{"id": "n1", "label": "Intake"}, {"id": "n2", "label": "Repair"}],
                    "edges": [{"from": "n1", "to": "n2", "label": "assign"}],
                },
            )
            diag_res = draft.generate_diagram(ctx, {"presentation_id": pid, "slide_number": 3, "description": "Intake to repair flow"})
            assert diag_res["nodes"] == 2
            s3 = next(s for s in p.slides if s.position == 3)
            assert s3.content["layout"] == "diagram"
            diag_block = next((b for b in s3.content["spec"]["blocks"] if b["type"] == "diagram"), None)
            assert diag_block is not None
            assert [n["label"] for n in diag_block["nodes"]] == ["Intake", "Repair"]

            # 2. Chart edit updates composed spec blocks
            chart_res = draft.generate_chart(
                ctx,
                {
                    "presentation_id": pid,
                    "slide_number": 3,
                    "chart_type": "bar",
                    "title": "Tickets by Role",
                    "labels": ["Staff", "Tech", "Admin"],
                    "values": [12, 8, 3],
                    "source_ref": 1,
                },
            )
            assert chart_res["points"] == 3
            s3 = next(s for s in p.slides if s.position == 3)
            assert s3.content["layout"] == "chart"
            chart_block = next((b for b in s3.content["spec"]["blocks"] if b["type"] == "chart"), None)
            assert chart_block is not None
            assert chart_block["kind"] == "bar"
            assert chart_block["series"][0]["values"] == [12, 8, 3]


def test_critique_repair_parallel_scoring_and_validator_guard(app, scripted, monkeypatch):
    """Render-and-critique repairs scores < 75, ignores errored checks in pass counts, saves scores, and refuses invented numbers."""
    from services import visual_quality_checker, intelligence

    with app.test_client() as c:
        h = login(c)
        pid = run_job(app, c, h)["result"]["presentation_id"]

    with app.app_context():
        p = db.session.get(Presentation, pid)
        original_s3_title = next(s for s in p.slides if s.position == 3).title

        def mock_critique(image_bytes, slide_title, topic):
            if "path" in slide_title.lower():
                return {"score": 88, "passed": True, "status": "ok", "problems": [], "fix_instruction": ""}
            if "responsibilities" in slide_title.lower():
                return {
                    "score": 68,
                    "passed": False,
                    "status": "ok",
                    "problems": ["Tight bottom spacing"],
                    "fix_instruction": "Simplify card layout",
                }
            # Simulate transient error on remaining slides -> must NOT fake score=85/passed
            return {"score": None, "passed": None, "status": "error", "problems": [], "fix_instruction": ""}

        monkeypatch.setattr(visual_quality_checker, "critique_slide_with_vision", mock_critique)

        # Case A: Repair attempt produces invented number -> validator rejects it and keeps slide unchanged
        bad_spec = {
            "slides": [{
                "n": 3,
                "kind": "content",
                "title": "Three roles share 99.4% accuracy across labs",
                "blocks": [{"type": "stat_row", "items": [{"value": "99.4%", "label": "Uptime"}, {"value": "10x", "label": "Speed"}]}],
            }]
        }
        monkeypatch.setattr(gemini, "generate_json", lambda *a, **k: bad_spec)
        repairs = visual_quality_checker.run_render_and_critique_repair(p, TOPIC, max_repairs=2)
        assert repairs == []
        s3 = next(s for s in p.slides if s.position == 3)
        assert s3.title == original_s3_title  # unchanged!

        vc = (p.settings or {}).get("visual_critique")
        assert vc is not None
        assert vc["evaluated_slides"] == 2
        assert vc["passed_slides"] == 1
        assert vc["failed_evaluations"] >= 1
        assert vc["average_score"] == 78.0  # (88 + 68) / 2, excluding errors

        # Intelligence report surfaces saved critique and unresolved < 75 warning
        intel = intelligence.analyze_presentation(p)
        assert intel["visual_critique"]["average_score"] == 78.0
        assert any(iss.get("type") == "visual_critique" and iss.get("slide") == 3 for iss in intel["issues"])

        # Case B: Valid repair within fact sheet succeeds and updates saved critique
        good_spec = {
            "slides": [{
                "n": 3,
                "kind": "content",
                "title": "Three roles coordinate every lab repair step",
                "kicker": "Roles",
                "visual_plan": "cards",
                "notes": "Three roles.",
                "blocks": [{"type": "steps", "items": [{"title": "Staff reports", "body": "Opens a ticket."}, {"title": "Admin assigns", "body": "Picks a technician."}]}],
            }]
        }
        monkeypatch.setattr(gemini, "generate_json", lambda *a, **k: good_spec)
        repairs_ok = visual_quality_checker.run_render_and_critique_repair(p, TOPIC, max_repairs=2)
        assert len(repairs_ok) == 1
        s3_after = next(s for s in p.slides if s.position == 3)
        assert s3_after.title == "Three roles coordinate every lab repair step"
        assert p.settings["visual_critique"]["repaired_slides"] == [3]


def test_filter_grounded_facts_expands_suffixes_and_keeps_general():
    """Value-based matching handles 2.5M == 2.5 million, $10bn == $10B, $5mn/$5mm == 5M, $1.2k == $1,200,
    30% == 30 percent, ties passage ids strictly to their own text, blocks general doc-spoofed metrics, and caps unverified general numeric facts."""
    passages = [
        {"id": "P1", "text": "The platform reached 2.5 million users while costs fell 30 percent on a $1,200 budget."},
        {"id": "P2", "text": "Valuation grew to $10bn after a $5mn bridge round and $4mm grant."},
    ]
    candidate_facts = [
        {"id": "F1", "claim": "Served 2.5M users globally.", "number": "2.5M", "source": "P1", "kind": "metric"},
        {"id": "F2", "claim": "Costs fell 30% year over year.", "number": "30%", "source": "P1", "kind": "metric"},
        {"id": "F3", "claim": "Initial budget was $1.2k total.", "number": "$1.2k", "source": "P1", "kind": "metric"},
        {"id": "F4", "claim": "Valuation hit $10B after a $5M bridge and $4M grant.", "number": "$10B", "source": "P2", "kind": "metric"},
        {"id": "F5", "claim": "Revenue reached 99M last quarter.", "number": "99M", "source": "P1", "kind": "metric"},
        {"id": "F6", "claim": "Cross-passage citation claiming 2.5M from P2 instead of P1.", "number": "2.5M", "source": "P2", "kind": "metric"},
        {"id": "F7", "claim": "Revenue is $99M, per the document.", "number": "$99M", "source": "general", "kind": "metric"},
        {"id": "F8", "claim": "Light travels at 299,792 km/s in vacuum.", "number": "299,792", "source": "general", "kind": "fact"},
        {"id": "F9", "claim": "Earth orbits the Sun at 107,000 km/h.", "number": "107,000", "source": "general", "kind": "fact"},
        {"id": "F10", "claim": "Sound travels at 343 m/s in dry air.", "number": "343", "source": "general", "kind": "fact"},  # 3rd general numeric -> capped at 2
    ]
    kept = validators.filter_grounded_facts(candidate_facts, "Platform growth", passages, "")
    kept_ids = [f["id"] for f in kept]
    assert kept_ids == ["F1", "F2", "F3", "F4", "F8", "F9"]
    assert kept[-1].get("unverified") is True
    assert kept[0].get("unverified") is None

    # Validate slide using normalized form against passage-worded fact
    passage_facts = [{"id": "F1", "claim": "Reached 2.5 million users; costs fell 30 percent on $1,200.", "number": None, "source": "P1", "kind": "metric"}]
    slide = {
        "kind": "content",
        "title": "Platform scales efficiently on lean budget",
        "blocks": [{"type": "stat_row", "items": [
            {"value": "2.5M", "label": "Users"},
            {"value": "30%", "label": "Cost reduction"},
            {"value": "$1.2k", "label": "Budget"},
        ]}],
    }
    assert validators.validate_slide(slide, passage_facts, "Platform growth") == []


def test_google_slides_renders_full_composed_scenes_including_diagrams_charts_and_sync(app, scripted, monkeypatch):
    """Publishing and syncing composed decks must use positioned scene primitives (diagrams, charts, cards, images), not plain bullet placeholders."""
    from services import google_auth, slides
    from services.deck import render_gslides
    from agents.registry import ToolContext
    from models import User
    from tests.test_phase5 import FakeDrive, FakeSlidesAPI, KEY
    from types import SimpleNamespace

    # 1. Direct primitive verification (rect, ellipse, line, text, image, bar/line/pie charts)
    test_scene = {
        "bg": "0f172a",
        "items": [
            {"k": "rect", "x": 1.0, "y": 1.0, "w": 4.0, "h": 2.0, "fill": "1e293b", "line": "38bdf8", "lw": 2.0, "r": 0.1, "alpha": 0.9},
            {"k": "ellipse", "x": 6.0, "y": 1.0, "w": 1.0, "h": 1.0, "fill": "38bdf8"},
            {"k": "line", "x1": 1.0, "y1": 3.5, "x2": 5.0, "y2": 3.5, "color": "f59e0b", "lw": 2.0, "dash": True, "arrow": True},
            {"k": "text", "x": 1.2, "y": 1.2, "w": 3.6, "h": 0.8, "text": "Hello Scene", "size": 24, "color": "ffffff", "bold": True, "align": "c", "valign": "m", "font": "Calibri"},
            {"k": "image", "x": 8.0, "y": 1.0, "w": 4.0, "h": 3.0, "src": {"url": "https://upload.wikimedia.org/solar.jpg"}},
            {"k": "image", "x": 8.0, "y": 4.2, "w": 2.0, "h": 1.5, "src": {"url": "/api/assets/a1/view?token=abc"}},
            {"k": "chart", "x": 1.0, "y": 4.0, "w": 6.0, "h": 2.8, "kind": "bar", "labels": ["Q1", "Q2"], "series": [{"name": "S", "values": [10, 25]}], "colors": ["38bdf8"], "fg": "ffffff", "grid": "334155"},
        ],
    }
    reqs, ids, nr = render_gslides.deck_requests([test_scene], backend_url="https://api.example.com")
    assert len(ids) == 1
    assert nr == []
    assert any(r.get("createSlide", {}).get("slideLayoutReference", {}).get("predefinedLayout") == "BLANK" for r in reqs)
    created_imgs = [r["createImage"]["url"] for r in reqs if "createImage" in r]
    assert "https://upload.wikimedia.org/solar.jpg" in created_imgs
    assert "https://api.example.com/api/assets/a1/view?token=abc" in created_imgs
    assert any("createLine" in r for r in reqs)
    assert any(r.get("insertText", {}).get("text") == "Hello Scene" for r in reqs)
    assert any(r.get("insertText", {}).get("text") == "25" for r in reqs)  # bar value label rendered

    # Line & Pie charts also render without errors
    line_pie = [
        {"bg": "ffffff", "items": [{"k": "chart", "x": 1, "y": 1, "w": 5, "h": 3, "kind": "line", "labels": ["A", "B"], "series": [{"name": "S", "values": [5, 15]}], "colors": ["2563eb"], "fg": "0f172a", "grid": "cbd5e1"}]},
        {"bg": "ffffff", "items": [{"k": "chart", "x": 1, "y": 1, "w": 5, "h": 3, "kind": "pie", "labels": ["X", "Y"], "series": [{"name": "S", "values": [40, 60]}], "colors": ["2563eb", "10b981"], "fg": "0f172a", "grid": "cbd5e1"}]},
    ]
    lp_reqs, _, _ = render_gslides.deck_requests(line_pie)
    assert any(r.get("insertText", {}).get("text") == "60 (60%)" for r in lp_reqs)

    # 2. End-to-end composed deck publish + sync uses BLANK scene layout & renders diagrams with zero not_rendered items
    api = FakeSlidesAPI()
    monkeypatch.setattr(slides, "build_services", lambda creds: slides.Services(api, FakeDrive()))
    monkeypatch.setattr(google_auth, "credentials_for", lambda u: SimpleNamespace())
    monkeypatch.setattr(google_auth, "is_connected", lambda u: True)

    with app.test_client() as c:
        h = login(c)
        pid = run_job(app, c, h)["result"]["presentation_id"]

        with app.app_context():
            p = db.session.get(Presentation, pid)
            u = db.session.get(User, p.user_id)
            u.google_refresh_token_enc = "enc"
            u.google_scopes = " ".join(google_auth.SCOPES)
            db.session.commit()

            from agents import registry
            ctx = ToolContext(user_id=u.id, google_connected=True)
            res = registry.execute("create_google_slides", {"presentation_id": pid}, ctx)
            assert res["ok"] is True
            assert "not_rendered" not in res
            assert res["notes_written"] == 4

            # Inspect batchUpdate requests sent to FakeSlidesAPI: diagrams -> createLine with arrows, not TITLE_AND_BODY
            batch_reqs = api.log[1][1]
            assert any(r.get("createLine") for r in batch_reqs)
            assert not any(r.get("createSlide", {}).get("slideLayoutReference", {}).get("predefinedLayout") == "TITLE_AND_BODY" for r in batch_reqs)

        # Sync after edit also emits scene primitives
        sync_r = c.post(
            "/api/presentation/edit",
            headers=h,
            json={"presentation_id": pid, "action": "edit_slide", "slide_position": 3, "title": "Updated Scene Sync Title", "sync": True},
        )
        assert sync_r.status_code == 200
        assert sync_r.get_json()["data"]["google_sync"]["synced"] is True
        last_sync_batch = next(entry[1] for entry in reversed(api.log) if entry[0] == "batch" and any("createSlide" in r for r in entry[1]))
        assert any(r.get("insertText", {}).get("text") == "Updated Scene Sync Title" for r in last_sync_batch)
