import logging
import sys
import watchtower
import boto3

class MyFilter(logging.Filter):
    def filter(self, record):
        record.session_id = "test-session"
        return True

cw = watchtower.CloudWatchLogHandler(
    log_group_name="test",
    log_stream_name="{session_id}",
    send_interval=1,
    boto3_client=boto3.client("logs", region_name="us-east-1")
)
cw.addFilter(MyFilter())

logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)
logger.addHandler(cw)

logger.info("Hello")
