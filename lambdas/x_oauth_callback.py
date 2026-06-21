"""Handles X OAuth callback and persists connected tokens."""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode
from urllib.request import Request, urlopen

from common import response, utc_now

try:
    import boto3
except ImportError:  # pragma: no cover
    boto3 = None


def _query_params(event):
    if event.get("queryStringParameters"):
        return event["queryStringParameters"]
    raw = event.get("rawQueryString", "")
    parsed = parse_qs(raw)
    return {key: values[0] for key, values in parsed.items()}


def _table(name: str):
    if boto3 is None:
        return None
    return boto3.resource("dynamodb").Table(os.environ[name])


def _secrets():
    return boto3.client("secretsmanager") if boto3 is not None else None


def _read_secret(secret_name: str) -> str:
    client = _secrets()
    if client is None:
        raise RuntimeError("Secrets Manager client unavailable")
    return client.get_secret_value(SecretId=secret_name)["SecretString"]


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


def _save_connected_account(account_id: str, token_payload: dict) -> None:
    token_secret_name = f"{os.environ['SECRETS_PREFIX']}/accounts/{account_id}"
    table = _table("X_CONNECTIONS_TABLE_NAME")
    if table is not None:
        table.put_item(
            Item={
                "PK": f"ACCOUNT#{account_id}",
                "SK": "X",
                "account_id": account_id,
                "connected_at": utc_now(),
                "token_secret_name": token_secret_name,
            }
        )

    client = _secrets()
    if client is None:
        raise RuntimeError("Secrets Manager client unavailable")
    payload = json.dumps(_with_token_metadata(token_payload))
    try:
        client.create_secret(Name=token_secret_name, SecretString=payload)
    except client.exceptions.ResourceExistsException:
        client.put_secret_value(SecretId=token_secret_name, SecretString=payload)


def _get_state_item(state: str):
    table = _table("X_STATE_TABLE_NAME")
    if table is None:
        raise RuntimeError("DynamoDB unavailable")
    result = table.get_item(Key={"PK": f"STATE#{state}", "SK": "X"})
    return result.get("Item")


def _token_request_variants(code: str, redirect_uri: str, verifier: str) -> list[tuple[dict, dict]]:
    client_id = os.environ["X_CLIENT_ID"]
    client_secret = _read_secret(os.environ["X_CLIENT_SECRET_SECRET_NAME"])
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")

    base_body = {
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
    }
    return [
        (
            base_body,
            {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {basic}",
            },
        ),
        (
            {**base_body, "client_id": client_id},
            {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {basic}",
            },
        ),
        (
            {**base_body, "client_id": client_id, "client_secret": client_secret},
            {
                "Content-Type": "application/x-www-form-urlencoded",
            },
        ),
    ]


def _exchange_code(code: str, redirect_uri: str, verifier: str) -> dict:
    token_url = os.environ["X_TOKEN_URL"]
    failures = []

    for body, headers in _token_request_variants(code, redirect_uri, verifier):
        request = Request(token_url, data=urlencode(body).encode("utf-8"), headers=headers, method="POST")
        try:
            with urlopen(request, timeout=20) as handle:
                return json.loads(handle.read().decode("utf-8"))
        except HTTPError as exc:
            failure_text = exc.read().decode("utf-8", errors="replace")
            failures.append(
                {
                    "status": exc.code,
                    "body": failure_text,
                    "used_auth_header": "Authorization" in headers,
                    "included_client_id": "client_id" in body,
                    "included_client_secret": "client_secret" in body,
                }
            )

    raise RuntimeError(json.dumps({"token_exchange_failures": failures}))


def lambda_handler(event, _context):
    params = _query_params(event)
    if "error" in params:
        return response(400, {"provider": "x", "status": "authorization_failed", "details": params})

    state = params.get("state", "")
    code = params.get("code", "")
    if not state or not code:
        return response(400, {"provider": "x", "error": "Missing code or state"})

    state_item = _get_state_item(state)
    if not state_item:
        return response(400, {"provider": "x", "error": "Unknown or expired state"})

    redirect_uri = f"{os.environ['OAUTH_CALLBACK_BASE_URL'].rstrip('/')}/oauth/x/callback"
    try:
        token_payload = _exchange_code(code, redirect_uri, state_item["code_verifier"])
        _save_connected_account(state_item["account_id"], token_payload)
        return response(
            200,
            {
                "provider": "x",
                "account_id": state_item["account_id"],
                "status": "connected",
                "connected_at": utc_now(),
            },
        )
    except Exception as exc:
        return response(
            502,
            {
                "provider": "x",
                "account_id": state_item["account_id"],
                "status": "token_exchange_failed",
                "error": str(exc),
            },
        )
