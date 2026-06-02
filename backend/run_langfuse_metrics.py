import os
import asyncio
import logging
import signal
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

from services.langfuse_metrics import LangfuseMetricsService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("langfuse-metrics-scheduler")

POLL_INTERVAL_SECONDS = int(os.environ.get("LANGFUSE_METRICS_INTERVAL", "300"))

async def run_scheduler():
    service = LangfuseMetricsService()
    logger.info(f"Langfuse metrics scheduler started. Polling every {POLL_INTERVAL_SECONDS} seconds.")
    
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        stop_event.set()
    
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            pass
    
    try:
        while not stop_event.is_set():
            try:
                result = await service.fetch_and_push_metrics()
                if result.get("success"):
                    logger.info(f"Metrics pushed successfully")
                else:
                    logger.warning(f"Metrics push failed: {result.get('error')}")
            except Exception as e:
                logger.exception("Error in metrics fetch cycle")
            
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=POLL_INTERVAL_SECONDS)
            except asyncio.TimeoutError:
                pass
    finally:
        await service.close()
        logger.info("Scheduler shutdown complete")


if __name__ == "__main__":
    asyncio.run(run_scheduler())