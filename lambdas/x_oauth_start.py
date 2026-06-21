"""Starts X OAuth for one managed account."""

from __future__ import annotations

import os
from urllib.parse import parse_qs

from common import build_authorize_url, build_s256_pair, redirect, response, ttl_epoch, utc_now, random_token

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


def lambda_handler(event, _context):
    account_id = _query_params(event).get("account_id", "account1").strip() or "account1"
    state = random_token(18)
    code_verifier, code_challenge = build_s256_pair()

    if boto3 is None:
        return response(500, {"error": "boto3 unavailable"})

    table = boto3.resource("dynamodb").Table(os.environ["X_STATE_TABLE_NAME"])
    table.put_item(
        Item={
            "PK": f"STATE#{state}",
            "SK": "X",
            "account_id": account_id,
            "code_verifier": code_verifier,
            "created_at": utc_now(),
            "expires_at": ttl_epoch(1),
        }
    )

    return redirect(build_authorize_url(state, code_challenge))
