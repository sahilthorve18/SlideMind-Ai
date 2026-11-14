"""REST endpoints for user visual assets, uploads, and secure asset delivery."""
import hashlib
import io
import logging
import os
from typing import Any, Dict

from flask import Blueprint, Response, g, request, send_file

from database import db
from models import VisualAsset
from services import storage
from utils.http import fail, json_body, ok, require_auth

log = logging.getLogger(__name__)

bp = Blueprint("assets", __name__, url_prefix="/api/assets")

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpeg",
    "image/jpg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
    "image/svg+xml": "svg",
    "image/gif": "gif",
}


def _asset_dict(a: VisualAsset) -> Dict[str, Any]:
    secure_url = storage.build_secure_asset_url(a.id, a.user_id)
    return {
        "id": a.id,
        "filename": a.filename,
        "original_filename": a.original_filename,
        "file_type": a.file_type,
        "mime_type": a.mime_type,
        "size_bytes": a.size_bytes,
        "storage_provider": a.storage_provider,
        "width": a.width,
        "height": a.height,
        "aspect_ratio": a.aspect_ratio,
        "title": a.title,
        "description": a.description,
        "tags": a.tags or [],
        "visual_category": a.visual_category,
        "is_company_logo": a.is_company_logo,
        "is_product_photo": a.is_product_photo,
        "secure_url": secure_url,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@bp.post("/upload")
@require_auth
def upload_asset():
    """Uploads a user visual asset (logo, diagram, product photo, graphic).
    Stores persistently, analyzes dimensions & tags, and returns asset metadata.
    """
    f = request.files.get("file")
    if not f or not f.filename:
        return fail("invalid_request", "Attach a valid image file in the 'file' field.", 400)

    # Validate mime type
    mime = (f.mimetype or "").lower()
    if mime not in ALLOWED_IMAGE_TYPES:
        # Fall back to extension inspection
        ext = os.path.splitext(f.filename)[1].lower()
        if ext in (".jpg", ".jpeg"):
            mime = "image/jpeg"
        elif ext == ".png":
            mime = "image/png"
        elif ext == ".webp":
            mime = "image/webp"
        elif ext == ".svg":
            mime = "image/svg+xml"
        elif ext == ".gif":
            mime = "image/gif"
        else:
            return fail("unsupported_media_type", f"Unsupported image type. Allowed: {list(ALLOWED_IMAGE_TYPES.keys())}", 415)

    data = f.read()
    if not data:
        return fail("invalid_request", "The uploaded file is empty.", 400)

    max_mb = 20
    if len(data) > max_mb * 1024 * 1024:
        return fail("file_too_large", f"Image exceeds maximum size of {max_mb}MB.", 413)

    content_hash = hashlib.sha256(data).hexdigest()

    # Check for deduplication
    existing = VisualAsset.query.filter_by(user_id=g.user.id, content_hash=content_hash).first()
    if existing:
        return ok({**_asset_dict(existing), "duplicate": True}, 200)

    # Save to persistent storage backend
    try:
        storage_key, provider = storage.save_asset_file(
            user_id=g.user.id,
            original_filename=f.filename,
            data=data,
            content_type=mime,
        )
    except Exception as e:
        log.error("Failed storing asset file: %s", e)
        return fail("storage_error", "Failed to store image in persistent storage.", 500)

    # Inspect dimensions
    img_info = storage.inspect_image_bytes(data)

    # Extract tags & classification
    meta = storage.extract_visual_metadata_and_tags(f.filename, data, img_info)

    asset = VisualAsset(
        user_id=g.user.id,
        filename=os.path.basename(storage_key),
        original_filename=f.filename,
        file_type=img_info.get("format", ALLOWED_IMAGE_TYPES.get(mime, "png")),
        mime_type=mime,
        size_bytes=len(data),
        content_hash=content_hash,
        storage_key=storage_key,
        storage_provider=provider,
        width=img_info.get("width"),
        height=img_info.get("height"),
        aspect_ratio=img_info.get("aspect_ratio"),
        title=meta.get("title") or f.filename,
        description=meta.get("description"),
        tags=meta.get("tags") or [],
        visual_category=meta.get("category", "general"),
        is_company_logo=meta.get("is_logo", False),
        is_product_photo=meta.get("is_product", False),
    )

    db.session.add(asset)
    db.session.commit()

    return ok({**_asset_dict(asset), "duplicate": False}, 201)


@bp.get("")
@require_auth
def list_assets():
    """Lists all visual assets uploaded by the authenticated user."""
    category = request.args.get("category")
    q = VisualAsset.query.filter_by(user_id=g.user.id)
    if category:
        q = q.filter_by(visual_category=category)
    assets = q.order_by(VisualAsset.created_at.desc()).all()
    return ok([_asset_dict(a) for a in assets])


@bp.get("/<asset_id>/view")
def view_asset(asset_id: str):
    """Secure proxy for serving user asset bytes.
    Secured by either:
    1. A valid Authorization Bearer token header from the asset owner.
    2. A cryptographically signed HMAC URL token (?token=...).
    Prevents guessable public URLs while allowing Google Slides API and canvas rendering.
    """
    asset = VisualAsset.query.filter_by(id=asset_id).first()
    if not asset:
        return fail("not_found", "Asset not found.", 404)

    # Authentication check
    authorized = False

    # Check 1: Signed URL token
    token = request.args.get("token")
    if token and storage.verify_signed_asset_token(asset.id, asset.user_id, token):
        authorized = True

    # Check 2: Session Bearer token
    if not authorized:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from utils.http import TOKEN_MAX_AGE, _serializer

                payload = _serializer().loads(auth_header[7:], max_age=TOKEN_MAX_AGE)
                if payload and payload.get("uid") == asset.user_id:
                    authorized = True
            except Exception:
                pass

    if not authorized:
        return fail("unauthorized", "Access denied. A valid authorization token or signature is required.", 401)

    try:
        data = storage.read_asset_file(asset.storage_key, asset.storage_provider)
    except FileNotFoundError:
        return fail("not_found", "Image content could not be located in storage.", 404)
    except Exception as e:
        log.error("Failed reading asset %s: %s", asset_id, e)
        return fail("storage_error", "Failed retrieving image from storage.", 500)

    resp = Response(data, mimetype=asset.mime_type or "image/png")
    resp.headers["Cache-Control"] = "private, max-age=86400"
    resp.headers["Content-Disposition"] = f'inline; filename="{asset.original_filename}"'
    return resp


@bp.delete("/<asset_id>")
@require_auth
def delete_asset(asset_id: str):
    """Deletes an asset from database and storage."""
    asset = VisualAsset.query.filter_by(id=asset_id, user_id=g.user.id).first()
    if not asset:
        return fail("not_found", "Asset not found.", 404)

    storage.delete_asset_file(asset.storage_key, asset.storage_provider)
    db.session.delete(asset)
    db.session.commit()
    return ok({"deleted": asset_id})
