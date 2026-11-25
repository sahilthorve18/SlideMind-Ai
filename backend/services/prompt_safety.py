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


def is_noncanonical_ip_host(host: str) -> bool:
    """Detect obfuscated IPv4 hostnames (decimal 2130706433, hex 0x7f000001, octal 0177.0.0.1, shorthand 127.1)."""
    import ipaddress

    h = (host or "").strip().lower()
    if not re.fullmatch(r"(?:\d+|0x[0-9a-f]+)(?:\.(?:\d+|0x[0-9a-f]+)){0,3}", h, re.I):
        return False
    parts = h.split(".")
    if len(parts) != 4 or any(p.startswith("0x") or (len(p) > 1 and p.startswith("0")) for p in parts):
        return True
    try:
        ipaddress.ip_address(h)
        return False
    except ValueError:
        return True


def is_disallowed_ip(ip_obj) -> bool:
    """True when an IP (or its IPv4-mapped counterpart for ::ffff:x.x.x.x) is private, loopback, link-local, reserved, or unspecified."""
    candidates = [ip_obj]
    mapped = getattr(ip_obj, "ipv4_mapped", None)
    if mapped is not None:
        candidates.append(mapped)
    return any(
        c.is_private or c.is_loopback or c.is_link_local or c.is_reserved or c.is_multicast or c.is_unspecified
        for c in candidates
    )


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
    if host in ("localhost", "metadata.google.internal", "0.0.0.0") or is_noncanonical_ip_host(host):
        return False
    try:
        ip = ipaddress.ip_address(host)
        if is_disallowed_ip(ip):
            return False
    except ValueError:
        pass  # domain name (further checked via DNS at fetch time)
    return True
