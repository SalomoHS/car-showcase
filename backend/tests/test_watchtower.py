import logging
import contextvars
import boto3
import watchtower

session_id_var = contextvars.ContextVar("session_id", default="default-stream")

class SessionIdFilter(logging.Filter):
    def filter(self, record):
        record.session_id = session_id_var.get()
        return True

cw_handler = watchtower.CloudWatchLogHandler(
    log_group_name="virtual-dealer-logs",
    log_stream_name="{session_id}",
    boto3_client=boto3.client("logs", region_name="us-east-1")
)
cw_handler.addFilter(SessionIdFilter())

logger = logging.getLogger("test_cw")
logger.setLevel(logging.INFO)
logger.addHandler(cw_handler)

session_id_var.set("uuid-1234")
logger.info("Log in stream uuid-1234")

session_id_var.set("uuid-5678")
logger.info("Log in stream uuid-5678")
