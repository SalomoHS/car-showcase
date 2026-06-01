import sys
import logging
from core.config import settings
from core.logger import logger, session_id_var

print("Logger loaded successfully!")
session_id_var.set("test-stream-override")
logger.info("This is a test message to CloudWatch!")
