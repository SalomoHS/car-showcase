#!/usr/bin/env python3
"""
Test script to verify Langfuse connection and logging with v4.7.1 API.
Run this to ensure Langfuse is properly configured.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

LANGFUSE_SECRET_KEY = os.environ.get('LANGFUSE_SECRET_KEY')
LANGFUSE_PUBLIC_KEY = os.environ.get('LANGFUSE_PUBLIC_KEY')
LANGFUSE_BASE_URL = os.environ.get('LANGFUSE_BASE_URL', 'https://cloud.langfuse.com')

print("=" * 60)
print("Langfuse Connection Test (v4.7.1)")
print("=" * 60)

# Check if credentials are set
print(f"\n1. Checking credentials...")
print(f"   Secret Key: {'✓ Set' if LANGFUSE_SECRET_KEY else '✗ Missing'}")
print(f"   Public Key: {'✓ Set' if LANGFUSE_PUBLIC_KEY else '✗ Missing'}")
print(f"   Base URL: {LANGFUSE_BASE_URL}")

if not LANGFUSE_SECRET_KEY or not LANGFUSE_PUBLIC_KEY:
    print("\n❌ ERROR: Langfuse credentials are not set in .env file")
    exit(1)

# Try to import Langfuse
print(f"\n2. Importing Langfuse...")
try:
    from langfuse import Langfuse
    print("   ✓ Langfuse imported successfully")
except ImportError as e:
    print(f"   ✗ Failed to import: {e}")
    print("\n   Install with: pip install langfuse")
    exit(1)

# Try to initialize Langfuse
print(f"\n3. Initializing Langfuse client...")
try:
    langfuse = Langfuse(
        secret_key=LANGFUSE_SECRET_KEY,
        public_key=LANGFUSE_PUBLIC_KEY,
        host=LANGFUSE_BASE_URL,
    )
    print("   ✓ Client initialized successfully")
except Exception as e:
    print(f"   ✗ Failed to initialize: {e}")
    exit(1)

# Try to create a test trace with NEW API
print(f"\n4. Creating test trace with NEW API...")
try:
    trace = langfuse.trace(
        name="test-trace",
        session_id="test-session-123",
        user_id="test-user",
        input={"test": "input"},
        metadata={
            "test": True,
            "source": "test_langfuse.py",
            "api_version": "v4.7.1",
        },
    )
    print("   ✓ Trace created successfully")
    print(f"   → Trace ID: {trace.id}")
except Exception as e:
    print(f"   ✗ Failed to create trace: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Try to create a generation with NEW API
print(f"\n5. Creating test generation with NEW API...")
try:
    generation = trace.generation(
        name="test-generation",
        model="test-model",
        input=[{"role": "user", "content": "Hello, this is a test"}],
        output="This is a test response",
        metadata={
            "test": True,
        },
    )
    # End the generation to record usage
    generation.end(
        usage={"input": 10, "output": 5, "total": 15}
    )
    print("   ✓ Generation created successfully")
    print(f"   → Generation ID: {generation.id}")
except Exception as e:
    print(f"   ✗ Failed to create generation: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Update trace with output
print(f"\n6. Updating trace with output...")
try:
    trace.update(
        output={"test": "output", "success": True},
    )
    print("   ✓ Trace updated successfully")
except Exception as e:
    print(f"   ✗ Failed to update trace: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test session continuity (chat + voice)
print(f"\n7. Testing session continuity (chat + voice)...")
try:
    session_id = "test-session-continuity-123"
    
    # Simulate text chat
    text_trace = langfuse.trace(
        name="chat-text",
        session_id=session_id,
        input={"message": "Tell me about this car"},
        metadata={"mode": "text", "car_name": "Mitsubishi Destinator"},
    )
    text_gen = text_trace.generation(
        name="text-generation",
        model="claude-sonnet-4.6",
        input=[{"role": "user", "content": "Tell me about this car"}],
        output="This is a great car with excellent features!",
    )
    text_gen.end(usage={"input": 20, "output": 15, "total": 35})
    print("   ✓ Text chat logged")
    
    # Simulate voice chat (same session!)
    voice_trace = langfuse.trace(
        name="voice-chat",
        session_id=session_id,  # Same session_id!
        input={"message": "What about the engine?"},
        metadata={"mode": "voice", "car_name": "Mitsubishi Destinator"},
    )
    voice_gen = voice_trace.generation(
        name="voice-generation",
        model="claude-sonnet-4.6",
        input=[{"role": "user", "content": "What about the engine?"}],
        output="The engine is powerful and fuel-efficient!",
    )
    voice_gen.end(usage={"input": 15, "output": 12, "total": 27})
    print("   ✓ Voice chat logged")
    print(f"   → Both traces share session: {session_id}")
except Exception as e:
    print(f"   ✗ Failed to test session continuity: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "=" * 60)
print("✅ All tests passed!")
print("=" * 60)
print("\nKey changes in v4.7.1:")
print("  • trace() returns a trace object (no need for manual trace_id)")
print("  • trace.generation() creates generation under trace")
print("  • generation.end() to finalize with usage")
print("  • trace.update() to update trace output")
print("  • No manual flush() needed (auto-batched)")
print("\nYou should now see test traces in your Langfuse dashboard at:")
print(f"  {LANGFUSE_BASE_URL}")
print("\nLook for:")
print("  - Session ID: test-session-123 (single trace)")
print("  - Session ID: test-session-continuity-123 (chat + voice)")
print("  - Trace names: test-trace, chat-text, voice-chat")
print("\nIf you don't see them, wait a few seconds and refresh the page.")
print("\nNext steps:")
print("  1. Start your server: uvicorn server:app --reload --port 8000")
print("  2. Check server logs for: 'Langfuse client initialized successfully'")
print("  3. Make a chat request to /api/chat-text")
print("  4. Make a voice request to /agora/start")
print("  5. Verify both chat and voice appear in the SAME session!")
print("=" * 60)
