from flask import Blueprint, g, request

from database import db
from models import Document
from rag import store
from rag.embed import EmbeddingError
from rag.extract import ExtractionError
from services.gemini import GeminiNotConfigured
from utils.http import fail, json_body, ok, require_auth

bp = Blueprint("documents", __name__, url_prefix="/api")


def _doc_dict(d: Document):
    return {
        "id": d.id,
        "filename": d.filename,
        "file_type": d.file_type,
        "size_bytes": d.size_bytes,
        "page_count": d.page_count,
        "status": d.status,
        "created_at": d.created_at.isoformat(),
    }


@bp.post("/upload")
@require_auth
def upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return fail("invalid_request", "Attach a file in the 'file' field.")
    data = f.read()
    try:
        doc, duplicate = store.index_document(g.user.id, f.filename, data)
    except ExtractionError as e:
        return fail("invalid_file", str(e), 422)
    except store.DocumentTooLarge as e:
        return fail("document_too_large", str(e), 413)
    except GeminiNotConfigured:
        return fail("ai_not_configured", "Document indexing needs GEMINI_API_KEY, which is not set on this server.", 503)
    except EmbeddingError as e:
        db.session.rollback()
        return fail("ai_unavailable", f"{e} Nothing was saved; please try again.", 502)
    return ok({**_doc_dict(doc), "duplicate": duplicate}, 200 if duplicate else 201)


@bp.get("/documents")
@require_auth
def list_documents():
    docs = Document.query.filter_by(user_id=g.user.id).order_by(Document.created_at.desc()).all()
    return ok([_doc_dict(d) for d in docs])


@bp.delete("/documents/<doc_id>")
@require_auth
def delete_document(doc_id):
    d = Document.query.filter_by(id=doc_id, user_id=g.user.id).first()
    if not d:
        return fail("not_found", "Document not found.", 404)
    db.session.delete(d)  # chunks and vectors cascade
    db.session.commit()
    return ok({"deleted": doc_id})


@bp.post("/rag/search")
@require_auth
def rag_search():
    data, err = json_body({"query": str})
    if err:
        return err
    query = data["query"].strip()[:1000]
    if not query:
        return fail("invalid_request", "A non-empty 'query' is required.")
    k = data.get("k", 5)
    if not isinstance(k, int) or not 1 <= k <= 20:
        return fail("invalid_request", "'k' must be an integer between 1 and 20.")
    ids = data.get("document_ids")
    if ids is not None and (not isinstance(ids, list) or not all(isinstance(i, str) for i in ids)):
        return fail("invalid_request", "'document_ids' must be a list of ids.")
    try:
        results = store.search(g.user.id, query, k, ids)
    except GeminiNotConfigured:
        return fail("ai_not_configured", "Search needs GEMINI_API_KEY, which is not set on this server.", 503)
    except EmbeddingError as e:
        return fail("ai_unavailable", str(e), 502)
    return ok({"query": query, "results": results})
