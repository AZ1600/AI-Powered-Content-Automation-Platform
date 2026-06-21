"""Returns high-level queue and plan counts for each connected X account."""

from __future__ import annotations

import os

from common import response

try:
    import boto3
    from boto3.dynamodb.conditions import Key
except ImportError:  # pragma: no cover
    boto3 = None
    Key = None


ACCOUNT_IDS = ["account1", "account2"]


def _posts_table():
    if boto3 is None:
        return None
    return boto3.resource("dynamodb").Table(os.environ["X_POSTS_TABLE_NAME"])


def _plans_table():
    if boto3 is None:
        return None
    return boto3.resource("dynamodb").Table(os.environ["X_PLANS_TABLE_NAME"])


def _queue_counts(account_id: str) -> dict:
    table = _posts_table()
    if table is None:
        raise RuntimeError("DynamoDB unavailable")
    result = table.query(KeyConditionExpression=Key("PK").eq(f"ACCOUNT#{account_id}"))
    items = result.get("Items", [])
    queued_items = [item for item in items if item.get("status") == "queued"]
    published_items = [item for item in items if item.get("status") == "published"]
    failed_items = [item for item in items if item.get("status") == "failed"]
    removed_items = [item for item in items if item.get("status") == "removed"]
    return {
        "queued": len(queued_items),
        "from_plan": len([item for item in queued_items if item.get("source_plan_id")]),
        "manual": len([item for item in queued_items if not item.get("source_plan_id")]),
        "published": len(published_items),
        "failed": len(failed_items),
        "removed": len(removed_items),
    }


def _plan_count(account_id: str) -> int:
    table = _plans_table()
    if table is None:
        raise RuntimeError("DynamoDB unavailable")
    result = table.query(KeyConditionExpression=Key("PK").eq(f"ACCOUNT#{account_id}"))
    items = result.get("Items", [])
    return len([item for item in items if str(item.get("SK", "")).startswith("PLAN#")])


def lambda_handler(_event, _context):
    try:
        accounts = []
        for account_id in ACCOUNT_IDS:
            queue = _queue_counts(account_id)
            accounts.append(
                {
                    "account_id": account_id,
                    "queued": queue["queued"],
                    "queued_from_plan": queue["from_plan"],
                    "manual_drafts": queue["manual"],
                    "published": queue["published"],
                    "failed": queue["failed"],
                    "removed": queue["removed"],
                    "saved_plans": _plan_count(account_id),
                }
            )

        return response(200, {"provider": "x", "accounts": accounts})
    except Exception as exc:
        return response(502, {"provider": "x", "status": "summary_failed", "error": str(exc)})
