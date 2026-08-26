#!/usr/bin/env python3
"""Save and queue One Piece X plans into the live publishing platform."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Set this after deployment. Keeping the endpoint out of source avoids coupling
# the content automation to a lost or replaced AWS account.
DEFAULT_BASE_URL = os.environ.get("ONE_PIECE_X_PLATFORM_BASE_URL", "").strip()
SUPPORTED_ACCOUNTS = ("account1", "account2")


def _load_plan(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _validate_plan(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    plan_date = str(plan.get("plan_date", "")).strip()
    accounts = plan.get("accounts")

    if not plan_date:
        errors.append("Missing top-level plan_date")
    if not isinstance(accounts, dict) or not accounts:
        errors.append("Missing top-level accounts map")
        return errors

    world_radar = plan.get("world_radar", [])
    if world_radar is not None and not isinstance(world_radar, list):
        errors.append("world_radar must be a list when provided")
    elif isinstance(world_radar, list):
        for index, item in enumerate(world_radar, start=1):
            if not isinstance(item, dict):
                errors.append(f"world_radar item {index} must be an object")
                continue
            for field in ("title", "category", "why_now", "source_url"):
                if not str(item.get(field, "")).strip():
                    errors.append(f"world_radar item {index} missing {field}")

    for account_id in SUPPORTED_ACCOUNTS:
        if account_id not in accounts:
            continue
        account_payload = accounts[account_id]
        posts = account_payload.get("posts")
        if not isinstance(posts, list) or not posts:
            errors.append(f"{account_id}: posts must be a non-empty list")
            continue
        for index, post in enumerate(posts, start=1):
            if not str(post.get("slot", "")).strip():
                errors.append(f"{account_id}: post {index} missing slot")
            if not str(post.get("type", "")).strip():
                errors.append(f"{account_id}: post {index} missing type")
            if not str(post.get("text", "")).strip():
                errors.append(f"{account_id}: post {index} missing text")

    return errors


def _post_json(base_url: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Automation-Key": os.environ.get("ONE_PIECE_X_PLATFORM_API_KEY", ""),
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as handle:
            raw = handle.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{path} failed with HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"{path} failed: {exc.reason}") from exc

    parsed = json.loads(raw)
    body = parsed.get("body")
    if isinstance(body, str):
        return json.loads(body)
    return parsed


def _save_and_queue_account(
    *,
    base_url: str,
    plan_date: str,
    account_id: str,
    payload: dict[str, Any],
    world_radar: list[dict[str, Any]],
    skip_queue: bool,
) -> dict[str, Any]:
    save_payload = {
        "account_id": account_id,
        "plan_date": plan_date,
        "posts": payload["posts"],
        "notes": payload.get("notes", ""),
        "world_radar": world_radar,
    }
    saved = _post_json(base_url, "/x/plan", save_payload)
    result: dict[str, Any] = {"saved": saved}
    if skip_queue:
        result["queued"] = {"status": "queue_skipped"}
        return result

    queued = _post_json(
        base_url,
        "/x/plan/queue",
        {
            "account_id": account_id,
            "plan_id": saved.get("plan_id", ""),
            "plan_sk": saved.get("plan_sk", ""),
        },
    )
    result["queued"] = queued
    return result


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-file", required=True, help="Path to JSON plan file")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Live platform base URL")
    parser.add_argument(
        "--accounts",
        nargs="*",
        choices=SUPPORTED_ACCOUNTS,
        default=list(SUPPORTED_ACCOUNTS),
        help="Accounts to send to the live platform",
    )
    parser.add_argument("--skip-queue", action="store_true", help="Save plans without queueing them")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the payload only")
    args = parser.parse_args(argv)

    if not args.dry_run and not args.base_url:
        parser.error("Set ONE_PIECE_X_PLATFORM_BASE_URL or pass --base-url")
    if not args.dry_run and not os.environ.get("ONE_PIECE_X_PLATFORM_API_KEY", "").strip():
        parser.error("Set ONE_PIECE_X_PLATFORM_API_KEY before saving or queueing a plan")

    plan = _load_plan(Path(args.plan_file))
    errors = _validate_plan(plan)
    if errors:
        print(json.dumps({"status": "invalid_plan", "errors": errors}, indent=2))
        return 1

    selected_accounts = args.accounts or list(SUPPORTED_ACCOUNTS)
    accounts_payload = plan["accounts"]
    results: dict[str, Any] = {
        "status": "ok",
        "plan_date": plan["plan_date"],
        "base_url": args.base_url,
        "accounts": {},
    }

    for account_id in selected_accounts:
        account_payload = accounts_payload.get(account_id)
        if not account_payload:
            results["accounts"][account_id] = {"status": "missing_from_plan"}
            continue
        if args.dry_run:
            results["accounts"][account_id] = {
                "status": "dry_run",
                "notes": account_payload.get("notes", ""),
                "post_count": len(account_payload["posts"]),
                "posts": account_payload["posts"],
                "world_radar": plan.get("world_radar", []),
            }
            continue
        results["accounts"][account_id] = _save_and_queue_account(
            base_url=args.base_url,
            plan_date=plan["plan_date"],
            account_id=account_id,
            payload=account_payload,
            world_radar=plan.get("world_radar", []),
            skip_queue=args.skip_queue,
        )

    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
