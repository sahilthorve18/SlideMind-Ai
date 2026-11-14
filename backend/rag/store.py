"""Indexing and semantic retrieval.

Vectors live in the `document_chunks.embedding` column: pgvector on PostgreSQL
(persistent, works on Render free + external Postgres), JSON on SQLite for
local development and tests (cosine similarity computed in Python).
"""
import hashlib

import sqlalchemy as sa

from database import db
from models import Document, DocumentChunk
from rag import embed
from rag.chunk import chunk_segments
from rag.extract import extract

MAX_CHUNKS = 400  # keeps indexing inside free-tier time/memory limits


class DocumentTooLarge(Exception):
    pass


def _is_pg() -> bool:
    return db.engine.dialect.name == "postgresql"


def index_document(user_id: str, filename: str, data: bytes) -> tuple[Document, bool]:
    """Validate, extract, chunk, embed and store. Returns (document, duplicate)."""
    ftype, segments, pages = extract(filename, data)  # raises ExtractionError
    digest = hashlib.sha256(data).hexdigest()

    existing = Document.query.filter_by(user_id=user_id, content_hash=digest).first()
    if existing and existing.status == "indexed":
        return existing, True
    if existing:  # previous attempt failed: retry cleanly
        db.session.delete(existing)
        db.session.commit()

    chunks = chunk_segments(segments)
    if len(chunks) > MAX_CHUNKS:
        raise DocumentTooLarge(f"This document is too large to index (over {MAX_CHUNKS} sections). Try a shorter file.")

    # Embed first so a failure leaves nothing half-indexed.
    vectors = embed.embed_texts([c.text for c in chunks], "RETRIEVAL_DOCUMENT")

    doc = Document(user_id=user_id, filename=filename[:255], file_type=ftype, size_bytes=len(data),
                   content_hash=digest, page_count=pages, status="indexed")
    db.session.add(doc)
    db.session.flush()
    for i, (c, v) in enumerate(zip(chunks, vectors)):
        db.session.add(DocumentChunk(document_id=doc.id, user_id=user_id, chunk_index=i, page_number=c.page,
                                     section_heading=(c.heading or "")[:512] or None, text=c.text, embedding=v))
    db.session.commit()
    return doc, False


def search(user_id: str, query: str, k: int = 5, document_ids: list[str] | None = None) -> list[dict]:
    """Semantic search over ONE user's indexed documents."""
    qvec = embed.embed_texts([query], "RETRIEVAL_QUERY")[0]
    base = (
        db.session.query(DocumentChunk, Document.filename)
        .join(Document, Document.id == DocumentChunk.document_id)
        .filter(DocumentChunk.user_id == user_id, Document.user_id == user_id, Document.status == "indexed")
    )
    if document_ids:
        base = base.filter(DocumentChunk.document_id.in_(document_ids))

    if _is_pg():
        from pgvector.sqlalchemy import Vector

        qlit = sa.cast(sa.literal("[" + ",".join(f"{x:.8f}" for x in qvec) + "]"), Vector(embed.EMBED_DIM))
        dist = DocumentChunk.embedding.op("<=>", return_type=sa.Float)(qlit)
        rows = base.add_columns(dist.label("dist")).order_by("dist").limit(k).all()
        scored = [(1 - float(d), c, fn) for c, fn, d in rows]
    else:
        scored = []
        for c, fn in base.all():
            if c.embedding:
                scored.append((sum(a * b for a, b in zip(qvec, c.embedding)), c, fn))
        scored.sort(key=lambda t: t[0], reverse=True)
        scored = scored[:k]

    return [
        {
            "chunk_id": c.id,
            "document_id": c.document_id,
            "filename": fn,
            "page_number": c.page_number,
            "section_heading": c.section_heading,
            "text": c.text,
            "score": round(score, 4),
        }
        for score, c, fn in scored
    ]
