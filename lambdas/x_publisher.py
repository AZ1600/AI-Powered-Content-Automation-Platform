"""Publishes text posts to connected X accounts or queues them for later."""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from common import require_automation_key, response, utc_now

try:
    import boto3
    from boto3.dynamodb.conditions import Key
except ImportError:  # pragma: no cover
    boto3 = None
    Key = None

RETRY_COOLDOWN_MINUTES = 10
MAX_RETRY_COUNT = 3
POST_RETENTION_DAYS = 180


def _connections_table():
    if boto3 is None:
        return None
    return boto3.resource("dynamodb").Table(os.environ["X_CONNECTIONS_TABLE_NAME"])


def _secrets():
    return boto3.client("secretsmanager") if boto3 is not None else None


def _posts_table():
    if boto3 is None:
        return None
    return boto3.resource("dynamodb").Table(os.environ["X_POSTS_TABLE_NAME"])


def _media_bucket():
    if boto3 is None:
        return None
    return boto3.client("s3")


def _parse_event_body(event) -> dict:
    raw_body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raise RuntimeError("Base64-encoded payloads are not supported in this MVP")
    return json.loads(raw_body)


def _parse_iso8601(value: str) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _expiry_epoch(days: int) -> int:
    return int((datetime.now(timezone.utc) + timedelta(days=days)).timestamp())


def _list_account_posts(account_id: str) -> list[dict]:
    table = _posts_table()
    if table is None:
        raise RuntimeError("DynamoDB unavailable")
    result = table.query(KeyConditionExpression=Key("PK").eq(f"ACCOUNT#{account_id}"))
    return result.get("Items", [])


def _find_duplicate_post(account_id: str, text: str) -> dict | None:
    normalized = text.strip().lower()
    for item in _list_account_posts(account_id):
        if item.get("status") not in {"queued", "published"}:
            continue
        if str(item.get("text", "")).strip().lower() == normalized:
            return item
    return None


def _get_post_item(account_id: str, post_id: str) -> dict | None:
    table = _posts_table()
    if table is None:
        raise RuntimeError("DynamoDB unavailable")
    result = table.get_item(Key={"PK": f"ACCOUNT#{account_id}", "SK": f"POST#{post_id}"})
    return result.get("Item")


def _update_post_item(account_id: str, post_id: str, updates: dict) -> None:
    table = _posts_table()
    if table is None:
        raise RuntimeError("DynamoDB unavailable")
    item = _get_post_item(account_id, post_id)
    if not item:
        raise RuntimeError(f"Post {post_id} not found for {account_id}")
    item.update(updates)
    table.put_item(Item=item)


def _connection_secret_name(account_id: str) -> str:
    table = _connections_table()
    if table is None:
        raise RuntimeError("DynamoDB unavailable")
    result = table.get_item(Key={"PK": f"ACCOUNT#{account_id}", "SK": "X"})
    item = result.get("Item")
    if not item:
        raise RuntimeError(f"Account {account_id} is not connected")
    return item["token_secret_name"]


def _load_account_tokens(account_id: str) -> dict:
    client = _secrets()
    if client is None:
        raise RuntimeError("Secrets Manager unavailable")
    secret_name = _connection_secret_name(account_id)
    secret_string = client.get_secret_value(SecretId=secret_name)["SecretString"]
    return json.loads(secret_string)


def _save_account_tokens(account_id: str, token_payload: dict) -> None:
    client = _secrets()
    if client is None:
        raise RuntimeError("Secrets Manager unavailable")
    secret_name = _connection_secret_name(account_id)
    client.put_secret_value(SecretId=secret_name, SecretString=json.dumps(token_payload))


def _with_token_metadata(token_payload: dict) -> dict:
    payload = dict(token_payload)
    payload["token_saved_at"] = utc_now()
    expires_in = payload.get("expires_in")
    if expires_in:
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
            payload["access_token_expires_at"] = expires_at.isoformat(timespec="seconds")
        except (TypeError, ValueError):
            pass
    return payload


def _client_basic_auth_header() -> str:
    client = _secrets()
    if client is None:
        raise RuntimeError("Secrets Manager unavailable")
    client_secret_name = os.environ["X_CLIENT_SECRET_SECRET_NAME"]
    client_secret = client.get_secret_value(SecretId=client_secret_name)["SecretString"]
    client_id = os.environ["X_CLIENT_ID"]
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")
    return f"Basic {basic}"


