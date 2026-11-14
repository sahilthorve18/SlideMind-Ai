import os

os.environ["SLIDEMIND_SKIP_AUTOAPP"] = "1"

import pytest
from app import create_app
from database import db
from models import Presentation, Slide, User
from services import exporter, slides, visual_intelligence


@pytest.fixture
def client_and_app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "RATELIMIT_ENABLED": False,
        "DEV_LOGIN_ENABLED": True,
        "GEMINI_API_KEY": "",
    })
    with app.app_context():
        db.create_all()
        user = User(email="test.visuals@slidemind.ai", name="Visual Tester")
        db.session.add(user)
        db.session.commit()
        yield app.test_client(), app, user
        db.session.remove()
        db.drop_all()


def test_indias_ai_revolution_presentation_10_slides(client_and_app):
    """Test generating a complete 10-slide presentation on 'India's AI Revolution'
    and verifying automatic image selection, placement, and export synchronization.
    """
    client, app, user = client_and_app
    with app.app_context():
        # 1. Create a 10-slide presentation with varied topic requirements
        p = Presentation(
            user_id=user.id,
            title="India's AI Revolution",
            settings={"theme": "futuristic_ai", "audience": "technical_professionals"},
            status="draft",
        )
        db.session.add(p)
        db.session.flush()

        slide_definitions = [
            ("India's AI Revolution: The Dawn of Sovereign Intelligence", "Executive vision of India's rapid AI emergence", [
                "Transforming from a global IT services hub to an indigenous AI superpower",
                "National AI Mission mobilizing compute, multilingual data, and innovation ecosystems",
                "Leveraging the world's largest digital public infrastructure to democratize intelligence"
            ]),
            ("Digital Public Infrastructure: The Foundation of Scale", "How Aadhaar, UPI, and India Stack empower AI", [
                "Over 1.4 billion citizens connected through open identity and digital payment protocols",
                "Unified open architectures enabling massive, high-velocity population-scale data collection",
                "Decentralized foundational rails reducing transaction costs to near zero"
            ]),
            ("Compute Sovereignty & Semiconductor Ecosystem", "National GPU clusters and domestic silicon fabrication", [
                "India AI Compute Capacity initiative deploying 10,000+ cutting-edge enterprise GPUs",
                "Subsidized high-performance compute fabrics for startups and deep tech researchers",
                "Establishing commercial semiconductor fabrication facilities in Gujarat and Assam"
            ]),
            ("Multilingual Foundational Models & Bhashini", "Bridging language barriers across 22 official languages", [
                "Project Bhashini creating open-source voice, translation, and text datasets",
                "Overcoming linguistic diversity through speech-first and local vernacular LLMs",
                "Empowering non-English speaking demographics with conversational AI interfaces"
            ]),
            ("Agritech & Climate Resilience", "Precision farming and predictive yield intelligence", [
                "Computer vision and satellite telemetry guiding hyper-local soil and pest management",
                "Real-time market price discovery and crop insurance assessment via AI mobile models",
                "Empowering 100M+ smallholder farmers with vernacular conversational advisories"
            ]),
            ("Healthcare Transformation at Population Scale", "Accessible diagnosis and rural health delivery", [
                "AI-assisted radiology screening for tuberculosis and diabetic retinopathy in primary centers",
                "Ayushman Bharat Digital Mission integrating unified electronic health records",
                "Decentralized triage platforms expanding specialist coverage to Tier-2 and Tier-3 cities"
            ]),
            ("Economic Impact & Investment Scale", "Projected GDP contributions and venture funding growth", [
                "AI poised to add $967 billion to the Indian economy by 2035",
                "Generative AI investments growing at an exponential 68% CAGR across enterprise sectors",
                "Over 1,200 active AI startups driving breakthrough indigenous enterprise solutions"
            ]),
            ("National AI Implementation Roadmap", "Multi-phase deployment milestones from 2024 to 2030", [
                "Phase 1: Compute procurement and public dataset curation (2024-2025)",
                "Phase 2: Sectoral deployment across health, agriculture, and civic governance (2026-2027)",
                "Phase 3: Global export of sovereign AI models and frugal engineering solutions (2028-2030)"
            ]),
            ("Ethical Governance & Responsible AI Frameworks", "Ensuring fairness, privacy, and systemic safety", [
                "Aligning with Global Partnership on Artificial Intelligence (GPAI) principles",
                "Digital Personal Data Protection (DPDP) Act safeguarding citizen privacy",
                "Mitigating algorithmic bias in demographic credit, healthcare, and public welfare delivery"
            ]),
            ("The Future Horizon: India's Global Leadership", "Conclusion and forward strategic synthesis", [
                "Frugal, accessible, and inclusive AI engineering setting a benchmark for the Global South",
                "Unlocking unprecedented productivity across manufacturing, education, and services",
                "Shaping the next decade of ethical, democratized human-centric artificial intelligence"
            ]),
        ]

        for i, (title, purpose, bullets) in enumerate(slide_definitions, start=1):
            s = Slide(
                presentation_id=p.id,
                position=i,
                title=title,
                content={
                    "purpose": purpose,
                    "bullets": [{"text": b, "source_ids": []} for b in bullets],
                },
            )
            db.session.add(s)

        db.session.commit()
        db.session.refresh(p)

        # 2. Run the Autonomous Visual Engine
        enriched_count = visual_intelligence.auto_populate_presentation_visuals(p)
        assert enriched_count > 0, "Autonomous engine should enrich slides"
        db.session.refresh(p)

        # 3. Verify EVERY slide: No empty placeholders, correct layouts, valid images
        slides_list = sorted(p.slides, key=lambda s: s.position)
        assert len(slides_list) == 10

        used_image_urls = []
        for idx, s in enumerate(slides_list):
            c = s.content or {}
            layout = c.get("layout")
            assert layout is not None, f"Slide {s.position} must have a defined layout"
            assert layout != "title_bullets", f"Slide {s.position} should be elevated from plain title_bullets"

            # Check cover slide
            if idx == 0:
                assert layout == "full_bleed_hero", "Cover slide must be full_bleed_hero"
                img = c.get("image")
                assert img is not None and isinstance(img, dict), "Cover slide must have an image"
                assert img.get("url"), "Cover slide image must have a valid URL"
                used_image_urls.append(img["url"])

            # Check conclusion slide
            elif idx == 9:
                assert layout in ("conclusion_cta", "quote_testimonial", "split_screen")
                img = c.get("image")
                if img:
                    assert img.get("url")
                    used_image_urls.append(img["url"])

            # Check inner slides
            else:
                if layout in ("split_screen", "image_gallery"):
                    img = c.get("image")
                    assert img is not None, f"Slide {s.position} ({layout}) must have an image"
                    assert img.get("url"), f"Slide {s.position} image must have a valid URL"
                    assert not img["url"].startswith("None"), "Image URL must not be None"
                    used_image_urls.append(img["url"])
                elif layout == "stats_kpi":
                    kpis = c.get("kpis")
                    assert kpis and len(kpis) >= 2, f"Slide {s.position} must have populated KPI cards"
                elif layout == "process_diagram":
                    steps = c.get("process_steps")
                    assert steps and len(steps) >= 2, f"Slide {s.position} must have populated process steps"
                elif layout in ("problem_solution", "comparison_table"):
                    assert c.get("problem") or c.get("comparison"), f"Slide {s.position} must have comparison data"

        # Check deduplication: all images used across the presentation should be unique!
        assert len(used_image_urls) == len(set(used_image_urls)), "All images must be distinct (no duplicates)"

        # 4. Synchronize Output: Verify PPTX Export
        pptx_bytes = exporter.export_pptx(p)
        assert len(pptx_bytes) > 20000, "PPTX must be a substantive valid binary presentation"
        # Verify PPTX is a valid zip package with PowerPoint structure
        import zipfile
        import io
        with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as z:
            assert "[Content_Types].xml" in z.namelist()
            assert "ppt/presentation.xml" in z.namelist()
            # Verify media files or slide definitions exist
            slide_xmls = [n for n in z.namelist() if n.startswith("ppt/slides/slide")]
            assert len(slide_xmls) == 10, "PPTX must contain all 10 slides"

        # 5. Synchronize Output: Verify PDF Export
        pdf_bytes = exporter.export_pdf(p)
        assert len(pdf_bytes) > 10000, "PDF must be a substantive valid binary file"
        assert pdf_bytes.startswith(b"%PDF"), "PDF export must start with %PDF magic header"

        # 6. Synchronize Output: Verify Google Slides Requests
        draft_dict = {
            "title": p.title,
            "theme": (p.settings or {}).get("theme", "futuristic_ai"),
            "slides": [
                {
                    "title": s.title,
                    "bullets": [b.get("text", "") for b in (s.content or {}).get("bullets", [])],
                    "layout": (s.content or {}).get("layout"),
                    "image": (s.content or {}).get("image"),
                    "content": s.content,
                }
                for s in slides_list
            ],
        }
        for idx, s_dict in enumerate(draft_dict["slides"]):
            reqs, _, _ = slides.slide_requests(idx, s_dict, draft_dict["theme"])
            # If the slide had an image, verify createImage request is present
            if s_dict.get("image") and s_dict["image"].get("url"):
                create_img_reqs = [r for r in reqs if "createImage" in r]
                assert len(create_img_reqs) == 1, f"Slide {idx + 1} must generate a createImage request for Google Slides"
                c_img = create_img_reqs[0]["createImage"]
                assert c_img["url"] == s_dict["image"]["url"]
                assert c_img["elementProperties"]["size"]["width"]["unit"] == "EMU"
                assert c_img["elementProperties"]["size"]["height"]["unit"] == "EMU"
