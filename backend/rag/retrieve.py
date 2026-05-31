"""S3 Vectors + Gemini embeddings retrieval module.

Adapted from the user-provided snippet. Synchronous boto3/genai calls are wrapped
in `asyncio.to_thread()` for use from the async FastAPI handlers.

Env vars (set in /app/backend/.env):
  GEMINI_API_KEY              — Google AI Studio key
  GEMINI_EMBED_MODEL          — default "models/gemini-embedding-2"
  AWS_REGION                  — default "ap-southeast-1"
  S3_VECTOR_BUCKET_NAME       — S3 Vectors bucket
  S3_VECTOR_INDEX_NAME        — index name inside that bucket
  S3_VECTOR_DIMENSION         — embedding dim (3072 for gemini-embedding-2)
  S3_PAYLOAD_BUCKET_NAME      — regular S3 bucket holding the source text payloads
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ──────────────────────── Config ────────────────────────
AWS_REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "ap-southeast-1"
AWS_PROFILE = os.environ.get("AWS_PROFILE")
S3_VECTOR_BUCKET_NAME = os.environ.get("S3_VECTOR_BUCKET_NAME", "virtual-dealer-prod")
S3_VECTOR_INDEX_NAME = os.environ.get("S3_VECTOR_INDEX_NAME", "cars-index")
S3_VECTOR_DIMENSION = int(os.environ.get("S3_VECTOR_DIMENSION", "3072"))
S3_PAYLOAD_BUCKET_NAME = os.environ.get("S3_PAYLOAD_BUCKET_NAME", "virtual-dealer-cars-rag-prod")
GEMINI_EMBED_MODEL = os.environ.get("GEMINI_EMBED_MODEL", "models/gemini-embedding-2")

# ──────────────────────── Lazy-init singletons ────────────────────────
_genai_configured = False
_s3v_client = None
_s3_client = None


def _configure_genai() -> None:
    global _genai_configured
    if _genai_configured:
        return
    import google.generativeai as genai  # type: ignore
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not configured")
    genai.configure(api_key=api_key)
    _genai_configured = True


def _get_s3vectors_client():
    global _s3v_client
    if _s3v_client is None:
        import boto3
        session = (
            boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
            if AWS_PROFILE else boto3.Session(region_name=AWS_REGION)
        )
        _s3v_client = session.client("s3vectors", region_name=AWS_REGION)
    return _s3v_client


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        import boto3
        session = (
            boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
            if AWS_PROFILE else boto3.Session(region_name=AWS_REGION)
        )
        _s3_client = session.client("s3")
    return _s3_client


# ──────────────────────── Sync core (runs in a thread) ────────────────────────
def _embed_query_gemini_sync(query: str) -> List[float]:
    _configure_genai()
    import google.generativeai as genai  # type: ignore
    resp = genai.embed_content(
        model=GEMINI_EMBED_MODEL,
        content=query,
        task_type="retrieval_document",
    )
    emb = resp.get("embedding") if isinstance(resp, dict) else getattr(resp, "embedding", None)
    if emb is None:
        raise RuntimeError("Embedding response empty")
    return [float(x) for x in emb]


def _fetch_text_sync(text_key: str) -> str:
    try:
        s3 = _get_s3_client()
        resp = s3.get_object(Bucket=S3_PAYLOAD_BUCKET_NAME, Key=text_key)
        return resp["Body"].read().decode("utf-8")
    except Exception as e:
        logger.warning("S3 fetch failed key=%s err=%s", text_key, e)
        return ""


def _retrieve_sync(query: str, top_k: int = 5, filters: Optional[dict] = None) -> List[Dict[str, Any]]:
    vector = _embed_query_gemini_sync(query)
    if len(vector) != S3_VECTOR_DIMENSION:
        raise RuntimeError(f"Embedding dimension mismatch: got {len(vector)} expected {S3_VECTOR_DIMENSION}")

    client = _get_s3vectors_client()
    req: Dict[str, Any] = {
        "vectorBucketName": S3_VECTOR_BUCKET_NAME,
        "indexName": S3_VECTOR_INDEX_NAME,
        "queryVector": {"float32": vector},
        "topK": top_k,
        "returnMetadata": True,
    }
    resp = client.query_vectors(**req)
    vectors = resp.get("vectors") or []

    results: List[Dict[str, Any]] = []
    for vec in vectors:
        key = vec.get("key", "")
        metadata = vec.get("metadata") or {}
        text_key = metadata.get("text_key", f"{key}.json")
        text = _fetch_text_sync(text_key)
        results.append({
            "key": key,
            "distance": vec.get("distance", 0.0),
            "metadata": metadata,
            "text": text,
        })
    return results


# ──────────────────────── Public async API ────────────────────────
async def retrieve(query: str, top_k: int = 5, filters: Optional[dict] = None) -> List[Dict[str, Any]]:
    """Async wrapper around the sync retrieval; safe to call from FastAPI handlers."""
    return await asyncio.to_thread(_retrieve_sync, query, top_k, filters)


def format_context(results: List[Dict[str, Any]], max_chars: int = 4000) -> str:
    """Format retrieved chunks into a context block for the system prompt."""
    if not results:
        return ""
    out_parts: List[str] = []
    used = 0
    for i, r in enumerate(results, 1):
        body = (r.get("text") or "").strip()
        if not body:
            continue
        snippet = f"[doc {i}] {body}".strip()
        if used + len(snippet) > max_chars:
            snippet = snippet[: max_chars - used]
            out_parts.append(snippet)
            break
        out_parts.append(snippet)
        used += len(snippet) + 2
    return "\n\n".join(out_parts)
