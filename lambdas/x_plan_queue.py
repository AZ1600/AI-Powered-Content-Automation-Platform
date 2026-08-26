"""Queues every post from a saved plan."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from common import require_automation_key, response
from x_publisher import _queue_post

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


def _scheduled_for_utc(plan_date: str, slot: str) -> str:
    if not plan_date or not slot:
        return ""
    local_dt = datetime.strptime(f"{plan_date} {slot}", "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("Europe/London"))
    return local_dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def lambda_handler(event, _context):
    try:
        require_automation_key(event)
        body = _parse_event_body(event)
        account_id = body.get("account_id", "").strip()
        plan_id = body.get("plan_id", "").strip()
        plan_sk = body.get("plan_sk", "").strip()

        if not account_id:
            return response(400, {"provider": "x", "error": "Missing account_id"})
        if not plan_sk:
            return response(400, {"provider": "x", "error": "Missing plan_sk"})

        plans_table = _plans_table()
        if plans_table is None:
            raise RuntimeError("DynamoDB unavailable")

        result = plans_table.get_item(Key={"PK": f"ACCOUNT#{account_id}", "SK": plan_sk})
        item = result.get("Item")
        if not item:
            return response(404, {"provider": "x", "error": "Plan not found"})

        queued = []
        skipped = []
        for post in item.get("posts", []):
            queued_item = _queue_post(
                account_id=account_id,
                text=post.get("text", ""),
                reply_to="",
                reason="queued_from_plan",
                plan_id=plan_id or item.get("plan_id", ""),
                slot=post.get("slot", ""),
                post_type=post.get("type", ""),
                scheduled_for=_scheduled_for_utc(item.get("plan_date", ""), post.get("slot", "")),
                publish_mode="scheduled",
                auto_approved=True,
                approval_source="plan_queue",
            )
            if queued_item.get("duplicate"):
                skipped.append(
                    {
                        "post_id": queued_item.get("post_id", ""),
                        "slot": post.get("slot", ""),
                        "type": post.get("type", ""),
                        "status": "duplicate_skipped",
                    }
                )
                continue
            queued.append(
                {
                    "post_id": queued_item["post_id"],
                    "slot": queued_item["slot"],
                    "type": queued_item["type"],
                    "queued_at": queued_item["queued_at"],
                }
            )

        return response(
            200,
            {
                "provider": "x",
                "account_id": account_id,
                "status": "plan_queued",
                "plan_id": item.get("plan_id", plan_id),
                "queued_count": len(queued),
                "skipped_count": len(skipped),
                "items": queued,
                "skipped": skipped,
            },
        )
    except PermissionError as exc:
        return response(401, {"provider": "x", "status": "unauthorized", "error": str(exc)})
    except Exception as exc:
        return response(502, {"provider": "x", "status": "plan_queue_failed", "error": str(exc)})
