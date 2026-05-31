"""Idempotent DynamoDB table bootstrap for the Virtual Dealer app.

Creates these tables if they do not exist:
  - virtual-dealer-status-checks  (PK: id)
  - virtual-dealer-leads          (PK: id)
  - virtual-dealer-chat-logs      (PK: session_id, SK: created_at, TTL on `expires_at`)

Uses PAY_PER_REQUEST billing so there is no provisioned capacity to manage.

Run once:  python /app/backend/bootstrap_dynamo.py
"""

import os
import asyncio
from pathlib import Path

import aioboto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

REGION = os.environ["AWS_REGION"]
T_STATUS = os.environ.get("DDB_TABLE_STATUS", "virtual-dealer-status-checks")
T_LEADS = os.environ.get("DDB_TABLE_LEADS", "virtual-dealer-leads")
T_CHAT = os.environ.get("DDB_TABLE_CHAT", "virtual-dealer-chat-logs")


TABLE_SPECS = [
    {
        "TableName": T_STATUS,
        "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": T_LEADS,
        "AttributeDefinitions": [{"AttributeName": "id", "AttributeType": "S"}],
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": T_CHAT,
        "AttributeDefinitions": [
            {"AttributeName": "session_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
        ],
        "KeySchema": [
            {"AttributeName": "session_id", "KeyType": "HASH"},
            {"AttributeName": "created_at", "KeyType": "RANGE"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
]

# Tables that should have a TTL enabled. Attribute name must match what server.py writes.
TTL_SPECS = {
    T_CHAT: "expires_at",
}


async def ensure_tables() -> None:
    session = aioboto3.Session()
    async with session.client("dynamodb", region_name=REGION) as ddb:
        existing = set()
        paginator = ddb.get_paginator("list_tables")
        async for page in paginator.paginate():
            existing.update(page.get("TableNames", []))

        for spec in TABLE_SPECS:
            name = spec["TableName"]
            if name in existing:
                print(f"[ok]   table exists: {name}")
                continue
            try:
                await ddb.create_table(**spec)
                print(f"[new]  creating:    {name}")
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code")
                if code == "ResourceInUseException":
                    print(f"[ok]   table exists (race): {name}")
                else:
                    raise

        # Wait until all tables are ACTIVE
        for spec in TABLE_SPECS:
            name = spec["TableName"]
            while True:
                desc = await ddb.describe_table(TableName=name)
                status = desc["Table"]["TableStatus"]
                if status == "ACTIVE":
                    print(f"[ready] {name}")
                    break
                print(f"[wait]  {name} status={status}")
                await asyncio.sleep(2)

        # Enable TTL where requested (idempotent)
        for table_name, ttl_attr in TTL_SPECS.items():
            try:
                desc = await ddb.describe_time_to_live(TableName=table_name)
                cur = desc.get("TimeToLiveDescription", {}) or {}
                cur_status = cur.get("TimeToLiveStatus")
                cur_attr = cur.get("AttributeName")
                if cur_status in ("ENABLED", "ENABLING") and cur_attr == ttl_attr:
                    print(f"[ok]   TTL already enabled on {table_name} (attr={cur_attr})")
                    continue
                await ddb.update_time_to_live(
                    TableName=table_name,
                    TimeToLiveSpecification={"Enabled": True, "AttributeName": ttl_attr},
                )
                print(f"[new]  TTL enabled on {table_name} (attr={ttl_attr})")
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code")
                # AWS throttles TTL updates to once per hour per table — treat as ok.
                if code in ("ValidationException",):
                    print(f"[warn] TTL update skipped on {table_name}: {e.response['Error'].get('Message')}")
                else:
                    raise


if __name__ == "__main__":
    asyncio.run(ensure_tables())
