"""Publishes a queued post immediately with approval."""

from __future__ import annotations

import json

from common import require_automation_key, response
from x_publisher import publish_queued_post


def _parse_event_body(event) -> dict:
    raw_body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raise RuntimeError("Base64-encoded payloads are not supported in this MVP")
    return json.loads(raw_body)


def lambda_handler(event, _context):
    try:
        require_automation_key(event)
        body = _parse_event_body(event)
        account_id = body.get("account_id", "").strip()
        post_id = body.get("post_id", "").strip()
        if "approved" in body and type(body["approved"]) is not bool:
            return response(400, {"provider": "x", "error": "approved must be a JSON boolean"})
        approved = body.get("approved") is True

        if not account_id:
            return response(400, {"provider": "x", "error": "Missing account_id"})
        if not post_id:
            return response(400, {"provider": "x", "error": "Missing post_id"})

        result = publish_queued_post(account_id, post_id, approved)
        print(json.dumps({"event": "queue_publish_result", "account_id": account_id, "post_id": post_id, "result": result}))
        status_code = 200 if result.get("status") not in {"approval_required"} else 400
        return response(status_code, result)
    except PermissionError as exc:
        return response(401, {"provider": "x", "status": "unauthorized", "error": str(exc)})
    except Exception as exc:
        print(json.dumps({"event": "queue_publish_exception", "error": str(exc)}))
        return response(502, {"provider": "x", "status": "queue_publish_failed", "error": str(exc)})
