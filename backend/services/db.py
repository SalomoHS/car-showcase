import aioboto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from typing import Any, Dict, List, Optional
from core.config import settings

class DynamoDBService:
    def __init__(self):
        self._session: Optional[aioboto3.Session] = None

    def _get_session(self) -> aioboto3.Session:
        if self._session is None:
            self._session = aioboto3.Session()
        return self._session

    def _resource(self):
        return self._get_session().resource("dynamodb", region_name=settings.AWS_REGION)

    def _to_jsonable(self, value: Any) -> Any:
        if isinstance(value, list):
            return [self._to_jsonable(v) for v in value]
        if isinstance(value, dict):
            return {k: self._to_jsonable(v) for k, v in value.items()}
        if isinstance(value, Decimal):
            if value % 1 == 0:
                return int(value)
            return float(value)
        return value

    def _clean_for_ddb(self, item: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for k, v in item.items():
            if v is None:
                continue
            if isinstance(v, float):
                out[k] = Decimal(str(v))
            elif isinstance(v, list):
                out[k] = [Decimal(str(x)) if isinstance(x, float) else x for x in v]
            else:
                out[k] = v
        return out

    async def put_item(self, table_name: str, item: Dict[str, Any]) -> None:
        async with self._resource() as ddb:
            table = await ddb.Table(table_name)
            await table.put_item(Item=self._clean_for_ddb(item))

    async def scan_all(self, table_name: str, limit: int = 1000) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        async with self._resource() as ddb:
            table = await ddb.Table(table_name)
            scan_kwargs: Dict[str, Any] = {}
            while True:
                resp = await table.scan(**scan_kwargs)
                items.extend(resp.get("Items", []))
                if len(items) >= limit or "LastEvaluatedKey" not in resp:
                    break
                scan_kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
        return [self._to_jsonable(i) for i in items[:limit]]

    async def query_by_session(
        self,
        table_name: str,
        session_id: str,
        ascending: bool = True,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        async with self._resource() as ddb:
            table = await ddb.Table(table_name)
            resp = await table.query(
                KeyConditionExpression=Key("session_id").eq(session_id),
                ScanIndexForward=ascending,
                Limit=limit,
            )
        return [self._to_jsonable(i) for i in resp.get("Items", [])]
