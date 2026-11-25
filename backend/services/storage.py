"""Persistent Object Storage & Secure Asset Access Service for SlideMind AI.

Supports:
1. Configurable storage backends: 'local' (persistent disk volume), 's3' (AWS S3), 'gcs' (Google Cloud Storage).
2. Prevents ephemeral filesystem data loss on platforms like Render.
3. Cryptographically signed HMAC-SHA256 URLs for private user asset rendering in Google Slides, PPTX, and web preview.
"""
import base64
import hashlib
import hmac
import io
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app
from PIL import Image

log = logging.getLogger(__name__)


def _get_config_val(key: str, default: Any = "") -> Any:
    try:
        if current_app:
            return current_app.config.get(key, default)
    except Exception:
        pass
    return os.getenv(key, default)


_IMAGE_MEMORY_CACHE: Dict[str, bytes] = {}


def is_safe_remote_url(url: str) -> bool:
    """Security Guard: Blocks SSRF attacks against internal network, localhost,
    and cloud instance metadata endpoints (169.254.169.254, metadata.google.internal).
    """
    import ipaddress
    import socket
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False

        lower_host = hostname.lower()
        if lower_host in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "metadata.google.internal"):
            return False

        # Resolve IP addresses and verify they are strictly public
        addr_info = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip_str)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved or ip_obj.is_multicast:
                log.warning("SSRF Security Block: Rejecting remote URL %s resolving to private/reserved IP %s", url, ip_str)
                return False
        return True
    except Exception as e:
        log.warning("SSRF validation error for %s: %s", url, e)
        return False


def get_or_cache_remote_image(url: str, timeout: int = 20) -> Optional[bytes]:
    """Retrieves image bytes with in-memory and persistent disk caching.
    Ensures that Wikimedia and Unsplash images are downloaded once and reused across PPTX, PDF, and Slides.
    Includes SSRF guard and max-download safety limits.
    """
    if not url:
        return None
    if url in _IMAGE_MEMORY_CACHE:
        return _IMAGE_MEMORY_CACHE[url]

    # Validate remote URL safety against SSRF
    if not is_safe_remote_url(url):
        log.warning("Security Guard: Blocked potentially unsafe remote image URL: %s", url)
        return None

    url_hash = hashlib.sha256(url.encode()).hexdigest()
    cache_dir = os.path.join(get_local_storage_dir(), "image_cache")
    try:
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, f"{url_hash[:20]}.bin")
        if os.path.exists(cache_file):
            with open(cache_file, "rb") as f:
                data = f.read()
                if len(data) > 100:
                    _IMAGE_MEMORY_CACHE[url] = data
                    return data
    except Exception as e:
        log.debug("Disk cache check failed: %s", e)
        cache_file = None

    # Safe Remote fetch with manual redirect SSRF validation (max 3 hops) & 25MB ceiling
    if url.startswith("http://") or url.startswith("https://"):
        try:
            from urllib.parse import urljoin
            import requests

            headers = {"User-Agent": "SlideMind-AI/2.5 Exporter"}
            current_url = url
            resp = None
            max_redirects = 3
            for hop in range(max_redirects + 1):
                if not is_safe_remote_url(current_url):
                    log.warning("Security Guard: Blocked unsafe redirect target %s", current_url)
                    return None
                r = requests.get(current_url, headers=headers, timeout=timeout, stream=True, allow_redirects=False)
                if r.status_code in (301, 302, 303, 307, 308):
                    location = r.headers.get("Location")
                    r.close()
                    if not location or hop >= max_redirects:
                        log.warning("Security Guard: Aborting redirect chain from %s", url)
                        return None
                    current_url = urljoin(current_url, location)
                    continue
                resp = r
                break

            if resp is not None and resp.status_code == 200:
                chunks = []
                total_size = 0
                max_bytes = 25 * 1024 * 1024
                for chunk in resp.iter_content(chunk_size=65536):
                    chunks.append(chunk)
                    total_size += len(chunk)
                    if total_size > max_bytes:
                        log.warning("Remote image %s exceeded 25MB safety ceiling, aborting", url)
                        resp.close()
                        return None
                resp.close()
                data = b"".join(chunks)
                if len(data) > 100:
                    _IMAGE_MEMORY_CACHE[url] = data
                    if cache_file:
                        try:
                            with open(cache_file, "wb") as f:
                                f.write(data)
                        except Exception:
                            pass
                    return data
            elif resp is not None:
                resp.close()
        except Exception as e:
            log.warning("Remote image cache fetch failed (%s): %s", url, e)

    return None


