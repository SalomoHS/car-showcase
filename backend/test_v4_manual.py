import os, sys, time
from dotenv import load_dotenv

load_dotenv("backend/.env")

try:
    from langfuse import Langfuse
    from langfuse.types import TraceContext
    print("Initializing...")
    langfuse = Langfuse()
    
    ctx = TraceContext(session_id="test-session-v4")
    
    print("Starting trace...")
    trace = langfuse.start_observation(
        name="test-trace-manual",
        trace_context=ctx,
        input={"hello": "world"}
    )
    
    print("Starting generation...")
    gen = trace.start_observation(
        name="test-gen-manual",
        as_type="generation",
        model="gpt-test",
        input=[{"role": "user", "content": "hi"}]
    )
    
    print("Updating generation...")
    gen.update(output="hello back")
    # In v4, we need to end the observation
    if hasattr(gen, 'end'):
        print("calling gen.end()")
        gen.end()
    
    if hasattr(trace, 'update'):
        trace.update(output={"success": True})
    if hasattr(trace, 'end'):
        print("calling trace.end()")
        trace.end()
        
    print("Flushing...")
    if hasattr(langfuse, 'flush'):
        langfuse.flush()
    print("Done")
except Exception as e:
    print(f"Error: {e}")
