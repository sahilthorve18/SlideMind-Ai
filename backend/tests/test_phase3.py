import io
import math
import os

os.environ["SLIDEMIND_SKIP_AUTOAPP"] = "1"

import pytest

from app import create_app
from database import db
from rag import embed
from rag.chunk import chunk_segments
from rag.extract import ExtractionError, Segment, extract
from services import gemini

VOCAB = ["solar", "wind", "battery", "cost", "grid", "policy", "hydrogen", "storage"]


def fake_embed(texts, task_type="RETRIEVAL_DOCUMENT"):
    """Deterministic bag-of-words vectors so retrieval ranking is testable offline."""
    out = []
    for t in texts:
        low = t.lower()
        v = [float(low.count(w)) for w in VOCAB] + [0.01] * (embed.EMBED_DIM - len(VOCAB))
        n = math.sqrt(sum(x * x for x in v))
        out.append([x / n for x in v])
    return out


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(embed, "embed_texts", fake_embed)
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "DEV_LOGIN_ENABLED": True,
                      "RATELIMIT_ENABLED": False, "GEMINI_API_KEY": "test-key"})
    with app.test_client() as c:
        yield c
    with app.app_context():
        db.drop_all()


def login(client, email="a@example.com"):
    r = client.post("/api/auth/dev-login", json={"email": email})
    return {"Authorization": "Bearer " + r.get_json()["data"]["token"]}


def make_pdf():
    import pymupdf
    doc = pymupdf.open()
    p1 = doc.new_page()
    p1.insert_text((72, 80), "Solar Power", fontsize=22)
    p1.insert_text((72, 120), "Solar panels convert sunlight into electricity. Solar cost has fallen sharply.", fontsize=11)
    p2 = doc.new_page()
    p2.insert_text((72, 80), "Storage", fontsize=22)
    p2.insert_text((72, 120), "Battery storage smooths the grid when wind output drops.", fontsize=11)
    return doc.tobytes()


def make_docx():
    import docx
    d = docx.Document()
    d.add_heading("Hydrogen", level=1)
    d.add_paragraph("Hydrogen can be produced with surplus wind power.")
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def make_pptx():
    from pptx import Presentation
    prs = Presentation()
    s = prs.slides.add_slide(prs.slide_layouts[1])
    s.shapes.title.text = "Policy"
    s.placeholders[1].text = "Grid policy shapes solar adoption."
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def upload(client, h, name, data):
    return client.post("/api/upload", headers=h, data={"file": (io.BytesIO(data), name)},
                       content_type="multipart/form-data")


# ---- extraction / chunking ----

def test_extract_pdf_tracks_pages_and_headings():
    ftype, segs, pages = extract("a.pdf", make_pdf())
    assert ftype == "pdf" and pages == 2
    assert {s.page for s in segs} == {1, 2}
    assert any(s.heading == "Solar Power" and s.page == 1 for s in segs)


def test_extract_docx_pptx_txt():
    _, segs, _ = extract("a.docx", make_docx())
    assert segs[0].heading == "Hydrogen"
    _, segs, pages = extract("a.pptx", make_pptx())
    assert pages == 1 and segs[0].page == 1 and segs[0].heading == "Policy"
    _, segs, _ = extract("a.txt", b"plain text here")
    assert segs[0].text == "plain text here"


@pytest.mark.parametrize("name,data", [
    ("a.exe", b"MZ..."), ("a.pdf", b"not a pdf"), ("a.docx", b"PK\x03\x04junk"), ("a.txt", b""), ("a.txt", b"ab\x00cd"),
])
def test_extract_rejects_invalid(name, data):
    with pytest.raises(ExtractionError):
        extract(name, data)


def test_chunking_keeps_metadata_and_size():
    text = "\n\n".join(f"Sentence number {i}. " * 40 for i in range(10))
    chunks = chunk_segments([Segment(text, 3, "Intro")])
    assert len(chunks) > 1
    assert all(c.page == 3 and c.heading == "Intro" for c in chunks)
    assert all(len(c.text) <= 1300 for c in chunks)


# ---- API ----

def test_upload_list_dedupe_delete(client):
    h = login(client)
    pdf = make_pdf()  # same bytes twice; regenerating would change the embedded PDF id
    r = upload(client, h, "energy.pdf", pdf)
    assert r.status_code == 201 and r.get_json()["data"]["page_count"] == 2
    doc_id = r.get_json()["data"]["id"]
    r2 = upload(client, h, "energy-copy.pdf", pdf)
    assert r2.status_code == 200 and r2.get_json()["data"]["duplicate"] is True
    assert len(client.get("/api/documents", headers=h).get_json()["data"]) == 1
    assert client.delete(f"/api/documents/{doc_id}", headers=h).status_code == 200
    assert client.get("/api/documents", headers=h).get_json()["data"] == []


def test_upload_rejects_bad_files(client):
    h = login(client)
    r = upload(client, h, "evil.exe", b"MZ")
    assert r.status_code == 422 and r.get_json()["error"]["code"] == "invalid_file"
    assert client.post("/api/upload", headers=h).status_code == 400


def test_search_ranks_relevant_chunk_and_isolates_users(client):
    ha, hb = login(client), login(client, "b@example.com")
    upload(client, ha, "energy.pdf", make_pdf())
    upload(client, ha, "h2.docx", make_docx())
    res = client.post("/api/rag/search", json={"query": "battery storage grid", "k": 2}, headers=ha).get_json()["data"]["results"]
    assert res[0]["page_number"] == 2 and "Battery" in res[0]["text"]
    assert res[0]["filename"] == "energy.pdf"
    other = client.post("/api/rag/search", json={"query": "battery storage grid"}, headers=hb).get_json()["data"]["results"]
    assert other == []
    doc_id = client.get("/api/documents", headers=ha).get_json()["data"][0]["id"]
    assert client.delete(f"/api/documents/{doc_id}", headers=hb).status_code == 404


def test_search_validation(client):
    h = login(client)
    assert client.post("/api/rag/search", json={"query": "  "}, headers=h).status_code == 400
    assert client.post("/api/rag/search", json={"query": "x", "k": 99}, headers=h).status_code == 400


def test_embedding_failure_saves_nothing(client, monkeypatch):
    def boom(texts, task_type="RETRIEVAL_DOCUMENT"):
        raise embed.EmbeddingError("The embedding service returned an error.")
    monkeypatch.setattr(embed, "embed_texts", boom)
    h = login(client)
    r = upload(client, h, "energy.pdf", make_pdf())
    assert r.status_code == 502
    assert client.get("/api/documents", headers=h).get_json()["data"] == []