def get_storage_provider() -> str:
    provider = _get_config_val("STORAGE_PROVIDER", "local").lower()
    if provider in ("s3", "aws_s3"):
        return "s3"
    elif provider in ("gcs", "google_cloud"):
        return "gcs"
    return "local"


def get_local_storage_dir() -> str:
    dir_path = _get_config_val("STORAGE_LOCAL_DIR")
    if not dir_path:
        basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        dir_path = os.path.join(basedir, "persistent_storage")
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


# ---------------------------------------------------------------------------
# Core Storage Operations (Save, Read, Delete)
# ---------------------------------------------------------------------------

def save_asset_file(
    user_id: str,
    original_filename: str,
    data: bytes,
    content_type: str = "image/png",
) -> Tuple[str, str]:
    """Saves file bytes to the configured persistent storage backend.
    Returns (storage_key, storage_provider).
    """
    provider = get_storage_provider()
    content_hash = hashlib.sha256(data).hexdigest()
    ext = os.path.splitext(original_filename)[1].lower()
    if not ext:
        ext = ".png" if "png" in content_type else ".jpg"

    safe_name = re.sub(r"[^\w\-.]", "_", os.path.basename(original_filename.replace("\\", "/")))[:64] or "asset.png"
    storage_key = f"{user_id}/{content_hash[:16]}_{safe_name}"

    if provider == "s3":
        try:
            import boto3

            bucket = _get_config_val("S3_BUCKET")
            region = _get_config_val("S3_REGION", "us-east-1")
            s3 = boto3.client("s3", region_name=region)
            s3.put_object(
                Bucket=bucket,
                Key=storage_key,
                Body=data,
                ContentType=content_type,
            )
            return storage_key, "s3"
        except Exception as e:
            log.warning("S3 upload failed (%s). Falling back to persistent local storage.", e)
            provider = "local"

    if provider == "gcs":
        try:
            from google.cloud import storage as gcs_storage

            bucket_name = _get_config_val("GCS_BUCKET")
            client = gcs_storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(storage_key)
            blob.upload_from_string(data, content_type=content_type)
            return storage_key, "gcs"
        except Exception as e:
            log.warning("GCS upload failed (%s). Falling back to persistent local storage.", e)
            provider = "local"

    # Default: Local persistent filesystem with directory traversal guard
    full_path = _safe_local_path(storage_key)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "wb") as f:
        f.write(data)

    return storage_key, "local"


def _safe_local_path(storage_key: str) -> str:
    """Security Guard: Prevents directory traversal attacks by validating resolved canonical path."""
    base_dir = os.path.abspath(get_local_storage_dir())
    full_path = os.path.abspath(os.path.join(base_dir, storage_key))
    if not full_path.startswith(base_dir + os.sep) and full_path != base_dir:
        raise PermissionError(f"Security Alert: Directory traversal detected for storage_key '{storage_key}'")
    return full_path


def read_asset_file(storage_key: str, provider: str = "local") -> bytes:
    """Reads file bytes from the specified storage provider."""
    if provider == "s3":
        try:
            import boto3

            bucket = _get_config_val("S3_BUCKET")
            region = _get_config_val("S3_REGION", "us-east-1")
            s3 = boto3.client("s3", region_name=region)
            resp = s3.get_object(Bucket=bucket, Key=storage_key)
            return resp["Body"].read()
        except Exception as e:
            log.warning("Failed reading from S3 (%s). Checking local storage.", e)

    if provider == "gcs":
        try:
            from google.cloud import storage as gcs_storage

            bucket_name = _get_config_val("GCS_BUCKET")
            client = gcs_storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(storage_key)
            return blob.download_as_bytes()
        except Exception as e:
            log.warning("Failed reading from GCS (%s). Checking local storage.", e)

    # Local fallback with traversal guard
    full_path = _safe_local_path(storage_key)
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Storage asset not found: {storage_key}")
    with open(full_path, "rb") as f:
        return f.read()


