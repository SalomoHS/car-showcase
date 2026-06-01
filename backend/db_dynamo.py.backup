"""Thin async DynamoDB helpers used by the FastAPI app.

We expose small async functions instead of a heavy DAO so each FastAPI
endpoint can use the most appropriate DynamoDB call (put_item / query / scan).

A single aioboto3 Session is reused per process; each call opens a short-lived
resource context to avoid leaking connections.
"""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Any, Dict, List, Optional

import aioboto3
from boto3.dynamodb.conditions import Key

AWS_REGION = os.environ.get("AWS_REGION", "ap-southeast-1")

T_STATUS = os.environ.get("DDB_TABLE_STATUS", "virtual-dealer-status-checks")
T_LEADS = os.environ.get("DDB_TABLE_LEADS", "virtual-dealer-leads")
T_CHAT = os.environ.get("DDB_TABLE_CHAT", "virtual-dealer-chat-logs")

_session: Optional[aioboto3.Session] = None


def _get_session() -> aioboto3.Session:
    global _session
    if _session is None:
        _session = aioboto3.Session()
    return _session


def _resource():
    return _get_session().resource("dynamodb", region_name=AWS_REGION)


# ──────────────────────── helpers ────────────────────────

def _to_jsonable(value: Any) -> Any:
    """DynamoDB returns Decimal for any numeric value. Convert recursively."""
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, Decimal):
        # int-valued Decimals -> int, else float
        if value % 1 == 0:
            return int(value)
        return float(value)
    return value


def _clean_for_ddb(item: Dict[str, Any]) -> Dict[str, Any]:
    """DynamoDB does not accept Python floats — convert to Decimal.
    Also drops keys whose value is None (DDB requires explicit NULL otherwise).
    """
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


# ──────────────────────── put / get / list ────────────────────────

async def put_item(table_name: str, item: Dict[str, Any]) -> None:
    async with _resource() as ddb:
        table = await ddb.Table(table_name)
        await table.put_item(Item=_clean_for_ddb(item))


async def scan_all(table_name: str, limit: int = 1000) -> List[Dict[str, Any]]:
    """Paginated scan. Fine for low-volume tables (status, leads)."""
    items: List[Dict[str, Any]] = []
    async with _resource() as ddb:
        table = await ddb.Table(table_name)
        scan_kwargs: Dict[str, Any] = {}
        while True:
            resp = await table.scan(**scan_kwargs)
            items.extend(resp.get("Items", []))
            if len(items) >= limit or "LastEvaluatedKey" not in resp:
                break
            scan_kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return [_to_jsonable(i) for i in items[:limit]]


async def query_by_session(
    table_name: str,
    session_id: str,
    ascending: bool = True,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Query the chat-logs table by session_id (partition key)."""
    async with _resource() as ddb:
        table = await ddb.Table(table_name)
        resp = await table.query(
            KeyConditionExpression=Key("session_id").eq(session_id),
            ScanIndexForward=ascending,
            Limit=limit,
        )
    return [_to_jsonable(i) for i in resp.get("Items", [])]
