"""Serves the One Piece X operations dashboard."""

from pathlib import Path

from common import html_response


def lambda_handler(event, _context):
    """Load the dashboard as a separate asset so the UI can evolve independently."""
    html = Path(__file__).with_name("dashboard.html").read_text(encoding="utf-8")
    return html_response(200, html)