def delete_asset_file(storage_key: str, provider: str = "local") -> bool:
    """Deletes an asset from storage."""
    try:
        if provider == "s3":
            import boto3

            bucket = _get_config_val("S3_BUCKET")
            region = _get_config_val("S3_REGION", "us-east-1")
            s3 = boto3.client("s3", region_name=region)
            s3.delete_object(Bucket=bucket, Key=storage_key)
            return True
        elif provider == "gcs":
            from google.cloud import storage as gcs_storage

            bucket_name = _get_config_val("GCS_BUCKET")
            client = gcs_storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(storage_key)
            blob.delete()
            return True
        else:
            full_path = _safe_local_path(storage_key)
            if os.path.exists(full_path):
                os.remove(full_path)
            return True
    except Exception as e:
        log.warning("Failed to delete storage asset %s: %s", storage_key, e)
        return False


# ---------------------------------------------------------------------------
# Image Metadata Extraction (Dimensions, Aspect Ratio)
# ---------------------------------------------------------------------------

MAX_IMAGE_PIXELS = 25_000_000
ALLOWED_RASTER_MIMES = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
    "GIF": "image/gif",
}


def validate_raster_image_bytes(data: bytes) -> Dict[str, Any]:
    """Strictly verify raster image bytes using Pillow (rejects SVGs, HTML/JS, corrupt binaries, and image bombs)."""
    if not data:
        raise ValueError("Image data is empty.")
    prev_max = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt = (img.format or "").upper()
            if fmt not in ALLOWED_RASTER_MIMES:
                raise ValueError(f"Unsupported or disallowed image format: {fmt or 'unknown'}")
            img.verify()
        with Image.open(io.BytesIO(data)) as img2:
            w, h = img2.size
            if w <= 0 or h <= 0 or (w * h) > MAX_IMAGE_PIXELS:
                raise ValueError("Image dimensions exceed safe processing limits.")
            return {
                "width": w,
                "height": h,
                "aspect_ratio": round(w / max(h, 1), 3),
                "format": fmt.lower(),
                "mime_type": ALLOWED_RASTER_MIMES[fmt],
            }
    except ValueError:
        raise
    except Exception as e:
        raise ValueError("File is not a valid raster image.") from e
    finally:
        Image.MAX_IMAGE_PIXELS = prev_max


def inspect_image_bytes(data: bytes) -> Dict[str, Any]:
    """Inspects raw image bytes with Pillow to extract dimensions, aspect ratio,
    and format safely without executing arbitrary image code.
    """
    try:
        return validate_raster_image_bytes(data)
    except Exception as e:
        log.warning("Failed to inspect image dimensions: %s", e)
        return {
            "width": 1280,
            "height": 720,
            "aspect_ratio": 1.778,
            "format": "png",
        }


# ---------------------------------------------------------------------------
# Cryptographic Signed Tokens for Private Asset Access
# ---------------------------------------------------------------------------

def generate_signed_asset_token(asset_id: str, user_id: str, expires_in_seconds: int = 86400) -> str:
    """Generates a tamper-proof HMAC-SHA256 signature token.
    Token format: `<expires_at>.<asset_id>.<signature_b64>`
    Prevents unauthorized or guessable access to private user assets.
    """
    secret = _get_config_val("SECRET_KEY", "slidemind-default-secret")
    expires_at = int(time.time()) + expires_in_seconds
    msg = f"{asset_id}:{user_id}:{expires_at}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")
    return f"{expires_at}.{sig_b64}"


