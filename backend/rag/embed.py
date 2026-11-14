"""Gemini embeddings (normalised, fixed dimension)."""
import logging
import math

from flask import current_app

from services import gemini

log = logging.getLogger(__name__)

EMBED_DIM = 768
BATCH = 100


class EmbeddingError(Exception):
    pass


def _normalize(vec):
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed_texts(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """Embed texts. Raises GeminiNotConfigured or EmbeddingError; never returns fake vectors."""
    from google.genai import errors, types

    client = gemini._client()
    model = current_app.config.get("EMBEDDING_MODEL", "gemini-embedding-001")
    out: list[list[float]] = []
    for i in range(0, len(texts), BATCH):
        batch = texts[i : i + BATCH]
        try:
            resp = client.models.embed_content(
                model=model,
                contents=batch,
                config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=EMBED_DIM),
            )
        except errors.APIError as e:
            log.warning("Embedding API error: %s", e)
            raise EmbeddingError("The embedding service returned an error.") from e
        except Exception as e:
            log.exception("Embedding call failed")
            raise EmbeddingError("Could not reach the embedding service.") from e
        vectors = [_normalize(list(e.values)) for e in resp.embeddings]
        if len(vectors) != len(batch):
            raise EmbeddingError("The embedding service returned an unexpected result.")
        out.extend(vectors)
    return out
