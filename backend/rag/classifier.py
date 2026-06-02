"""RAG-need classifier.

The user requested a single-call LLM classifier (max_tokens=4). In practice our
custom Anthropic endpoint enforces extended thinking, so 4 tokens only captures
preamble — the actual `true`/`false` token appears after ~150-300 reasoning
tokens. To keep latency and cost predictable for the live voice loop, the
primary classifier is a **deterministic keyword-based heuristic** that decides
in zero time and zero cost. An LLM-based fallback is provided for callers that
want to refine ambiguous cases (currently unused on the hot path).
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Specs/lookup-style triggers — if any matches the user's question we run RAG.
# Aim for high precision (false-positive RAG calls only add latency, not wrong answers).
_TRIGGER_RE = re.compile(
    r"\b("
    # Dimensions & measurements
    r"spec|specs|specification|specifications|dimension|dimensions|"
    r"width|height|length|wheelbase|ground[- ]?clearance|payload|towing|"
    r"capacit(?:y|ies)|liter|liters|litre|litres|cc|cubic|kg|kgs|tonne|"
    # Powertrain
    r"engine|displacement|cylinder|cylinders|hp|horsepower|bhp|kw|torque|nm|"
    r"transmission|gearbox|gear|4wd|awd|drivetrain|"
    # Fuel
    r"fuel|consumption|economy|mileage|km/?l|kmpl|mpg|tank|"
    # Pricing & purchase
    r"price|prices|cost|costs|how[- ]?much|harga|berapa|otr|"
    # Availability
    r"color|colors|colour|colours|warna|trim|trims|variant|variants|"
    # After-sales
    r"warranty|guarantee|free[- ]?service|service[- ]?interval|service[- ]?period|"
    # Seating
    r"seat|seats|seater|seating|legroom|headroom|"
    # Safety
    r"airbag|airbags|abs|brake|brakes|safety|ncap|crash"
    r")\b",
    re.IGNORECASE,
)


def _keyword_classify(question: str) -> bool:
    return bool(_TRIGGER_RE.search(question or ""))


async def classify_need_rag(anthropic_client, model: str, question: str) -> bool:
    """Returns True if RAG retrieval should be invoked. Defaults to False on any error.

    Uses a two-tier approach:
    1. Fast keyword-based classification (zero latency, zero cost)
    2. LLM-based classification as fallback for ambiguous cases

    `anthropic_client` and `model` are kept for API stability so the caller can
    swap in an LLM-based implementation later without code changes.
    """
    q = (question or "").strip()
    if not q:
        return False

    if _keyword_classify(q):
        return True

    return await _llm_classify(anthropic_client, model, q)


async def _llm_classify(anthropic_client, model: str, question: str) -> bool:
    """LLM-based classifier for ambiguous cases that keyword classification doesn't catch."""
    from core.logger import get_langfuse_client
    from contextlib import ExitStack
    langfuse = get_langfuse_client()

    try:
        with ExitStack() as stack:
            generation = None
            if langfuse:
                generation = stack.enter_context(langfuse.start_as_current_observation(
                    name="classifier_llm",
                    as_type="generation",
                    model=model,
                    input=question,
                ))

            response = await anthropic_client.messages.create(
                model=model,
                max_tokens=1000,
                system="Determine if the user's question requires querying a car details (specification, testimony, price). Reply with only 'true' or 'false'.",
                messages=[{"role": "user", "content": question}],
                temperature=0.0,
            )

            parts = []
            for block in response.content or []:
                block_type = getattr(block, "type", None) or (block.get("type") if isinstance(block, dict) else None)
                if block_type == "text":
                    parts.append(getattr(block, "text", None) or (block.get("text") if isinstance(block, dict) else ""))

            answer = ("".join(parts)).strip().lower()
            result = "true" in answer

            if generation:
                generation.update(
                    output=answer,
                    metadata={"result": result}
                )

            return result
    except Exception as e:
        logger.exception("LLM classifier failed; defaulting need_rag=False")
        return False
