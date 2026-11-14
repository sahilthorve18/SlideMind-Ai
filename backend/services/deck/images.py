"""Resolve an image reference to bytes for the exporters. There is deliberately NO default/fallback
image: if an image cannot be fetched the slide is drawn without it."""
import io
import logging

log = logging.getLogger(__name__)


def image_bytes(src) -> bytes | None:
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
            from models import VisualAsset
            from services import storage
            asset = VisualAsset.query.filter_by(id=url.split("/api/assets/")[1].split("/")[0]).first()
            if asset:
                return storage.read_asset_file(asset.storage_key, asset.storage_provider)
    except Exception as e:  # noqa: BLE001
        log.debug("asset lookup failed: %s", e)
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
        im = Image.open(io.BytesIO(data))
        im.load()
        w, h = im.size
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        out = io.BytesIO()
        im.save(out, "JPEG", quality=88)
        return out.getvalue(), w, h
    except Exception as e:  # noqa: BLE001
        log.warning("unreadable image: %s", e)
        return None
