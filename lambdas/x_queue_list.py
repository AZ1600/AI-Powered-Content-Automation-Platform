"""Lists queued posts for a connected X account."""

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


def _posts_table():
    if boto3 is None:
        return None
    return boto3.resource("dynamodb").Table(os.environ["X_POSTS_TABLE_NAME"])


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

        table = _posts_table()
        if table is None:
            raise RuntimeError("DynamoDB unavailable")

        result = table.query(KeyConditionExpression=Key("PK").eq(f"ACCOUNT#{account_id}"))
        items = sorted(result.get("Items", []), key=lambda item: item.get("queued_at", ""), reverse=True)
        queued_items = [item for item in items if item.get("status") == "queued"]
        from_plan_count = len([item for item in queued_items if item.get("source_plan_id")])
        manual_count = len(queued_items) - from_plan_count

        return response(
            200,
            {
                "provider": "x",
                "account_id": account_id,
                "count": len(queued_items),
                "summary": {
                    "queued": len(queued_items),
                    "from_plan": from_plan_count,
                    "manual": manual_count,
                },
                "items": json_safe(queued_items),
            },
        )
    except Exception as exc:
        return response(502, {"provider": "x", "status": "queue_list_failed", "error": str(exc)})
