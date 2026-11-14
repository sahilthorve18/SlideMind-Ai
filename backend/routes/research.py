"""Standalone web research endpoint."""
from flask import Blueprint, current_app

from services import gemini
from utils.http import fail, json_body, ok, require_auth

bp = Blueprint("research", __name__, url_prefix="/api")


@bp.post("/research")
@require_auth
def do_research():
    data, err = json_body({"query": str})
    if err:
        return err
    q = data["query"].strip()
    if not (2 <= len(q) <= 500):
        return fail("invalid_request", "Query must be 2-500 characters.")
    if not current_app.config.get("GEMINI_API_KEY"):
        return fail("ai_not_configured", "The AI service is not configured (missing GEMINI_API_KEY).", 503)

    from google.genai import types

    try:
        client = gemini._client()
        
        def _call():
            return client.models.generate_content(
                model=gemini.get_model_candidates()[0],
                contents=(
                    "Research this topic and provide a factual, dated summary with key bullet points, statistics, and citations.\n\n"
                    f"Question: {q}"
                ),
                config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())], temperature=0.2),
            )
        
        resp = gemini._call_with_retry(_call, max_retries=2, base_delay=1.5)
        sources = []
        for cand in getattr(resp, "candidates", []) or []:
            meta = getattr(cand, "grounding_metadata", None)
            if meta:
                for chunk in getattr(meta, "grounding_chunks", []) or []:
                    web = getattr(chunk, "web", None)
                    if web and getattr(web, "uri", None):
                        sources.append({"title": getattr(web, "title", "Web source"), "url": web.uri})

        return ok({"query": q, "content": resp.text or "", "sources": sources})
    except gemini.GeminiRateLimitError as e:
        return fail("rate_limit_exceeded", str(e), 429, {"retry_after": 60})
    except gemini.GeminiError as e:
        return fail("ai_unavailable", str(e), 502)
    except Exception as e:
        return fail("research_failed", str(e), 500)
