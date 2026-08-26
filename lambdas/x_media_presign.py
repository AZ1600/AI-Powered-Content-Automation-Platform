"""Creates short-lived private S3 upload URLs for dashboard image attachments."""

from __future__ import annotations

import json
import os
from pathlib import PurePath
from uuid import uuid4

from common import require_automation_key, response

try:
    import boto3
except ImportError:  # pragma: no cover
    boto3 = None


ALLOWED_MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp"}


def lambda_handler(event, _context):
    try:
        require_automation_key(event)
        body = json.loads(event.get("body") or "{}")
        filename = PurePath(str(body.get("file_name", "image"))).name
        media_type = str(body.get("content_type", "")).lower().strip()
        if media_type not in ALLOWED_MEDIA_TYPES:
            return response(400, {"provider": "x", "error": "Only JPEG, PNG, and WebP images are supported"})
        if boto3 is None:
            raise RuntimeError("S3 client unavailable")

        key = f"uploads/{uuid4().hex}-{filename}"
        upload_url = boto3.client("s3").generate_presigned_url(
            "put_object",
            Params={"Bucket": os.environ["X_MEDIA_BUCKET_NAME"], "Key": key, "ContentType": media_type},
            ExpiresIn=300,
        )
        return response(200, {"provider": "x", "media_key": key, "media_type": media_type, "upload_url": upload_url})
    except PermissionError as exc:
        return response(401, {"provider": "x", "status": "unauthorized", "error": str(exc)})
    except Exception as exc:
        return response(502, {"provider": "x", "status": "media_presign_failed", "error": str(exc)})
