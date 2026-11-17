"""Offline regression tests for publishing-approval boundaries.

External token retrieval, DynamoDB and X API publishing are mocked. These
checks cannot post live content or access AWS resources.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lambdas"))

import x_publisher  # noqa: E402
import x_queue_publish  # noqa: E402
import x_queue_scheduler  # noqa: E402


def _event(payload):
    return {"headers": {"X-Automation-Key": "offline-test"}, "body": json.dumps(payload)}


def _body(result):
    return json.loads(result["body"])


def test_manual_publish_rejects_non_boolean_approval_before_side_effects():
    for value in ("false", "true", 0, 1, None, [], {}):
        with (
            patch.object(x_publisher, "require_automation_key"),
            patch.object(x_publisher, "_get_publish_tokens") as tokens,
            patch.object(x_publisher, "_queue_post") as queue,
        ):
            result = x_publisher.lambda_handler(
                _event({"account_id": "account1", "text": "offline test", "approved": value}), None
            )
            assert result["statusCode"] == 400, value
            assert "approved must be a JSON boolean" in _body(result)["error"]
            tokens.assert_not_called()
            queue.assert_not_called()


def test_manual_publish_without_approval_fails_closed():
    for extra in ({}, {"approved": False}):
        with (
            patch.object(x_publisher, "require_automation_key"),
            patch.object(x_publisher, "_get_publish_tokens") as tokens,
        ):
            result = x_publisher.lambda_handler(
                _event({"account_id": "account1", "text": "offline test", **extra}), None
            )
            assert result["statusCode"] == 400
            assert "requires approved=true" in _body(result)["error"]
            tokens.assert_not_called()


def test_manual_publish_explicit_true_can_reach_mocked_publisher():
    with (
        patch.object(x_publisher, "require_automation_key"),
        patch.object(x_publisher, "_get_publish_tokens", return_value={"access_token": "fake-token"}),
        patch.object(x_publisher, "_publish_post", return_value={"data": {"id": "offline-post"}}) as publish,
    ):
        result = x_publisher.lambda_handler(
            _event({"account_id": "account1", "text": "offline test", "approved": True}), None
        )
        assert result["statusCode"] == 200
        assert _body(result)["status"] == "posted"
        publish.assert_called_once_with("fake-token", "offline test", "", "", "")


def test_manual_queue_rejects_non_boolean_flag_before_queueing():
    for value in ("false", "true", 0, 1, None, [], {}):
        with (
            patch.object(x_publisher, "require_automation_key"),
            patch.object(x_publisher, "_queue_post") as queue,
            patch.object(x_publisher, "_get_publish_tokens") as tokens,
        ):
            result = x_publisher.lambda_handler(
                _event({"account_id": "account1", "text": "offline test", "queue_only": value}), None
            )
            assert result["statusCode"] == 400, value
            assert "queue_only must be a JSON boolean" in _body(result)["error"]
            queue.assert_not_called()
            tokens.assert_not_called()


def test_manual_queue_explicit_true_queues_without_publishing():
    with (
        patch.object(x_publisher, "require_automation_key"),
        patch.object(
            x_publisher,
            "_queue_post",
            return_value={"post_id": "offline-id", "queued_at": "2026-01-01T00:00:00Z"},
        ) as queue,
        patch.object(x_publisher, "_get_publish_tokens") as tokens,
    ):
        result = x_publisher.lambda_handler(
            _event({"account_id": "account1", "text": "offline test", "queue_only": True}), None
        )
        assert result["statusCode"] == 200
        assert _body(result)["status"] == "queued"
        queue.assert_called_once()
        tokens.assert_not_called()


def test_manual_queue_explicit_false_does_not_queue():
    with (
        patch.object(x_publisher, "require_automation_key"),
        patch.object(x_publisher, "_queue_post") as queue,
    ):
        result = x_publisher.lambda_handler(
            _event({"account_id": "account1", "text": "offline test", "queue_only": False}), None
        )
        assert result["statusCode"] == 400  # Explicit approval is still required.
        queue.assert_not_called()


def test_queue_publish_rejects_non_boolean_approval_before_side_effects():
    for value in ("false", "true", 0, 1, None, [], {}):
        with (
            patch.object(x_queue_publish, "require_automation_key"),
            patch.object(x_queue_publish, "publish_queued_post") as publish,
        ):
            result = x_queue_publish.lambda_handler(
                _event({"account_id": "account1", "post_id": "post-1", "approved": value}), None
            )
            assert result["statusCode"] == 400, value
            assert "approved must be a JSON boolean" in _body(result)["error"]
            publish.assert_not_called()


def test_queue_publish_missing_approval_fails_closed():
    with (
        patch.object(x_queue_publish, "require_automation_key"),
        patch.object(
            x_queue_publish, "publish_queued_post", return_value={"status": "approval_required"}
        ) as publish,
    ):
        result = x_queue_publish.lambda_handler(
            _event({"account_id": "account1", "post_id": "post-1"}), None
        )
        assert result["statusCode"] == 400
        publish.assert_called_once_with("account1", "post-1", False)


def test_queue_publish_explicit_false_fails_closed():
    with (
        patch.object(x_queue_publish, "require_automation_key"),
        patch.object(x_queue_publish, "publish_queued_post", return_value={"status": "approval_required"}) as publish,
    ):
        result = x_queue_publish.lambda_handler(
            _event({"account_id": "account1", "post_id": "post-1", "approved": False}), None
        )
        assert result["statusCode"] == 400
        publish.assert_called_once_with("account1", "post-1", False)


def test_queue_publish_explicit_true_can_reach_mocked_publisher():
    with (
        patch.object(x_queue_publish, "require_automation_key"),
        patch.object(x_queue_publish, "publish_queued_post", return_value={"status": "published"}) as publish,
    ):
        result = x_queue_publish.lambda_handler(
            _event({"account_id": "account1", "post_id": "post-1", "approved": True}), None
        )
        assert result["statusCode"] == 200
        publish.assert_called_once_with("account1", "post-1", True)


def test_queue_publish_unauthorized_request_never_publishes():
    with (
        patch.object(x_queue_publish, "require_automation_key", side_effect=PermissionError("Invalid key")),
        patch.object(x_queue_publish, "publish_queued_post") as publish,
    ):
        result = x_queue_publish.lambda_handler(
            _event({"account_id": "account1", "post_id": "post-1", "approved": True}), None
        )
        assert result["statusCode"] == 401
        publish.assert_not_called()


def test_scheduler_requires_true_boolean_approval_and_scheduled_mode():
    approved = {"auto_approved": True, "publish_mode": "scheduled"}
    assert x_queue_scheduler._is_scheduler_approved(approved)
    for value in ("true", "false", 1, 0, None, [], {}, False):
        assert not x_queue_scheduler._is_scheduler_approved({"auto_approved": value, "publish_mode": "scheduled"})
    assert not x_queue_scheduler._is_scheduler_approved({"auto_approved": True, "publish_mode": "manual"})


def test_scheduler_skips_string_approved_posts_without_publishing():
    item = {
        "account_id": "account1",
        "post_id": "offline-id",
        "status": "queued",
        "auto_approved": "true",
        "publish_mode": "scheduled",
        "scheduled_for": "2025-01-01T00:00:00+00:00",
    }
    with (
        patch.object(x_queue_scheduler, "_list_account_posts", return_value=[item]),
        patch.object(x_queue_scheduler, "publish_queued_post") as publish,
    ):
        result = x_queue_scheduler.lambda_handler({"account_id": "account1"}, None)
        assert result["statusCode"] == 200
        assert len(_body(result)["skipped_manual_or_unapproved"]) == 1
        publish.assert_not_called()


def test_manual_publish_unauthorized_request_never_reads_tokens():
    with (
        patch.object(x_publisher, "require_automation_key", side_effect=PermissionError("Invalid key")),
        patch.object(x_publisher, "_get_publish_tokens") as tokens,
    ):
        result = x_publisher.lambda_handler(
            _event({"account_id": "account1", "text": "offline test", "approved": True}), None
        )
        assert result["statusCode"] == 401
        tokens.assert_not_called()
