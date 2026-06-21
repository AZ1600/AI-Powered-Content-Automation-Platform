"""Marks a queued post as removed."""

from __future__ import annotations

import json
import os

from common import response, utc_now

try:
    import boto3
except ImportError:  # pragma: no cover
    boto3 = None


def _posts_table():
    if boto3 is None:
        return None
    return boto3.resource("dynamodb").Table(os.environ["X_POSTS_TABLE_NAME"])


def _parse_event_body(event) -> dict:
    raw_body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raise RuntimeError("Base64-encoded payloads are not supported in this MVP")
    return json.loads(raw_body)


def lambda_handler(event, _context):
    try:
        body = _parse_event_body(event)
        account_id = body.get("account_id", "").strip()
        post_id = body.get("post_id", "").strip()

        if not account_id:
            return response(400, {"provider": "x", "error": "Missing account_id"})
        if not post_id:
            return response(400, {"provider": "x", "error": "Missing post_id"})

        table = _posts_table()
        if table is None:
            raise RuntimeError("DynamoDB unavailable")

        result = table.get_item(Key={"PK": f"ACCOUNT#{account_id}", "SK": f"POST#{post_id}"})
        item = result.get("Item")
        if not item:
            return response(404, {"provider": "x", "error": "Queued post not found"})

        item["status"] = "removed"
        item["removed_at"] = utc_now()
        table.put_item(Item=item)
        return response(
            200,
            {
                "provider": "x",
                "account_id": account_id,
                "post_id": post_id,
                "status": "removed",
            },
        )
    except Exception as exc:
        return response(502, {"provider": "x", "status": "queue_remove_failed", "error": str(exc)})
