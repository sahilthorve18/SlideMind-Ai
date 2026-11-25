"""Resolve an image reference to bytes for the exporters. There is deliberately NO default/fallback
image: if an image cannot be fetched the slide is drawn without it."""
import io
import logging

log = logging.getLogger(__name__)


def image_bytes(src, owner_user_id: str | None = None) -> bytes | None:
    if isinstance(src, str):
        url = src
    elif isinstance(src, dict):
        url = src.get("url") or src.get("image_url")
    else:
        return None
    if not url:
        return None
    try:
        if "/api/assets/" in url:
            from urllib.parse import parse_qs, urlparse
            from models import VisualAsset
            from services import storage
            from services.prompt_safety import extract_asset_id_from_url

            asset_id = extract_asset_id_from_url(url)
            asset = VisualAsset.query.filter_by(id=asset_id).first() if asset_id else None
            if not asset:
                return None
            tok = parse_qs(urlparse(url).query).get("token", [None])[0]
            authorized = False
            if owner_user_id is not None:
                authorized = (asset.user_id == owner_user_id)
            elif tok:
                authorized = storage.verify_signed_asset_token(asset.id, asset.user_id, tok)
            if not authorized:
                log.warning("Asset export access denied for asset %s (owner mismatch or invalid token)", asset_id)
                return None
            return storage.read_asset_file(asset.storage_key, asset.storage_provider)
    except Exception as e:  # noqa: BLE001
        log.debug("asset lookup failed: %s", e)
        return None
    try:
        from services import storage
        data = storage.get_or_cache_remote_image(url, timeout=20)
        if data and len(data) > 100:
            return data
    except Exception as e:  # noqa: BLE001
        log.warning("image fetch failed (%s): %s", url, e)
    return None


def to_png_or_jpeg(data: bytes) -> tuple[bytes, int, int] | None:
    try:
        from PIL import Image
        from services.storage import MAX_IMAGE_PIXELS
        prev_max = Image.MAX_IMAGE_PIXELS
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
        try:
            im = Image.open(io.BytesIO(data))
            im.load()
            w, h = im.size
            if w <= 0 or h <= 0 or (w * h) > MAX_IMAGE_PIXELS:
                return None
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
            out = io.BytesIO()
            im.save(out, "JPEG", quality=88)
            return out.getvalue(), w, h
        finally:
            Image.MAX_IMAGE_PIXELS = prev_max
    except Exception as e:  # noqa: BLE001
        log.warning("unreadable image: %s", e)
        return None
