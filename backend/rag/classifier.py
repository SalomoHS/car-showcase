"""Tiny RAG-need classifier — single Anthropic call with max_tokens=4.

Returns True if the user's question likely needs to look up specific factual
specs (e.g., dimensions, prices, features) from the knowledge base, False if
it can be answered from generic conversation context.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

CLASSIFIER_SYSTEM = (
    "You decide if a sales question needs a knowledge-base lookup. "
    "Reply with exactly one word: true or false.\n"
    "Reply 'true' for questions about specific car specs, features, dimensions, "
    "pricing, fuel economy, options, trim differences, safety equipment, towing "
    "capacity, warranty terms, available colors, dealer locations, or any factual "
    "detail that varies by model.\n"
    "Reply 'false' for greetings, chitchat, opinions, comparisons of generic "
    "categories, or follow-ups that can be answered from earlier conversation."
)


async def classify_need_rag(anthropic_client, model: str, question: str) -> bool:
    """Returns True if RAG retrieval should be invoked. Defaults to False on any error."""
    q = (question or "").strip()
    if not q:
        return False
    try:
        resp = await anthropic_client.messages.create(
            model=model,
            max_tokens=4,
            system=CLASSIFIER_SYSTEM,
            messages=[{"role": "user", "content": q[:1000]}],
        )
        parts = []
        for block in resp.content or []:
            btype = getattr(block, "type", None) or (block.get("type") if isinstance(block, dict) else None)
            if btype == "text":
                parts.append(getattr(block, "text", None) or (block.get("text") if isinstance(block, dict) else ""))
        text = ("".join(parts)).strip().lower()
        return text.startswith("true")
    except Exception:
        logger.exception("classifier failed; defaulting need_rag=False")
        return False
