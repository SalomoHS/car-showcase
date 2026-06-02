import os
import asyncio
import aiohttp
import aioboto3
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

from core.config import settings

logger = logging.getLogger("langfuse-metrics")

LANGFUSE_NAMESPACE = "LangfuseMetrics"

class LangfuseMetricsService:
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._cw_session: Optional[aioboto3.Session] = None
        self._base_url = settings.LANGFUSE_BASE_URL
        self._secret_key = settings.LANGFUSE_SECRET_KEY
        self._public_key = settings.LANGFUSE_PUBLIC_KEY

    def _get_cw_session(self) -> aioboto3.Session:
        if self._cw_session is None:
            self._cw_session = aioboto3.Session()
        return self._cw_session

    def _get_cw_client(self):
        return self._get_cw_session().client("cloudwatch", region_name=settings.AWS_REGION)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            auth = aiohttp.BasicAuth(self._public_key, self._secret_key)
            self._session = aiohttp.ClientSession(auth=auth)
        return self._session

    async def _fetch_traces(self, start_time: datetime, end_time: datetime) -> dict:
        session = await self._get_session()
        url = f"{self._base_url}/api/public/traces"
        params = {
            "startTime": start_time.isoformat(),
            "endTime": end_time.isoformat(),
            "limit": 100,
        }
        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    body = await resp.text()
                    logger.warning(f"Langfuse API returned {resp.status}: {body[:200]}")
                    return {"data": []}
        except Exception as e:
            logger.error(f"Failed to fetch traces: {e}")
            return {"data": []}

    async def _fetch_generations(self, start_time: datetime, end_time: datetime) -> dict:
        session = await self._get_session()
        url = f"{self._base_url}/api/public/generations"
        params = {
            "startTime": start_time.isoformat(),
            "endTime": end_time.isoformat(),
            "limit": 100,
        }
        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    body = await resp.text()
                    logger.warning(f"Langfuse API returned {resp.status}: {body[:200]}")
                    return {"data": []}
        except Exception as e:
            logger.error(f"Failed to fetch generations: {e}")
            return {"data": []}

    async def _fetch_observations(self, start_time: datetime, end_time: datetime) -> dict:
        session = await self._get_session()
        url = f"{self._base_url}/api/public/observations"
        params = {
            "startTime": start_time.isoformat(),
            "endTime": end_time.isoformat(),
            "limit": 100,
            "type": "GENERATION",
        }
        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    body = await resp.text()
                    logger.warning(f"Langfuse observations API returned {resp.status}: {body[:200]}")
                    return {"data": []}
        except Exception as e:
            logger.error(f"Failed to fetch observations: {e}")
            return {"data": []}

    def _calculate_anthropic_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = {
            "claude-sonnet-4.6": {"input": 3.0, "output": 15.0},
            "claude-haiku-4.5": {"input": 0.25, "output": 1.25},
            "claude-opus-4.7": {"input": 15.0, "output": 75.0},
            "claude-sonnet-4.7": {"input": 3.0, "output": 15.0},
            "claude-3-5-sonnet": {"input": 3.0, "output": 15.0},
            "claude-3-5-haiku": {"input": 0.25, "output": 1.25},
        }
        model_key = model.lower().replace("-", "_").replace(".", "_")
        default_pricing = {"input": 3.0, "output": 15.0}
        p = pricing.get(model, default_pricing)
        input_cost = (input_tokens / 1_000_000) * p["input"]
        output_cost = (output_tokens / 1_000_000) * p["output"]
        return round(input_cost + output_cost, 6)

    async def fetch_and_push_metrics(self) -> dict:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
        
        traces_data = await self._fetch_traces(start_time, end_time)
        observations_data = await self._fetch_observations(start_time, end_time)
        
        total_input_tokens = 0
        total_output_tokens = 0
        total_cost = 0.0
        total_traces = 0
        total_generations = 0
        response_times: list = []
        
        for trace in traces_data.get("data", []):
            total_traces += 1
            if trace.get("endTime") and trace.get("startTime"):
                try:
                    start = datetime.fromisoformat(trace["startTime"].replace("Z", "+00:00"))
                    end = datetime.fromisoformat(trace["endTime"].replace("Z", "+00:00"))
                    response_time_ms = (end - start).total_seconds() * 1000
                    response_times.append(response_time_ms)
                except Exception:
                    pass
        
        for obs in observations_data.get("data", []):
            if obs.get("type") == "GENERATION":
                total_generations += 1
                usage = obs.get("usage", {}) or {}
                if usage:
                    input_tok = usage.get("input_tokens", 0) or usage.get("input", 0) or 0
                    output_tok = usage.get("output_tokens", 0) or usage.get("output", 0) or 0
                    total_input_tokens += input_tok
                    total_output_tokens += output_tok
                    
                    model = obs.get("model", "unknown") or "unknown"
                    cost = self._calculate_anthropic_cost(model, input_tok, output_tok)
                    total_cost += cost

        sorted_times = sorted(response_times) if response_times else []
        p95_index = int(len(sorted_times) * 0.95)
        p95_response_time = sorted_times[p95_index] if sorted_times else 0
        
        metrics = [
            ("TotalCostUSD", total_cost, "None"),
            ("TotalInputTokens", float(total_input_tokens), "Count"),
            ("TotalOutputTokens", float(total_output_tokens), "Count"),
            ("TotalTokens", float(total_input_tokens + total_output_tokens), "Count"),
            ("TotalTraces", float(total_traces), "Count"),
            ("TotalGenerations", float(total_generations), "Count"),
            ("P95ResponseTimeMs", p95_response_time, "Milliseconds"),
        ]

        metric_data = []
        for name, value, unit in metrics:
            metric_entry = {
                "MetricName": name,
                "Value": value,
                "Timestamp": end_time,
                "Dimensions": [{"Name": "Service", "Value": "Langfuse"}],
            }
            if unit and unit != "None":
                metric_entry["Unit"] = unit
            metric_data.append(metric_entry)
        
        try:
            async with self._get_cw_client() as cw:
                await cw.put_metric_data(
                    Namespace=LANGFUSE_NAMESPACE,
                    MetricData=metric_data,
                )
            logger.info(
                f"Pushed Langfuse metrics: cost=${total_cost:.4f}, "
                f"tokens={total_input_tokens + total_output_tokens}, "
                f"p95={p95_response_time:.0f}ms"
            )
            return {"success": True, "metrics": metrics}
        except Exception as e:
            logger.error(f"Failed to push metrics to CloudWatch: {e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


async def run_metrics_fetch():
    service = LangfuseMetricsService()
    try:
        result = await service.fetch_and_push_metrics()
        print(f"Metrics fetch result: {result}")
    finally:
        await service.close()


if __name__ == "__main__":
    from pathlib import Path
    from dotenv import load_dotenv
    
    ROOT_DIR = Path(__file__).parent.parent
    load_dotenv(ROOT_DIR / ".env")
    
    asyncio.run(run_metrics_fetch())