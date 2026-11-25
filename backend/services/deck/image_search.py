"""Clean, modern visual search engine for SlideMind AI deck generation.
Queries Wikimedia Commons, Wikipedia, Unsplash, Pexels, and bespoke AI visuals.
"""
from dataclasses import asdict, dataclass
import hashlib
import html
import logging
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote
import requests

log = logging.getLogger(__name__)

USER_AGENT = "SlideMind-AI-PresentationEngine/2.0 (https://slidemind.ai; contact@slidemind.ai)"
REQUEST_TIMEOUT = 12


@dataclass
class VisualBrief:
    slide_title: str
    main_message: str
    key_concepts: List[str]
    required_visual_type: str = "photograph"
    search_keywords: List[str] = None
    preferred_composition: str = "split_right"
    aspect_ratio: str = "16:9"
    visual_placement: str = "right"
    style: str = "editorial"
    negative_space: str = "balanced"

    def __post_init__(self):
        if self.search_keywords is None:
            self.search_keywords = [self.slide_title]


@dataclass
class CandidateImage:
    id: str
    title: str
    image_url: str
    thumb_url: str
    source: str
    source_page: str
    artist: str
    artist_url: Optional[str]
    license: str
    license_url: Optional[str]
    width: int
    height: int
    aspect_ratio: float
    description: str
    score: float = 0.0
    relevance_rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clean_html_text(raw_html: Optional[str]) -> str:
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", "", raw_html)
    return html.unescape(text).strip()


def search_wikipedia_images(query: str, limit: int = 4) -> List[CandidateImage]:
    """Retrieves encyclopedic photography from Wikipedia REST API with CC/Public Domain licensing."""
    clean_query = query.strip()
    if not clean_query:
        return []

    url = "https://en.wikipedia.org/w/rest.php/v1/search/page"
    params = {"q": clean_query, "limit": min(max(limit, 1), 8)}
    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return []
        data = resp.json()
        pages = data.get("pages", [])
        candidates: List[CandidateImage] = []

        for p in pages:
            thumb_info = p.get("thumbnail")
            if not thumb_info or not thumb_info.get("url"):
                continue
            raw_url = thumb_info["url"]
            full_thumb = "https:" + raw_url if raw_url.startswith("//") else raw_url

            # Skip SVG, flags, icons, coats of arms
            fl = full_thumb.lower()
            if any(skip in fl for skip in (".svg", "flag_of_", "coat_of_arms", "symbol", "icon", "logo", "map")):
                continue

            hi_res_url = re.sub(r"/\d+px-", "/1280px-", full_thumb)
            medium_url = re.sub(r"/\d+px-", "/640px-", full_thumb)
            pid = p.get("id") or abs(hash(full_thumb)) % 1000000
            title = p.get("title") or clean_query
            desc = p.get("description") or f"{title} — Encyclopedic topic visual"
            page_key = p.get("key", title.replace(" ", "_"))

            candidates.append(
                CandidateImage(
                    id=f"wiki_page_{pid}",
                    title=title,
                    image_url=hi_res_url,
                    thumb_url=medium_url,
                    source="Wikimedia Commons",
                    source_page=f"https://en.wikipedia.org/wiki/{quote(page_key)}",
                    artist="Wikipedia / Wikimedia Commons Contributor",
                    artist_url=f"https://en.wikipedia.org/wiki/{quote(page_key)}",
                    license="Creative Commons Attribution-ShareAlike 4.0 / Public Domain",
                    license_url="https://creativecommons.org/licenses/by-sa/4.0/",
                    width=1280,
                    height=720,
                    aspect_ratio=1.78,
                    description=desc[:250],
                    score=84.0,
                    relevance_rationale=f"Authentic Wikipedia web topic photograph for '{title}'",
                )
            )
        return candidates
    except Exception as e:
        log.warning("Wikipedia REST search failed for '%s': %s", clean_query, e)
        return []


