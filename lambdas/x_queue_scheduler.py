"""Publishes due queued posts on a schedule."""

from __future__ import annotations

from datetime import datetime, timezone

from common import response
from x_publisher import _list_account_posts, _parse_iso8601, publish_queued_post

ACCOUNT_IDS = {"account1", "account2"}


def _is_scheduler_approved(item: dict) -> bool:
    return bool(item.get("auto_approved")) and str(item.get("publish_mode", "")) == "scheduled"


def _is_due(item: dict) -> bool:
    if item.get("status") != "queued":
        return False
    if not _is_scheduler_approved(item):
        return False
    scheduled_for = _parse_iso8601(str(item.get("scheduled_for", "")))
    if not scheduled_for:
        return False
    return scheduled_for <= datetime.now(timezone.utc)


def lambda_handler(event, _context):
    try:
        account_id = str(event.get("account_id", "")).strip()
        account_ids = [account_id] if account_id in ACCOUNT_IDS else sorted(ACCOUNT_IDS)
        processed = []
        skipped = []
        for scheduled_account_id in account_ids:
            for item in _list_account_posts(scheduled_account_id):
                if item.get("status") != "queued":
                    continue
                if not _is_scheduler_approved(item):
                    skipped.append(
                        {
                            "account_id": scheduled_account_id,
                            "post_id": item.get("post_id", ""),
                            "status": "manual_or_unapproved",
                        }
                    )
                    continue
                if not _is_due(item):
                    continue
                result = publish_queued_post(scheduled_account_id, str(item.get("post_id", "")), approved=True)
                processed.append(
                    {
                        "account_id": scheduled_account_id,
                        "post_id": item.get("post_id", ""),
                        "status": result.get("status", "unknown"),
                    }
                )

        return response(
            200,
            {
                "provider": "x",
                "status": "scheduler_ran",
                "processed": processed,
                "skipped_manual_or_unapproved": skipped,
            },
        )
    except Exception as exc:
        return response(502, {"provider": "x", "status": "scheduler_failed", "error": str(exc)})
