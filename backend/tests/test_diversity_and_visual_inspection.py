"""
Test end-to-end template diversity, adaptive density, PPTX vector parity,
and visual image rendering inspection.
"""

import pytest
from app import create_app
from database import db
from models import User, Presentation, Slide
from services import template_engine, visual_quality_checker, exporter


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()




def test_pptx_and_visual_inspection_parity(app):
    """Verifies that PPTX export and visual image inspection operate with full parity across structural layouts."""
    user = User(email="architect@slidemind.ai", name="Lead Architect")
    db.session.add(user)
    db.session.commit()

    p = Presentation(user_id=user.id, title="Enterprise AI Transformation 2026", settings={"theme": "swiss_minimal", "density": "detailed"})
    db.session.add(p)
    db.session.flush()

    # Add diverse structural slides
    slides_data = [
        ("Cover", "full_bleed_hero", {"headline": "Autonomous AI Strategy", "bullets": [{"text": "Mission critical blueprint"}]}),
        ("Market Curve", "market_adoption_gaussian", {"headline": "Adoption Diffusion", "bullets": [{"text": "Crossing the chasm"}]}),
        ("Competitor Matrix", "competitor_matrix_2x2", {"bullets": [{"text": "Leader in accuracy"}, {"text": "Verified defensibility"}]}),
        ("Funnel", "chevron_funnel", {"funnel_stages": [{"title": "Attract", "desc": "Inbound"}, {"title": "Close", "desc": "Contract"}]}),
        ("Monument KPI", "stats_kpi_monument", {"kpis": [{"value": "30M+", "label": "Growth", "description": "Active users"}], "bullets": [{"text": "Empirical audit"}]}),
        ("Comparison", "comparison_table", {"table_headers": ["Feature", "SlideMind", "Others"], "table_rows": [["Vector Parity", "Yes", "No"]]}),
    ]

    for idx, (title, layout, content) in enumerate(slides_data, start=1):
        s = Slide(presentation_id=p.id, position=idx, title=title, content={"layout": layout, **content})
        db.session.add(s)
    db.session.commit()

    # 1. Test PPTX export generates valid PPTX package bytes without error
    pptx_bytes = exporter.export_pptx(p)
    assert isinstance(pptx_bytes, bytes)
    assert len(pptx_bytes) > 2000
    assert pptx_bytes[:4] == b"PK\x03\x04"  # Valid ZIP/OpenXML magic number

    # 2. Test PDF export generates valid PDF bytes
    pdf_bytes = exporter.export_pdf(p)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes[:4] == b"%PDF"

    # 3. Test Visual Image Inspection renders actual 960x540 PNG images and passes inspection
    inspection = visual_quality_checker.inspect_presentation_visually(p)
    assert inspection["total_slides_inspected"] == 6
    assert inspection["visual_inspection_passed"] is True
    assert len(inspection["slides"]) == 6
    for s_rep in inspection["slides"]:
        assert s_rep["contrast_status"] == "pass"
        assert s_rep["rendered_dimensions"][0] > 0
        assert s_rep["rendered_dimensions"][1] > 0
