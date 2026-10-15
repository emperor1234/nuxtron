"""Adobe PDF Services processing adapter."""

from __future__ import annotations

from typing import Any
import json
import os
import urllib.parse

from .provider_http import provider_request_failed
from .provider_http import provider_unavailable
from .provider_http import request_provider_api
from .provider_http import validate_public_media_source_url


async def _dispatch_adobe_pdf(
    storage_key: str, operation: str, params: dict[str, Any], source_url: str | None
) -> dict[str, Any]:
    """Submit document work to Adobe using pinned provider egress and an explicit public source."""
    client_id = os.getenv("ADOBE_PDF_CLIENT_ID", "")
    client_secret = os.getenv("ADOBE_PDF_CLIENT_SECRET", "")
    if not (client_id and client_secret):
        return provider_unavailable(
            "adobe_pdf", "PROVIDER_CREDENTIALS_MISSING", "Adobe PDF credentials are not configured."
        )
    if not source_url:
        return provider_unavailable(
            "adobe_pdf", "MEDIA_SOURCE_URL_REQUIRED", "A public HTTPS document source URL is required."
        )
    try:
        source_url = await validate_public_media_source_url(source_url)
    except (TypeError, ValueError):
        return provider_unavailable(
            "adobe_pdf",
            "MEDIA_SOURCE_URL_NOT_ALLOWED",
            "The media source URL is not a permitted public HTTPS destination.",
        )

    token_payload = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": "openid,AdobeID,DCAPI",
        }
    ).encode()
    try:
        token_response = await request_provider_api(
            "POST",
            "https://ims-na1.adobelogin.com/ims/token/v3",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            body=token_payload,
        )
    except Exception as exc:
        return provider_request_failed("adobe_pdf", exc)
    if token_response.status_code >= 400:
        return {
            "provider": "adobe_pdf",
            "status": "error",
            "error_code": "PROVIDER_AUTH_FAILED",
            "error": "Adobe authentication failed.",
        }
    try:
        access_token = str(token_response.json().get("access_token", ""))
    except (ValueError, AttributeError):
        access_token = ""
    if not access_token:
        return {
            "provider": "adobe_pdf",
            "status": "error",
            "error_code": "PROVIDER_AUTH_FAILED",
            "error": "Adobe authentication did not return an access token.",
        }

    operation_paths = {
        "convert": "exportpdf",
        "extract": "extractpdf",
        "compress": "compresspdf",
        "merge": "combinepdf",
        "split": "splitpdf",
        "ocr": "ocr",
        "auto": "exportpdf",
    }
    operation_path = operation_paths.get(operation, "exportpdf")
    operation_payload = json.dumps(
        {"assetID": source_url, "targetFormat": params.get("target_format", "docx")}
    ).encode()
    try:
        response = await request_provider_api(
            "POST",
            f"https://pdf-services.adobe.io/operation/{operation_path}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "x-api-key": client_id,
                "Content-Type": "application/json",
            },
            body=operation_payload,
        )
        if response.status_code >= 400:
            return {
                "provider": "adobe_pdf",
                "status": "error",
                "error_code": "PROVIDER_REJECTED_REQUEST",
                "error": "Adobe PDF Services rejected the document request.",
            }
        result = response.json()
        return {
            "provider": "adobe_pdf",
            "status": "processing",
            "mode": "live",
            "job_id": result.get("jobID"),
            "location": result.get("location"),
            "operation": operation_path,
        }
    except Exception as exc:
        return provider_request_failed("adobe_pdf", exc)
