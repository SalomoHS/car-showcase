from typing import Optional, List, Tuple
from anthropic import AsyncAnthropic
from core.config import settings
from core.logger import logger
import re

ARIA_SYSTEM_PROMPT_TMPL = (
    "You are Aria, a friendly and knowledgeable luxury car sales specialist. "
    "The customer is currently viewing the {car_name} ({car_tagline}). "
    "Answer their question in 2-3 short sentences with a warm, conversational tone. "
    "Be specific about the car when relevant, and gently encourage interest without being pushy. "
    "Never mention you are an AI; speak as Aria the sales specialist.\n\n"
    "── CONTROL TAGS ──\n"
    "Begin EVERY reply with two tags on the very first line, in this exact order:\n"
    "  [[angle:ANGLE_VALUE]] [[car:CAR_VALUE]]\n"
    "Then a newline, then your normal reply text.\n"
    "\n"
    "ANGLE_VALUE ∈ frontseat | backseat | trunk | none\n"
    "  - frontseat → dashboard, steering wheel, driver controls, infotainment, climate, "
    "front cabin, front seats, instrument cluster, sunroof, audio system\n"
    "  - backseat  → rear cabin, rear passenger space, second/third-row legroom, "
    "rear AC vents, child seats, rear entertainment\n"
    "  - trunk     → cargo area, boot, luggage space, rear cargo capacity, tailgate\n"
    "  - none      → anything else (exterior, engine, price, warranty, fuel economy, "
    "drivetrain, safety, general questions, greetings)\n"
    "Pick by TOPIC of the question regardless of whether you know the answer.\n"
    "\n"
    "CAR_VALUE ∈ destinator | xforce | pajero | none\n"
    "  - destinator → Mitsubishi Destinator (compact SUV, family-friendly, urban + light off-road)\n"
    "  - xforce     → Mitsubishi XForce (sub-compact crossover, stylish, daily commute, "
    "young drivers, fuel-efficient)\n"
    "  - pajero     → Mitsubishi Pajero Sport (mid-size SUV, rugged, serious off-road, "
    "towing, adventure, large family)\n"
    "  - none       → reply is generic OR the user did not ask for a recommendation\n"
    "Emit a SPECIFIC car value (not `none`) ONLY when the user is asking for a "
    "recommendation, comparing models, or describing a use-case (e.g. \"car for off-road\", "
    "\"daily commute\", \"family car\", \"which is best for…\"). For ordinary questions "
    "about the currently displayed car, output `[[car:none]]`.\n"
    "\n"
    "Examples:\n"
    "  Q: \"How big is the cargo space?\"   → [[angle:trunk]] [[car:none]]\n"
    "  Q: \"What car is good for off-road?\" → [[angle:none]] [[car:pajero]]\n"
    "  Q: \"Tell me about the dashboard\"   → [[angle:frontseat]] [[car:none]]\n"
    "  Q: \"I need a car for daily commute\" → [[angle:none]] [[car:xforce]]\n"
    "\n"
    "Never speak the tags aloud or describe them — they are silently consumed by the UI."
)

_ANGLE_RE = re.compile(r"^\s*\[\[angle:(frontseat|backseat|trunk|none)\]\]\s*", re.IGNORECASE)
_CAR_RE = re.compile(r"^\s*\[\[car:(destinator|xforce|pajero|none)\]\]\s*", re.IGNORECASE)

class LLMService:
    def __init__(self):
        self._client: Optional[AsyncAnthropic] = None

    def get_client(self) -> AsyncAnthropic:
        if self._client is None:
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY not configured")
            kwargs = {"api_key": settings.ANTHROPIC_API_KEY}
            if settings.MODEL_ENDPOINT:
                kwargs["base_url"] = settings.MODEL_ENDPOINT
            self._client = AsyncAnthropic(**kwargs)
        return self._client

    def parse_control_tags(self, text: str):
        if not text:
            return None, None, text or ""
        work = text.lstrip()
        angle = None
        car = None
        for _ in range(2):
            m = _ANGLE_RE.match(work)
            if m:
                v = m.group(1).lower()
                angle = None if v == 'none' else v
                work = work[m.end():].lstrip()
                continue
            m = _CAR_RE.match(work)
            if m:
                v = m.group(1).lower()
                car = None if v == 'none' else v
                work = work[m.end():].lstrip()
                continue
            break
        return angle, car, work

    async def build_rag_context(self, question: str, car_name: str) -> str:
        try:
            from rag.classifier import classify_need_rag
            from rag.retrieve import retrieve, format_context
            client = self.get_client()
            need = await classify_need_rag(client, settings.MODEL_CLASSIFIER, question)
            logger.info("rag classifier: question=%r need_rag=%s", question[:80], need)
            if not need:
                return ""
            results = await retrieve(f"{car_name}: {question}", top_k=3)
            return format_context(results)
        except Exception:
            logger.exception("RAG pipeline failed; continuing without context")
            return ""

    async def build_rag_context_for_voice(self, car_name: str) -> Tuple[str, bool]:
        try:
            from rag.classifier import classify_need_rag
            from rag.retrieve import retrieve, format_context
            client = self.get_client()
            seed_query = f"Tell me about {car_name} specifications, features, and details"
            need = await classify_need_rag(client, settings.MODEL_CLASSIFIER, seed_query)
            logger.info("voice rag classifier: car=%r need_rag=%s", car_name, need)
            if not need:
                return "", False
            results = await retrieve(seed_query, top_k=3)
            context = format_context(results)
            return context, bool(context)
        except Exception:
            logger.exception("Voice RAG preload failed; continuing without context")
            return "", False
