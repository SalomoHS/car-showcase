import aioboto3
from typing import Optional
from core.config import settings

class CloudWatchMetricsService:
    def __init__(self):
        self._session: Optional[aioboto3.Session] = None
        self._namespace = "CustomMetrics"
        self._service = "Backend"

    def _get_session(self) -> aioboto3.Session:
        if self._session is None:
            self._session = aioboto3.Session()
        return self._session

    def _client(self):
        return self._get_session().client("cloudwatch", region_name=settings.AWS_REGION)

    async def put_metric(self, metric_name: str, value: float, unit: str = "Count") -> None:
        async with self._client() as cw:
            await cw.put_metric_data(
                Namespace=self._namespace,
                MetricData=[
                    {
                        "MetricName": metric_name,
                        "Dimensions": [
                            {"Name": "Service", "Value": self._service}
                        ],
                        "Value": value,
                        "Unit": unit,
                    }
                ]
            )

    async def increment_request_count(self, count: float = 1.0) -> None:
        await self.put_metric("RequestCount", count, "Count")

    async def increment_error_count(self, count: float = 1.0) -> None:
        await self.put_metric("ErrorCount", count, "Count")

_cw_metrics_service: Optional[CloudWatchMetricsService] = None

def get_cw_metrics_service() -> CloudWatchMetricsService:
    global _cw_metrics_service
    if _cw_metrics_service is None:
        _cw_metrics_service = CloudWatchMetricsService()
    return _cw_metrics_service