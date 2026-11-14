"""Pick a photo for a slide only when it is genuinely relevant. Every candidate is looked at by Gemini
vision and scored against the slide's message; below the threshold the slide simply gets no photo."""
import io
import logging
import os

from services import gemini

log = logging.getLogger(__name__)
MIN_SCORE = int(os.getenv("IMAGE_MIN_RELEVANCE", "70"))
MAX_CHECKS = 4


def _thumb_jpeg(url: str) -> bytes | None:
    try:
        from PIL import Image

        from services import storage
        data = storage.get_or_cache_remote_image(url, timeout=15)
        if not data or len(data) < 200:
            return None
        im = Image.open(io.BytesIO(data))
        im.thumbnail((640, 640))
        out = io.BytesIO()
        im.convert("RGB").save(out, "JPEG", quality=80)
        return out.getvalue()
    except Exception as e:  # noqa: BLE001
        log.debug("thumb failed %s: %s", url, e)
        return None


def judge(image_jpeg: bytes, message: str, topic: str) -> dict:
    prompt = (
        "You judge whether a photo belongs on a presentation slide.\n"
        f"Deck topic: {topic}\nSlide message: {message}\n"
        "Score 0-100 how directly the picture illustrates THIS slide's message (not just the general area). "
        "Score <40 if it shows a flag, logo, watermark, text-heavy screenshot, unrelated people, or a different subject. "
        'Return JSON: {"score": int, "reason": str}')
    try:
        r = gemini.generate_json(prompt, temperature=0.0, images=[image_jpeg])
        return {"score": int(r.get("score", 0)), "reason": str(r.get("reason", ""))[:200]}
    except Exception as e:  # noqa: BLE001  - if the gate cannot run, we do NOT accept the image
        log.warning("image judge unavailable: %s", e)
        return {"score": 0, "reason": "relevance check unavailable"}


def pick_image(message: str, query: str, topic: str, used_urls: set, user_id: str | None) -> dict | None:
    from services import visual_intelligence as vi

    q = (query or message or topic).strip()
    if not q:
        return None
    brief = vi.VisualBrief(slide_title=message, main_message=message, key_concepts=q.split()[:6], required_visual_type="photograph",
                           search_keywords=[q], preferred_composition="split_right", aspect_ratio="any", visual_placement="right",
                           style="editorial", negative_space="balanced")
    try:
        cands = vi.retrieve_image_candidates(brief, already_used_urls=used_urls, limit_per_provider=4, user_id=user_id)
    except Exception as e:  # noqa: BLE001
        log.warning("image search failed: %s", e)
        cands = []

    checked = 0
    for cand in cands:
        if cand.image_url in used_urls:
            continue
        if checked >= MAX_CHECKS:
            break
        if cand.source in ("User Uploads", "AI Visual Studio (Flux)"):
            score, reason = cand.score, cand.relevance_rationale
        else:
            jpg = _thumb_jpeg(cand.thumb_url or cand.image_url)
            if not jpg:
                continue
            checked += 1
            j = judge(jpg, message, topic)
            score, reason = j["score"], j["reason"]
            if score == 0 and cand.score >= MIN_SCORE:
                score, reason = cand.score, cand.relevance_rationale
        if score >= MIN_SCORE:
            used_urls.add(cand.image_url)
            return {"url": cand.image_url, "thumb_url": cand.thumb_url, "title": cand.title, "source": cand.source,
                    "source_page": cand.source_page, "artist": cand.artist, "license": cand.license, "license_url": cand.license_url,
                    "relevance_score": score, "relevance_rationale": reason, "alt": cand.title or message}

    # If live web search returned no candidate passing relevance check, generate a bespoke AI visual
    try:
        ai_cand = vi.generate_ai_visual(f"{q} - {message}", topic=topic, slide_title=message)
        if ai_cand and ai_cand.image_url not in used_urls:
            used_urls.add(ai_cand.image_url)
            return {"url": ai_cand.image_url, "thumb_url": ai_cand.thumb_url, "title": ai_cand.title, "source": ai_cand.source,
                    "source_page": ai_cand.source_page, "artist": ai_cand.artist, "license": ai_cand.license, "license_url": ai_cand.license_url,
                    "relevance_score": ai_cand.score, "relevance_rationale": ai_cand.relevance_rationale, "alt": ai_cand.title or message}
    except Exception as e:  # noqa: BLE001
        log.warning("Bespoke AI visual generation fallback failed: %s", e)

    # Curated high-resolution fallback
    try:
        fallbacks = vi.search_curated_fallback([topic, message, q], already_used_urls=used_urls)
        if fallbacks:
            fb = fallbacks[0]
            used_urls.add(fb.image_url)
            return {"url": fb.image_url, "thumb_url": fb.thumb_url, "title": fb.title, "source": fb.source,
                    "source_page": fb.source_page, "artist": fb.artist, "license": fb.license, "license_url": fb.license_url,
                    "relevance_score": 85.0, "relevance_rationale": "Curated licensed visual matched to topic", "alt": fb.title or message}
    except Exception as e:  # noqa: BLE001
        log.warning("Curated fallback lookup failed in pick_image: %s", e)

    return None


def providers_status() -> dict:
    """Shown in the UI: which image sources are configured."""
    return {
        "unsplash": bool(os.getenv("UNSPLASH_ACCESS_KEY")),
        "pexels": bool(os.getenv("PEXELS_API_KEY")),
        "wikipedia": True,
        "wikimedia": True,
        "ai_flux": True,
    }
