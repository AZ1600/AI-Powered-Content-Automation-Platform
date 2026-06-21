"""Generates a daily plan for a connected X account."""

from __future__ import annotations

import json
from datetime import datetime

from common import response, utc_now

ACCOUNT_WINDOWS = {
    "account1": ["08:30", "11:30", "14:30", "17:30", "20:30"],
    "account2": ["09:30", "12:30", "15:30", "18:30", "21:30"],
}

ACCOUNT_BLUEPRINTS = {
    "account1": {
        "notes": "Manga-first day. Keep spoilers contained and use debate hooks, theory prompts, and chapter-energy reactions.",
        "templates": [
            ("hook", "Which One Piece manga panel still hits hardest on a reread?"),
            ("reaction", "If a new reader just reached THAT turning point, what is the one non-spoiler thing you would tell them?"),
            ("theory", "What is one long-running One Piece theory you still think has a real chance of paying off?"),
            ("debate", "Which Straw Hat had the strongest post-timeskip manga character stretch?"),
            ("cta", "Drop your hottest spoiler-safe manga take in one sentence."),
        ],
    },
    "account2": {
        "notes": "Anime-safe day. Focus on episode reactions, callbacks, emotional payoff, and broad fan engagement without manga spoilers.",
        "templates": [
            ("hook", "What is the most underrated emotional payoff in the One Piece anime?"),
            ("callback", "Which older One Piece arc deserves way more respect when you rewatch it now?"),
            ("breakdown", "What is one anime-only detail or direction choice that made a scene hit harder for you?"),
            ("debate", "Which Straw Hat voice performance has elevated the character the most for you?"),
            ("cta", "If you had to recommend one spoiler-light One Piece episode to hook a friend, which one is it?"),
        ],
    },
}


def _parse_event_body(event) -> dict:
    raw_body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raise RuntimeError("Base64-encoded payloads are not supported in this MVP")
    return json.loads(raw_body)


def _date_theme(plan_date: str) -> str:
    try:
        day_name = datetime.fromisoformat(plan_date).strftime("%A")
    except ValueError:
        day_name = "Daily"
    return f"{day_name} One Piece engagement run"


def _build_plan(account_id: str, plan_date: str) -> dict:
    blueprint = ACCOUNT_BLUEPRINTS[account_id]
    windows = ACCOUNT_WINDOWS[account_id]
    posts = []
    for slot, template in zip(windows, blueprint["templates"]):
        post_type, text = template
        posts.append({"slot": slot, "type": post_type, "text": text})
    return {
        "provider": "x",
        "account_id": account_id,
        "status": "plan_generated",
        "plan_date": plan_date,
        "generated_at": utc_now(),
        "notes": f"{_date_theme(plan_date)}. {blueprint['notes']}",
        "posts": posts,
    }


def lambda_handler(event, _context):
    try:
        body = _parse_event_body(event)
        account_id = body.get("account_id", "").strip()
        plan_date = body.get("plan_date", "").strip()

        if account_id not in ACCOUNT_BLUEPRINTS:
            return response(400, {"provider": "x", "error": "Unsupported account_id"})
        if not plan_date:
            return response(400, {"provider": "x", "error": "Missing plan_date"})

        return response(200, _build_plan(account_id, plan_date))
    except Exception as exc:
        return response(502, {"provider": "x", "status": "plan_generate_failed", "error": str(exc)})