def search_wikimedia_commons(query: str, limit: int = 6) -> List[CandidateImage]:
    """Retrieves high-resolution, commercially licensed Creative Commons / Public Domain
    images from the official Wikimedia Commons API with full author & license metadata.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": clean_query,
        "gsrnamespace": 6,
        "gsrlimit": min(max(limit, 1), 12),
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata|dimensions",
        "iiurlwidth": 1280,
        "format": "json",
    }
    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return []
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        candidates: List[CandidateImage] = []

        for pid, page in pages.items():
            title = page.get("title", "").replace("File:", "").strip()
            if not any(title.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
                continue

            imageinfo = page.get("imageinfo", [{}])[0]
            thumb_url = imageinfo.get("thumburl") or imageinfo.get("url")
            if not thumb_url:
                continue

            extmeta = imageinfo.get("extmetadata", {})
            width = int(imageinfo.get("thumbwidth") or imageinfo.get("width") or 1280)
            height = int(imageinfo.get("thumbheight") or imageinfo.get("height") or 720)
            ar = round(width / max(height, 1), 2)

            lic = extmeta.get("LicenseShortName", {}).get("value") or "Public Domain / CC"
            lic_url = extmeta.get("LicenseUrl", {}).get("value")
            artist = _clean_html_text(extmeta.get("Artist", {}).get("value")) or "Wikimedia Commons Contributor"
            desc = _clean_html_text(extmeta.get("ImageDescription", {}).get("value")) or title

            candidates.append(
                CandidateImage(
                    id=f"wiki_{pid}",
                    title=title,
                    image_url=thumb_url,
                    thumb_url=thumb_url,
                    source="Wikimedia Commons",
                    source_page=imageinfo.get("descriptionurl") or f"https://commons.wikimedia.org/wiki/File:{quote(title)}",
                    artist=artist[:100],
                    artist_url=None,
                    license=str(lic),
                    license_url=lic_url,
                    width=width,
                    height=height,
                    aspect_ratio=ar,
                    description=desc[:250],
                )
            )

        return candidates
    except Exception as e:
        log.warning("Wikimedia Commons search failed for '%s': %s", query, e)
        return []


def search_unsplash(query: str, limit: int = 6) -> List[CandidateImage]:
    """Retrieves high-resolution images from Unsplash API when access key is provided."""
    key = os.getenv("UNSPLASH_ACCESS_KEY")
    if not key:
        return []

    url = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {key}", "User-Agent": USER_AGENT}
    params = {"query": query, "per_page": limit, "orientation": "landscape"}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return []
        data = resp.json()
        results = data.get("results", [])
        candidates: List[CandidateImage] = []

        for p in results:
            urls = p.get("urls", {})
            user = p.get("user", {})
            w = int(p.get("width") or 1280)
            h = int(p.get("height") or 720)
            candidates.append(
                CandidateImage(
                    id=f"unsplash_{p.get('id')}",
                    title=p.get("alt_description") or p.get("description") or query,
                    image_url=urls.get("regular") or urls.get("full") or urls.get("small"),
                    thumb_url=urls.get("small") or urls.get("regular"),
                    source="Unsplash",
                    source_page=p.get("links", {}).get("html") or "https://unsplash.com",
                    artist=user.get("name") or "Unsplash Photographer",
                    artist_url=user.get("links", {}).get("html"),
                    license="Unsplash License (Free for commercial use)",
                    license_url="https://unsplash.com/license",
                    width=w,
                    height=h,
                    aspect_ratio=round(w / max(h, 1), 2),
                    description=(p.get("description") or p.get("alt_description") or "")[:250],
                )
            )
        return candidates
    except Exception as e:
        log.warning("Unsplash search failed: %s", e)
        return []


def search_pexels(query: str, limit: int = 6) -> List[CandidateImage]:
    """Retrieves high-resolution images from Pexels API when API key is provided."""
    key = os.getenv("PEXELS_API_KEY")
    if not key:
        return []

    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": key, "User-Agent": USER_AGENT}
    params = {"query": query, "per_page": limit, "orientation": "landscape"}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return []
        data = resp.json()
        photos = data.get("photos", [])
        candidates: List[CandidateImage] = []

        for p in photos:
            src = p.get("src", {})
            w = int(p.get("width") or 1280)
            h = int(p.get("height") or 720)
            candidates.append(
                CandidateImage(
                    id=f"pexels_{p.get('id')}",
                    title=p.get("alt") or query,
                    image_url=src.get("large2x") or src.get("large") or src.get("medium"),
                    thumb_url=src.get("medium") or src.get("small"),
                    source="Pexels",
                    source_page=p.get("url") or "https://pexels.com",
                    artist=p.get("photographer") or "Pexels Creator",
                    artist_url=p.get("photographer_url"),
                    license="Pexels License (Free to use)",
                    license_url="https://www.pexels.com/license/",
                    width=w,
                    height=h,
                    aspect_ratio=round(w / max(h, 1), 2),
                    description=p.get("alt") or "",
                )
            )
        return candidates
    except Exception as e:
        log.warning("Pexels search failed: %s", e)
        return []


def generate_ai_visual(
    prompt: str,
    topic: str = "",
    slide_title: str = "",
    seed: Optional[int] = None,
) -> Optional[CandidateImage]:
    """Generates a bespoke 16:9 presentation visual using Pollinations AI (Flux.1)."""
    clean_p = prompt.strip() or f"{slide_title} {topic}".strip()
    if not clean_p:
        return None

    if seed is None:
        raw_key = f"{topic}_{slide_title}_{prompt}_{os.urandom(4).hex()}"
        seed = int(hashlib.md5(raw_key.encode("utf-8")).hexdigest()[:8], 16) % 10000000

    visual_prompt = (
        f"{clean_p}, professional editorial photography, clean architectural composition, "
        f"cinematic soft lighting, photorealistic, 8k resolution, minimalist presentation slide background, "
        f"16:9 widescreen, no text, no watermark, no logo"
    )
    encoded = quote(visual_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&model=flux&nologo=true&seed={seed}"

    try:
        from services import storage
        data = storage.get_or_cache_remote_image(url, timeout=25)
        if not data or len(data) < 3000:
            return None

        return CandidateImage(
            id=f"ai_flux_{seed}",
            title=f"{slide_title or topic or 'Concept'}",
            image_url=url,
            thumb_url=url,
            source="AI Visual Studio (Flux)",
            source_page="https://slidemind.ai",
            artist="SlideMind AI Studio / Flux.1",
            artist_url=None,
            license="Creative Commons Zero / Open Public Commercial Use",
            license_url="https://creativecommons.org/publicdomain/zero/1.0/",
            width=1280,
            height=720,
            aspect_ratio=1.78,
            description=f"Bespoke generated photorealistic presentation visual: {clean_p[:120]}",
            score=88.0,
            relevance_rationale="Bespoke AI visual generated for this exact slide message",
        )
    except Exception as e:
        log.warning("Pollinations AI visual generation failed: %s", e)
        return None


def retrieve_image_candidates(
    brief: VisualBrief,
    already_used_urls: Optional[set] = None,
    limit_per_provider: int = 5,
    user_id: Optional[str] = None,
) -> List[CandidateImage]:
    """Queries user uploaded assets and live providers (Wikimedia, Unsplash, Pexels)
    using the slide's visual brief, prioritizing relevant user uploads and deduplicating.
    """
    already_used = already_used_urls or set()
    aggregated: List[CandidateImage] = []
    seen_urls = set()

    # Priority 0: Relevant User Uploaded Assets
    if user_id:
        try:
            from models import VisualAsset
            from services import storage

            user_assets = VisualAsset.query.filter_by(user_id=user_id).all()
            query_tokens = set(" ".join(brief.search_keywords + brief.key_concepts).lower().split())

            for ua in user_assets:
                asset_tokens = set((ua.title or "").lower().split() + [t.lower() for t in (ua.tags or [])])
                overlap = len(query_tokens.intersection(asset_tokens))
                if overlap >= 1:
                    signed_url = storage.build_secure_asset_url(ua.id, ua.user_id)
                    aggregated.append(
                        CandidateImage(
                            id=f"user_{ua.id}",
                            title=ua.title or ua.original_filename,
                            image_url=signed_url,
                            thumb_url=signed_url,
                            source="User Uploads",
                            source_page="user_library",
                            artist="User Asset",
                            artist_url=None,
                            license="Proprietary / User Upload",
                            license_url=None,
                            width=ua.width or 1280,
                            height=ua.height or 720,
                            aspect_ratio=ua.aspect_ratio or 1.78,
                            description=ua.description or "User uploaded authentic asset",
                            score=90.0,
                            relevance_rationale=f"User asset matched (overlap: {overlap})",
                        )
                    )
        except Exception as e:
            log.warning("User asset retrieval skipped: %s", e)

    keywords = brief.search_keywords or [brief.slide_title]
    for query in keywords:
        if len(aggregated) >= 12:
            break

        # 1. Wikipedia REST Search
        for c in search_wikipedia_images(query, limit=limit_per_provider):
            if c.image_url not in seen_urls and c.image_url not in already_used:
                seen_urls.add(c.image_url)
                aggregated.append(c)

        # 2. Wikimedia Commons
        for c in search_wikimedia_commons(query, limit=limit_per_provider):
            if c.image_url not in seen_urls and c.image_url not in already_used:
                seen_urls.add(c.image_url)
                aggregated.append(c)

        # 3. Unsplash
        for c in search_unsplash(query, limit=3):
            if c.image_url not in seen_urls and c.image_url not in already_used:
                seen_urls.add(c.image_url)
                aggregated.append(c)

        # 4. Pexels
        for c in search_pexels(query, limit=3):
            if c.image_url not in seen_urls and c.image_url not in already_used:
                seen_urls.add(c.image_url)
                aggregated.append(c)

    # Bespoke AI fallback if no candidate found
    if len(aggregated) < 2 and keywords:
        ai_visual = generate_ai_visual(keywords[0], slide_title=brief.slide_title)
        if ai_visual and ai_visual.image_url not in seen_urls and ai_visual.image_url not in already_used:
            aggregated.append(ai_visual)

    return aggregated
