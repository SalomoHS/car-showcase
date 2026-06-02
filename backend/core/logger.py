import logging
import sys
import boto3
import watchtower
import contextvars
from core.config import settings

session_id_var = contextvars.ContextVar("session_id")

class SessionIdFilter(logging.Filter):
    def filter(self, record):
        record.session_id = session_id_var.get()
        return True

class DynamicCloudWatchLogHandler(watchtower.CloudWatchLogHandler):
    def _get_stream_name(self, record):
        return getattr(record, "session_id")

# Initialize Boto3 CloudWatch client using settings
try:
    boto3_client = boto3.client(
        'logs',
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )
    
    cw_handler = DynamicCloudWatchLogHandler(
        log_group_name="virtual-dealer-logs",
        boto3_client=boto3_client
    )
    cw_handler.addFilter(SessionIdFilter())
    cw_formatter = logging.Formatter('[%(levelname)s] | %(asctime)s | %(name)s | %(message)s')
    cw_handler.setFormatter(cw_formatter)
    handlers = [logging.StreamHandler(sys.stdout), cw_handler]
except Exception as e:
    handlers = [logging.StreamHandler(sys.stdout)]
    print(f"Failed to initialize CloudWatch logging: {e}", file=sys.stderr)

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
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
