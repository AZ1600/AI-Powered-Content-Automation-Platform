"""Saves a daily posting plan for a connected X account."""

from __future__ import annotations

import json
import os
from uuid import uuid4

from common import response, utc_now

try:
    import boto3
except ImportError:  # pragma: no cover
    boto3 = None


def _plans_table():
    if boto3 is None:
        return None
    return boto3.resource("dynamodb").Table(os.environ["X_PLANS_TABLE_NAME"])


def _parse_event_body(event) -> dict:
    raw_body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raise RuntimeError("Base64-encoded payloads are not supported in this MVP")
    return json.loads(raw_body)


def lambda_handler(event, _context):
    try:
        body = _parse_event_body(event)
        account_id = body.get("account_id", "").strip()
        plan_date = body.get("plan_date", "").strip()
        posts = body.get("posts", [])
        notes = body.get("notes", "").strip()

        if not account_id:
            return response(400, {"provider": "x", "error": "Missing account_id"})
        if not plan_date:
            return response(400, {"provider": "x", "error": "Missing plan_date"})
        if not isinstance(posts, list) or not posts:
            return response(400, {"provider": "x", "error": "posts must be a non-empty list"})

        table = _plans_table()
        if table is None:
            raise RuntimeError("DynamoDB unavailable")

        plan_id = f"plan_{uuid4().hex}"
        item = {
            "PK": f"ACCOUNT#{account_id}",
            "SK": f"PLAN#{plan_date}#{plan_id}",
            "plan_id": plan_id,
            "account_id": account_id,
            "plan_date": plan_date,
            "posts": posts,
            "notes": notes,
            "saved_at": utc_now(),
        }
        table.put_item(Item=item)

        return response(
            200,
            {
                "provider": "x",
                "account_id": account_id,
                "status": "plan_saved",
                "plan_id": plan_id,
                "plan_sk": item["SK"],
                "plan_date": plan_date,
                "saved_at": item["saved_at"],
            },
        )
    except Exception as exc:
        return response(502, {"provider": "x", "status": "plan_save_failed", "error": str(exc)})
