import asyncio
import os
import sys

# add parent dir to path so we can import backend.server
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from dotenv import load_dotenv
load_dotenv("backend/.env")

async def test():
    from backend.core.logger import get_langfuse_client
    from langfuse.types import TraceContext
    import uuid

    langfuse = get_langfuse_client()
    session_id = f"test-voice-{uuid.uuid4().hex[:4]}"
    
    ctx = TraceContext(session_id=session_id, user_id="car-123")
    
    trace = langfuse.start_observation(
        name="voice-chat-test",
        trace_context=ctx,
        input={"message": "hello voice"},
        metadata={"mode": "voice"}
    )
    
    gen = trace.start_observation(
        name="voice-generation",
        as_type="generation",
        model="test-model",
        input=[{"role": "user", "content": "hello voice"}],
        output="hi there",
    )
    gen.end()
    
    trace.update(output={"response": "hi there"})
    trace.end()
    langfuse.flush()
    print("Done flushing!")

if __name__ == "__main__":
    asyncio.run(test())
