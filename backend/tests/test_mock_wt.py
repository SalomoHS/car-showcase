import logging
import sys

class MockWatchtowerHandler(logging.Handler):
    def emit(self, record):
        print(f"Emit called! dict: {record.__dict__}")
        stream_name = "{session_id}".format(**record.__dict__)
        print("Stream:", stream_name)

class SessionIdFilter(logging.Filter):
    def filter(self, record):
        record.session_id = "mock-session"
        return True

h = MockWatchtowerHandler()
h.addFilter(SessionIdFilter())

logging.basicConfig(handlers=[h], level=logging.DEBUG)

logging.getLogger("test").debug("Hello %s", "World")
