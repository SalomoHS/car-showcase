import logging
import sys
from core.config import settings

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("backend")
uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.setLevel(settings.LOG_LEVEL)
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.setLevel(settings.LOG_LEVEL)

try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    logger.warning("Langfuse not installed. Install with: pip install langfuse")

_langfuse_client = None

def get_langfuse_client():
    global _langfuse_client
    if not LANGFUSE_AVAILABLE:
        return None
    if _langfuse_client is None and settings.LANGFUSE_SECRET_KEY and settings.LANGFUSE_PUBLIC_KEY:
        try:
            _langfuse_client = Langfuse(
                secret_key=settings.LANGFUSE_SECRET_KEY,
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                host=settings.LANGFUSE_BASE_URL,
            )
            logger.info("Langfuse client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Langfuse: {e}")
            return None
    return _langfuse_client
