import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from dotenv import load_dotenv
load_dotenv("backend/.env")

async def test():
    from backend.core.logger import get_langfuse_client
    from langfuse import propagate_attributes
    import uuid

    langfuse = get_langfuse_client()
    session_id = f"test-ctx-{uuid.uuid4().hex[:4]}"
    
    with propagate_attributes(session_id=session_id):
        with langfuse.start_as_current_observation(as_type="span", name="chat-session-root") as root_span:
            root_span.update(input={"message": "hello context"})
            root_span.update(metadata={"mode": "text"})
            
            with langfuse.start_as_current_observation(as_type="generation", name="chat-generation") as gen:
                gen.update(input=[{"role": "user", "content": "hello context"}])
                await asyncio.sleep(0.1)
                gen.update(output="hi back from gen")
                
            root_span.update(output={"response": "hi back from root"})
            
    langfuse.flush()
    print("Done context test!")

if __name__ == "__main__":
    asyncio.run(test())