def _refresh_access_token(account_id: str, refresh_token: str) -> dict:
    token_url = os.environ["X_TOKEN_URL"]
    body = {
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "client_id": os.environ["X_CLIENT_ID"],
    }
    request = Request(
        token_url,
        data=urlencode(body).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": _client_basic_auth_header(),
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as handle:
            refreshed = json.loads(handle.read().decode("utf-8"))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(
            json.dumps(
                {
                    "event": "x_refresh_http_error",
                    "account_id": account_id,
                    "status_code": exc.code,
                    "response_body": error_body,
                }
            )
        )
        raise RuntimeError(f"X refresh failed: {exc.code} {error_body}") from exc

    refreshed_payload = _with_token_metadata(refreshed)
    if "refresh_token" not in refreshed_payload:
        refreshed_payload["refresh_token"] = refresh_token
    _save_account_tokens(account_id, refreshed_payload)
    print(json.dumps({"event": "x_refresh_success", "account_id": account_id}))
    return refreshed_payload


def _access_token_expired(tokens: dict) -> bool:
    expires_at = _parse_iso8601(str(tokens.get("access_token_expires_at", "")))
    if not expires_at:
        return False
    return datetime.now(timezone.utc) >= (expires_at - timedelta(minutes=2))


def _get_publish_tokens(account_id: str, *, force_refresh: bool = False) -> dict:
    tokens = _load_account_tokens(account_id)
    refresh_token = str(tokens.get("refresh_token", ""))
    if force_refresh or (_access_token_expired(tokens) and refresh_token):
        return _refresh_access_token(account_id, refresh_token)
    return tokens


def _queue_post(
    account_id: str,
    text: str,
    reply_to: str = "",
    reason: str = "",
    *,
    plan_id: str = "",
    slot: str = "",
    post_type: str = "",
    scheduled_for: str = "",
    publish_mode: str = "manual",
    auto_approved: bool = False,
    approval_source: str = "",
    media_key: str = "",
    media_type: str = "",
) -> dict:
    table = _posts_table()
    if table is None:
        raise RuntimeError("DynamoDB unavailable")

    duplicate = _find_duplicate_post(account_id, text)
    if duplicate:
        return {
            "duplicate": True,
            "post_id": duplicate.get("post_id", ""),
            "queued_at": duplicate.get("queued_at", ""),
            "status": duplicate.get("status", ""),
        }

    queued_at = utc_now()
    post_id = f"post_{uuid4().hex}"
    item = {
        "PK": f"ACCOUNT#{account_id}",
        "SK": f"POST#{post_id}",
        "post_id": post_id,
        "account_id": account_id,
        "text": text,
        "reply_to": reply_to,
        "status": "queued",
        "queued_at": queued_at,
        "publish_reason": reason or "manual_queue",
        "source_plan_id": plan_id,
        "slot": slot,
        "type": post_type,
        "scheduled_for": scheduled_for,
        "publish_mode": publish_mode,
        "auto_approved": auto_approved,
        "approval_source": approval_source,
        "media_key": media_key,
        "media_type": media_type,
        "retry_count": 0,
        # Retain enough history for practical performance review, then let DynamoDB TTL remove it.
        "expires_at": _expiry_epoch(POST_RETENTION_DAYS),
    }
    table.put_item(Item=item)
    return item


def _upload_image(access_token: str, media_key: str, media_type: str) -> str:
    if not media_key.startswith("uploads/") or media_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise RuntimeError("Unsupported media attachment")
    client = _media_bucket()
    if client is None:
        raise RuntimeError("S3 client unavailable")
    image = client.get_object(Bucket=os.environ["X_MEDIA_BUCKET_NAME"], Key=media_key)["Body"].read()
    if len(image) > 5 * 1024 * 1024:
        raise RuntimeError("Image exceeds the 5 MB upload limit")
    request = Request(
        "https://api.x.com/2/media/upload",
        data=json.dumps({"media": base64.b64encode(image).decode("ascii"), "media_category": "tweet_image", "media_type": media_type}).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as handle:
            media_id = json.loads(handle.read().decode("utf-8")).get("data", {}).get("id", "")
    except HTTPError as exc:
        raise RuntimeError(f"X image upload failed: {exc.code} {exc.read().decode('utf-8', errors='replace')}") from exc
    if not media_id:
        raise RuntimeError("X image upload did not return a media ID")
    return media_id


def _publish_post(access_token: str, text: str, reply_to: str = "", media_key: str = "", media_type: str = "") -> dict:
    payload = {"text": text}
    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to}
    if media_key:
        payload["media"] = {"media_ids": [_upload_image(access_token, media_key, media_type)]}

    request = Request(
        "https://api.x.com/2/tweets",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=20) as handle:
            return json.loads(handle.read().decode("utf-8"))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(
            json.dumps(
                {
                    "event": "x_publish_http_error",
                    "status_code": exc.code,
                    "response_body": error_body,
                    "reply_to": reply_to,
                    "text_preview": text[:80],
                }
            )
        )
        raise RuntimeError(f"X publish failed: {exc.code} {error_body}") from exc


def _should_queue(exc: Exception) -> bool:
    message = str(exc)
    return "CreditsDepleted" in message or "402" in message


def _retry_block_reason(post: dict) -> str:
    if int(post.get("retry_count", 0)) >= MAX_RETRY_COUNT:
        return f"Retry limit reached ({MAX_RETRY_COUNT})"

    last_attempt = _parse_iso8601(str(post.get("last_attempt_at", "")))
    if not last_attempt:
        return ""

    cooldown_until = last_attempt + timedelta(minutes=RETRY_COOLDOWN_MINUTES)
    if datetime.now(timezone.utc) < cooldown_until:
        return f"Retry cooldown active until {cooldown_until.isoformat(timespec='seconds')}"
    return ""


def publish_queued_post(account_id: str, post_id: str, approved: bool) -> dict:
    if not approved:
        return {"provider": "x", "account_id": account_id, "post_id": post_id, "status": "approval_required"}

    item = _get_post_item(account_id, post_id)
    if not item:
        raise RuntimeError(f"Post {post_id} not found")

    if item.get("status") == "published":
        return {
            "provider": "x",
            "account_id": account_id,
            "post_id": post_id,
            "status": "already_published",
            "tweet_id": item.get("tweet_id", ""),
        }

    retry_block = _retry_block_reason(item)
    if retry_block:
        return {
            "provider": "x",
            "account_id": account_id,
            "post_id": post_id,
            "status": "retry_blocked",
            "detail": retry_block,
        }

    duplicate = _find_duplicate_post(account_id, str(item.get("text", "")))
    if duplicate and duplicate.get("post_id") != post_id and duplicate.get("status") == "published":
        _update_post_item(
            account_id,
            post_id,
            {
                "status": "failed",
                "last_error": "Duplicate content already published",
                "last_attempt_at": utc_now(),
                "retry_count": int(item.get("retry_count", 0)) + 1,
            },
        )
        return {
            "provider": "x",
            "account_id": account_id,
            "post_id": post_id,
            "status": "duplicate_blocked",
        }

    _update_post_item(account_id, post_id, {"last_attempt_at": utc_now()})
    tokens = _get_publish_tokens(account_id)
    access_token = tokens.get("access_token", "")
    if not access_token:
        raise RuntimeError(f"No access token saved for {account_id}")

    try:
        publish_result = _publish_post(access_token, str(item.get("text", "")), str(item.get("reply_to", "")), str(item.get("media_key", "")), str(item.get("media_type", "")))
        tweet_id = publish_result.get("data", {}).get("id", "")
        print(
            json.dumps(
                {
                    "event": "x_publish_success",
                    "account_id": account_id,
                    "post_id": post_id,
                    "tweet_id": tweet_id,
                }
            )
        )
        _update_post_item(
            account_id,
            post_id,
            {
                "status": "published",
                "published_at": utc_now(),
                "tweet_id": tweet_id,
                "last_error": "",
            },
        )
        return {
            "provider": "x",
            "account_id": account_id,
            "post_id": post_id,
            "status": "published",
            "published_at": utc_now(),
            "result": publish_result,
        }
    except Exception as exc:
        if "401" in str(exc) and tokens.get("refresh_token"):
            tokens = _get_publish_tokens(account_id, force_refresh=True)
            access_token = tokens.get("access_token", "")
            if access_token:
                try:
                    publish_result = _publish_post(access_token, str(item.get("text", "")), str(item.get("reply_to", "")), str(item.get("media_key", "")), str(item.get("media_type", "")))
                    tweet_id = publish_result.get("data", {}).get("id", "")
                    _update_post_item(
                        account_id,
                        post_id,
                        {
                            "status": "published",
                            "published_at": utc_now(),
                            "tweet_id": tweet_id,
                            "last_error": "",
                        },
                    )
                    return {
                        "provider": "x",
                        "account_id": account_id,
                        "post_id": post_id,
                        "status": "published",
                        "published_at": utc_now(),
                        "result": publish_result,
                    }
                except Exception as retry_exc:
                    exc = retry_exc
        updated_retry_count = int(item.get("retry_count", 0)) + 1
        print(
            json.dumps(
                {
                    "event": "x_publish_failed",
                    "account_id": account_id,
                    "post_id": post_id,
                    "retry_count": updated_retry_count,
                    "error": str(exc),
                }
            )
        )
        _update_post_item(
            account_id,
            post_id,
            {
                "status": "failed",
                "last_error": str(exc),
                "last_attempt_at": utc_now(),
                "retry_count": updated_retry_count,
            },
        )
        return {
            "provider": "x",
            "account_id": account_id,
            "post_id": post_id,
            "status": "failed",
            "retry_count": updated_retry_count,
            "error": str(exc),
        }


def lambda_handler(event, _context):
    try:
        require_automation_key(event)
        body = _parse_event_body(event)
        account_id = body.get("account_id", "").strip()
        text = body.get("text", "").strip()
        reply_to = body.get("reply_to", "").strip()
        # Never coerce untrusted JSON values such as "false" to True.
        if "queue_only" in body and type(body["queue_only"]) is not bool:
            return response(400, {"provider": "x", "error": "queue_only must be a JSON boolean"})
        if "approved" in body and type(body["approved"]) is not bool:
            return response(400, {"provider": "x", "error": "approved must be a JSON boolean"})
        queue_only = body.get("queue_only") is True
        approved = body.get("approved") is True
        scheduled_for = body.get("scheduled_for", "").strip()
        media_key = body.get("media_key", "").strip()
        media_type = body.get("media_type", "").strip()

        if not account_id:
            return response(400, {"provider": "x", "error": "Missing account_id"})
        if not text:
            return response(400, {"provider": "x", "error": "Missing text"})

        if queue_only:
            queued_item = _queue_post(
                account_id,
                text,
                reply_to,
                reason="queue_only",
                scheduled_for=scheduled_for,
                publish_mode="manual",
                auto_approved=False,
                approval_source="",
                media_key=media_key,
                media_type=media_type,
            )
            if queued_item.get("duplicate"):
                return response(
                    200,
                    {
                        "provider": "x",
                        "account_id": account_id,
                        "status": "duplicate_skipped",
                        "post_id": queued_item["post_id"],
                    },
                )
            return response(
                200,
                {
                    "provider": "x",
                    "account_id": account_id,
                    "status": "queued",
                    "queued_at": queued_item["queued_at"],
                    "post_id": queued_item["post_id"],
                },
            )

        if not approved:
            return response(400, {"provider": "x", "error": "Live publish requires approved=true"})

        tokens = _get_publish_tokens(account_id)
        access_token = tokens.get("access_token", "")
        if not access_token:
            return response(400, {"provider": "x", "error": f"No access token saved for {account_id}"})

        try:
            publish_result = _publish_post(access_token, text, reply_to, media_key, media_type)
            tweet_id = publish_result.get("data", {}).get("id", "")
            return response(
                200,
                {
                    "provider": "x",
                    "account_id": account_id,
                    "status": "posted",
                    "posted_at": utc_now(),
                    "tweet_id": tweet_id,
                    "result": publish_result,
                },
            )
        except Exception as exc:
            if "401" in str(exc) and tokens.get("refresh_token"):
                tokens = _get_publish_tokens(account_id, force_refresh=True)
                access_token = tokens.get("access_token", "")
                if access_token:
                    try:
                        publish_result = _publish_post(access_token, text, reply_to, media_key, media_type)
                        tweet_id = publish_result.get("data", {}).get("id", "")
                        return response(
                            200,
                            {
                                "provider": "x",
                                "account_id": account_id,
                                "status": "posted",
                                "posted_at": utc_now(),
                                "tweet_id": tweet_id,
                                "result": publish_result,
                            },
                        )
                    except Exception as retry_exc:
                        exc = retry_exc
            if _should_queue(exc):
                queued_item = _queue_post(
                    account_id,
                    text,
                    reply_to,
                    reason="credits_depleted",
                    scheduled_for=scheduled_for,
                    publish_mode="manual",
                    auto_approved=False,
                    approval_source="",
                )
                return response(
                    200,
                    {
                        "provider": "x",
                        "account_id": account_id,
                        "status": "queued",
                        "queued_at": queued_item["queued_at"],
                        "post_id": queued_item["post_id"],
                        "reason": "credits_depleted",
                        "detail": str(exc),
                    },
                )
            raise
    except PermissionError as exc:
        return response(401, {"provider": "x", "status": "unauthorized", "error": str(exc)})
    except Exception as exc:
        return response(
            502,
            {
                "provider": "x",
                "status": "publish_failed",
                "error": str(exc),
            },
        )
