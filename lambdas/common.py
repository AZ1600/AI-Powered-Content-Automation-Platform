"""Shared helpers for the X-only platform."""

from __future__ import annotations

import base64
import hmac
import hashlib
import json
import os
import secrets
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

try:
    import boto3
except ImportError:  # pragma: no cover
    boto3 = None


def env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ttl_epoch(hours: int = 1) -> int:
    return int((datetime.now(timezone.utc) + timedelta(hours=hours)).timestamp())


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return _json_default(value)
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    return value


def response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(json_safe(body), default=_json_default),
    }


def html_response(status_code: int, body: str) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "text/html; charset=utf-8"},
        "body": body,
    }


def redirect(location: str) -> dict[str, Any]:
    return {
        "statusCode": 302,
        "headers": {"Location": location},
        "body": "",
    }


def random_token(size: int = 32) -> str:
    return secrets.token_urlsafe(size)


def build_s256_pair() -> tuple[str, str]:
    verifier = random_token(48)
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return verifier, challenge


def build_authorize_url(state: str, code_challenge: str) -> str:
    params = {
        "response_type": "code",
        "client_id": env("X_CLIENT_ID"),
        "redirect_uri": f"{env('OAUTH_CALLBACK_BASE_URL').rstrip('/')}/oauth/x/callback",
        "scope": os.environ.get("X_OAUTH_SCOPE", "tweet.read tweet.write users.read offline.access"),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{env('X_AUTHORIZE_URL')}?{urlencode(params)}"


def require_automation_key(event: dict[str, Any]) -> None:
    """Reject write requests that do not originate from the configured automation."""
    headers = event.get("headers") or {}
    supplied = str(headers.get("x-automation-key") or headers.get("X-Automation-Key") or "")
    secret_arn = os.environ.get("AUTOMATION_API_KEY_SECRET_ARN", "").strip()
    if not supplied or not secret_arn or boto3 is None:
        raise PermissionError("Automation API key is required")

    expected = boto3.client("secretsmanager").get_secret_value(SecretId=secret_arn)["SecretString"]
    if not hmac.compare_digest(supplied, expected):
        raise PermissionError("Automation API key is invalid")