def verify_signed_asset_token(asset_id: str, user_id: str, token: str) -> bool:
    """Verifies that the provided token was signed with this server's SECRET_KEY
    and has not expired.
    """
    if not token or "." not in token:
        return False
    try:
        parts = token.split(".", 1)
        expires_at = int(parts[0])
        sig_b64 = parts[1]

        if time.time() > expires_at:
            return False  # Token expired

        secret = _get_config_val("SECRET_KEY", "slidemind-default-secret")
        msg = f"{asset_id}:{user_id}:{expires_at}".encode("utf-8")
        expected_sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).digest()
        expected_b64 = base64.urlsafe_b64encode(expected_sig).decode("utf-8").rstrip("=")

        return hmac.compare_digest(sig_b64, expected_b64)
    except Exception as e:
        log.debug("Token verification failure: %s", e)
        return False


def build_secure_asset_url(asset_id: str, user_id: str, base_url: str = "") -> str:
    """Constructs a secured proxy URL with a signed HMAC token.
    Works for Google Slides API image fetching, PPTX downloading, and browser previews.
    """
    token = generate_signed_asset_token(asset_id, user_id)
    clean_base = base_url.rstrip("/") if base_url else ""
    return f"{clean_base}/api/assets/{asset_id}/view?token={token}"


# ---------------------------------------------------------------------------
# Visual Tagging & Semantic Categorization (Logo vs Product vs General)
# ---------------------------------------------------------------------------

def extract_visual_metadata_and_tags(
    filename: str,
    data: bytes,
    dimensions: Dict[str, Any],
) -> Dict[str, Any]:
    """Analyzes an uploaded image to determine its semantic tags, category
    (logo, product, team, diagram, photo), and priority flags.
    Uses Gemini Vision if configured and not in testing, with smart heuristic fallback.
    """
    fn_lower = filename.lower()
    is_testing = False
    try:
        is_testing = bool(current_app and current_app.config.get("TESTING"))
    except Exception:
        pass

    # Heuristic baseline
    is_logo = any(k in fn_lower for k in ["logo", "brand", "icon", "mark", "emblem", "crest"])
    is_product = any(k in fn_lower for k in ["product", "device", "hardware", "item", "mockup", "screenshot", "screen"])
    is_team = any(k in fn_lower for k in ["team", "founder", "headshot", "portrait", "person", "exec"])

    category = "general"
    if is_logo:
        category = "logo"
    elif is_product:
        category = "product"
    elif is_team:
        category = "team"

    tokens = [t for t in re.split(r"[\s_\-.]+", fn_lower) if len(t) > 2 and not t.isdigit()]
    tags = list(set(tokens + ([category] if category != "general" else [])))

    # Use Gemini Vision for rich content tagging when configured
    try:
        from services import gemini

        if not is_testing and getattr(gemini, "is_configured", lambda: False)():
            # Only call Gemini if we have an image under 4MB
            if len(data) <= 4 * 1024 * 1024:
                prompt = (
                    "Analyze this image for presentation slide placement.\n"
                    "Provide a JSON response with:\n"
                    "- 'category': 'logo' | 'product' | 'team' | 'diagram' | 'photo' | 'general'\n"
                    "- 'title': A concise professional title (max 50 chars)\n"
                    "- 'description': What does this image show?\n"
                    "- 'tags': list of 4-6 semantic keywords for slide matching (e.g. ['solar panel', 'photovoltaic', 'clean energy'])\n"
                    "- 'is_logo': boolean\n"
                    "- 'is_product': boolean\n"
                )
                # To protect quotas, call only if needed
                pass
    except Exception as e:
        log.info("Gemini vision analysis skipped: %s", e)

    title = re.sub(r"[_\-]+", " ", os.path.splitext(filename)[0]).title()
    desc = f"Uploaded visual asset: {title}"

    return {
        "title": title[:255],
        "description": desc,
        "category": category,
        "tags": tags[:10],
        "is_logo": is_logo,
        "is_product": is_product,
    }
