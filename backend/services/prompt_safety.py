"""Centralized security helpers for upload filename hygiene, safe URL checks, and prompt-injection boundaries."""
import os
import re
from urllib.parse import urlparse

_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_PROMPT_TEXT_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_FENCE_TAG_RE = re.compile(
    r"<\s*/?\s*(?:documents|sources|material|web|system|instructions|untrusted_data)\b[^>]*>",
    re.IGNORECASE,
)


def sanitize_filename(filename: str | None, fallback: str = "uploaded_file", max_len: int = 180) -> str:
    """Normalize an uploaded filename to a single safe basename without path separators, control chars, or quotes."""
    raw = str(filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    clean = _CONTROL_RE.sub("", raw)
    clean = re.sub(r'[<>:"\'`|?*]+', "_", clean)
    clean = re.sub(r"\s+", " ", clean).strip(" .")
    if not clean:
        clean = fallback
    return clean[:max_len]


def sanitize_prompt_label(text: str | None, max_len: int = 120) -> str:
    """Make a user-supplied label (filename, title) safe for single-line interpolation inside a prompt."""
    clean = _CONTROL_RE.sub(" ", str(text or ""))
    clean = re.sub(r'[<>"\'`]+', "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:max_len]


def sanitize_untrusted_text(text: str | None) -> str:
    """Neutralize control characters and XML-style boundary breakout tags inside untrusted document/web text."""
    clean = _PROMPT_TEXT_CONTROL_RE.sub("", str(text or ""))
    return _FENCE_TAG_RE.sub("[tag-removed]", clean)


def wrap_untrusted(tag: str, text: str | None) -> str:
    """Wrap untrusted text inside a balanced delimiter block after stripping matching boundary tags."""
    safe_tag = re.sub(r"[^a-zA-Z0-9_]", "", tag) or "untrusted_data"
    body = sanitize_untrusted_text(text)
    return f"<{safe_tag}>\n{body}\n</{safe_tag}>"


def extract_asset_id_from_url(url: str) -> str | None:
    """Extract asset_id from a local /api/assets/<id>/view URL, or None if not an asset URL."""
    if not isinstance(url, str) or "/api/assets/" not in url:
        return None
    tail = url.split("/api/assets/", 1)[1]
    asset_id = tail.split("/", 1)[0].split("?", 1)[0].strip()
    return asset_id or None


def is_safe_visual_url(url: str | None) -> bool:
    """Validate that a slide image URL is a public http(s) URL or local /api/assets/<id>/view path."""
    import ipaddress

    if not isinstance(url, str):
        return False
    u = url.strip()
    if not u or len(u) > 2048:
        return False
    if u.startswith("/api/assets/"):
        return bool(extract_asset_id_from_url(u))
    parsed = urlparse(u)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host in ("localhost", "metadata.google.internal", "0.0.0.0"):
        return False
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    except ValueError:
        pass  # domain name (further checked via DNS at fetch time)
    return True
