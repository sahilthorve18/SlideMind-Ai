"""Database models for every table the spec requires."""
import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector

from database import db

EMBED_DIM = 768


def _uuid() -> str:
    return str(uuid.uuid4())


_last_ts = 0.0

def _now():
    global _last_ts
    import time
    t = time.time()
    if t <= _last_ts:
        t = _last_ts + 0.001
    _last_ts = t
    return datetime.fromtimestamp(t, timezone.utc)


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class User(TimestampMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255))
    avatar_url = db.Column(db.String(512))
    google_sub = db.Column(db.String(64), unique=True, index=True)
    # Encrypted at rest in Phase 5; never returned to the frontend.
    google_refresh_token_enc = db.Column(db.Text)
    google_scopes = db.Column(db.Text)  # space-separated scopes the user actually granted

    @property
    def is_guest(self) -> bool:
        return bool(self.email and self.email.startswith("guest_") and self.email.endswith("@slidemind.ai"))


class Conversation(TimestampMixin, db.Model):
    __tablename__ = "conversations"
    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(255), default="New chat")
    active_presentation_id = db.Column(db.String(36), db.ForeignKey("presentations.id", ondelete="SET NULL"))
    messages = db.relationship("Message", backref="conversation", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    conversation_id = db.Column(db.String(36), db.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = db.Column(db.String(16), nullable=False)  # user | assistant | tool
    content = db.Column(db.Text, nullable=False)
    meta = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False, index=True)


class Document(TimestampMixin, db.Model):
    __tablename__ = "documents"
    __table_args__ = (db.UniqueConstraint("user_id", "content_hash", name="uq_document_user_hash"),)
    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(8), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    content_hash = db.Column(db.String(64), nullable=False)  # prevents duplicate indexing
    page_count = db.Column(db.Integer)
    status = db.Column(db.String(16), default="pending", nullable=False)  # pending|indexed|failed
    error = db.Column(db.Text)
    chunks = db.relationship("DocumentChunk", backref="document", cascade="all, delete-orphan")


class DocumentChunk(db.Model):
    __tablename__ = "document_chunks"
    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    document_id = db.Column(db.String(36), db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.String(36), nullable=False, index=True)
    chunk_index = db.Column(db.Integer, nullable=False)
    page_number = db.Column(db.Integer)
    section_heading = db.Column(db.String(512))
    text = db.Column(db.Text, nullable=False)
    # pgvector on PostgreSQL; JSON fallback on SQLite (dev/tests).
    embedding = db.Column(db.JSON().with_variant(Vector(EMBED_DIM), "postgresql"))
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)


class Presentation(TimestampMixin, db.Model):
    __tablename__ = "presentations"
    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    google_presentation_id = db.Column(db.String(128), index=True)
    google_url = db.Column(db.String(512))
    settings = db.Column(db.JSON, default=dict)  # audience, language, theme, citation style...
    status = db.Column(db.String(16), default="draft", nullable=False)
    slides = db.relationship("Slide", backref="presentation", cascade="all, delete-orphan", order_by="Slide.position")
    versions = db.relationship("PresentationVersion", backref="presentation", cascade="all, delete-orphan")


class Slide(TimestampMixin, db.Model):
    __tablename__ = "slides"
    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    presentation_id = db.Column(db.String(36), db.ForeignKey("presentations.id", ondelete="CASCADE"), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False)
    google_object_id = db.Column(db.String(128))
    title = db.Column(db.String(512))
    content = db.Column(db.JSON, default=dict)
    speaker_notes = db.Column(db.Text)


class PresentationVersion(db.Model):
    __tablename__ = "presentation_versions"
    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    presentation_id = db.Column(db.String(36), db.ForeignKey("presentations.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = db.Column(db.Integer, nullable=False)
    snapshot = db.Column(db.JSON, nullable=False)
    reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)


class SourceReference(db.Model):
    __tablename__ = "source_references"
    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    slide_id = db.Column(db.String(36), db.ForeignKey("slides.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_text = db.Column(db.Text)
    source_type = db.Column(db.String(16), nullable=False)  # document | web
    document_id = db.Column(db.String(36), db.ForeignKey("documents.id", ondelete="SET NULL"))
    chunk_id = db.Column(db.String(36), db.ForeignKey("document_chunks.id", ondelete="SET NULL"))
    page_number = db.Column(db.Integer)
    passage = db.Column(db.Text)
    url = db.Column(db.String(1024))
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False)


class ToolExecutionLog(db.Model):
    __tablename__ = "tool_execution_logs"
    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    conversation_id = db.Column(db.String(36), db.ForeignKey("conversations.id", ondelete="SET NULL"), index=True)
    user_id = db.Column(db.String(36), index=True)
    tool_name = db.Column(db.String(64), nullable=False, index=True)
    arguments = db.Column(db.JSON)
    result_summary = db.Column(db.Text)
    status = db.Column(db.String(16), nullable=False)  # success | error
    error = db.Column(db.Text)
    duration_ms = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True), default=_now, nullable=False, index=True)


class BackgroundJob(TimestampMixin, db.Model):
    __tablename__ = "background_jobs"
    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(db.String(36), nullable=False, index=True)
    kind = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(16), default="queued", nullable=False, index=True)  # queued|running|done|failed
    progress = db.Column(db.Integer, default=0, nullable=False)
    payload = db.Column(db.JSON)
    result = db.Column(db.JSON)
    error = db.Column(db.Text)


class VisualAsset(TimestampMixin, db.Model):
    __tablename__ = "visual_assets"
    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(32), nullable=False)  # png, jpeg, webp, svg
    mime_type = db.Column(db.String(64), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    content_hash = db.Column(db.String(64), nullable=False, index=True)
    storage_key = db.Column(db.String(512), nullable=False)
    storage_provider = db.Column(db.String(32), default="local", nullable=False)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    aspect_ratio = db.Column(db.Float)
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    tags = db.Column(db.JSON, default=list)  # extracted visual tags e.g. ["logo", "solar", "wind", "product"]
    visual_category = db.Column(db.String(64), default="general")  # logo, product, diagram, photo, team
    is_company_logo = db.Column(db.Boolean, default=False)
    is_product_photo = db.Column(db.Boolean, default=False)
    meta = db.Column(db.JSON, default=dict)
