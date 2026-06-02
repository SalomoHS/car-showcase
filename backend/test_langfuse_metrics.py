#!/usr/bin/env python3
"""
Test script for Langfuse Metrics Service.
Verifies the service can fetch metrics from Langfuse API and push to CloudWatch.
"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

def check_env():
    print("=" * 60)
    print("Checking Environment Variables")
    print("=" * 60)
    
    required = [
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_BASE_URL",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_REGION",
    ]
    
    all_ok = True
    for var in required:
        value = os.environ.get(var)
        status = "✓ Set" if value else "✗ Missing"
        print(f"  {var}: {status}")
        if not value:
            all_ok = False
    
    print()
    if not all_ok:
        print("❌ ERROR: Missing required environment variables")
        return False
    print("✓ All required environment variables are set")
    return True


async def test_metrics_fetch():
    print("\n" + "=" * 60)
    print("Testing Langfuse Metrics Fetch")
    print("=" * 60)
    
    from services.langfuse_metrics import LangfuseMetricsService
    
    service = LangfuseMetricsService()
    
    try:
        print("\n1. Fetching traces from Langfuse API...")
        from datetime import datetime, timezone, timedelta
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
        
        traces = await service._fetch_traces(start_time, end_time)
        trace_count = len(traces.get("data", []))
        print(f"   ✓ Fetched {trace_count} traces")
        
        print("\n2. Fetching generations from Langfuse API...")
        generations = await service._fetch_generations(start_time, end_time)
        gen_count = len(generations.get("data", []))
        print(f"   ✓ Fetched {gen_count} generations")
        
        print("\n3. Calculating costs...")
        test_cost = service._calculate_anthropic_cost("claude-sonnet-4.6", 1000, 500)
        print(f"   ✓ Sample cost calculation (1000 in + 500 out tokens): ${test_cost:.6f}")
        
        print("\n4. Full metrics fetch and CloudWatch push...")
        result = await service.fetch_and_push_metrics()
        
        if result.get("success"):
            print("   ✓ Metrics pushed to CloudWatch successfully")
            for name, value, unit in result.get("metrics", []):
                print(f"     - {name}: {value} {unit}")
        else:
            print(f"   ✗ Failed: {result.get('error')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await service.close()


async def main():
    print("\n" + "=" * 60)
    print("Langfuse Metrics Service Test")
    print("=" * 60)
    
    if not check_env():
        exit(1)
    
    if await test_metrics_fetch():
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Start the metrics scheduler: python run_langfuse_metrics.py")
        print("2. Or use Docker: docker-compose up -d langfuse-metrics")
        print("3. Check CloudWatch console for LangfuseMetrics namespace")
        print("4. Import cloudwatch-dashboard.json to add Langfuse widgets")
    else:
        print("\n" + "=" * 60)
        print("❌ Tests failed. Check the errors above.")
        print("=" * 60)
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())