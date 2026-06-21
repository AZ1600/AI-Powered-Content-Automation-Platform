"""Lists saved daily plans for a connected X account."""

from __future__ import annotations

import os
from urllib.parse import parse_qs

from common import json_safe, response

try:
    import boto3
    from boto3.dynamodb.conditions import Key
except ImportError:  # pragma: no cover
    boto3 = None
    Key = None


def _plans_table():
    if boto3 is None:
        return None
    return boto3.resource("dynamodb").Table(os.environ["X_PLANS_TABLE_NAME"])


def _query_params(event):
    if event.get("queryStringParameters"):
        return event["queryStringParameters"]
    raw = event.get("rawQueryString", "")
    parsed = parse_qs(raw)
    return {key: values[0] for key, values in parsed.items()}


def lambda_handler(event, _context):
    try:
        params = _query_params(event)
        account_id = params.get("account_id", "").strip()
        if not account_id:
            return response(400, {"provider": "x", "error": "Missing account_id"})

        table = _plans_table()
        if table is None:
            raise RuntimeError("DynamoDB unavailable")

        result = table.query(KeyConditionExpression=Key("PK").eq(f"ACCOUNT#{account_id}"))
        items = sorted(result.get("Items", []), key=lambda item: item.get("saved_at", ""), reverse=True)
        plan_items = [item for item in items if str(item.get("SK", "")).startswith("PLAN#")]

        return response(
            200,
            {
                "provider": "x",
                "account_id": account_id,
                "count": len(plan_items),
                "items": json_safe(plan_items),
            },
        )
    except Exception as exc:
        return response(502, {"provider": "x", "status": "plan_list_failed", "error": str(exc)})
