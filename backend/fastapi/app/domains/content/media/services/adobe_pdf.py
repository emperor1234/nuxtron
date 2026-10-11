"""Adobe PDF Services processing adapter."""

from __future__ import annotations
from typing import Any
import asyncio
import os


async def _dispatch_adobe_pdf(
    storage_key: str, operation: str, params: dict[str, Any], source_url: str | None
) -> dict[str, Any]:
    """
    Adobe PDF Services API — enterprise document conversion, extraction, OCR.
    Docs: https://developer.adobe.com/document-services/docs/apis/
    Env vars: ADOBE_PDF_CLIENT_ID, ADOBE_PDF_CLIENT_SECRET
    """
    await asyncio.sleep(0)
    client_id = os.getenv("ADOBE_PDF_CLIENT_ID", "")
    client_secret = os.getenv("ADOBE_PDF_CLIENT_SECRET", "")
    if not (client_id and client_secret):
        return {
            "provider": "adobe_pdf",
            "status": "dispatched",
            "mode": "credentials-not-configured",
            "message": "Set ADOBE_PDF_CLIENT_ID and ADOBE_PDF_CLIENT_SECRET to enable live dispatch.",
            "would_call": "https://pdf-services.adobe.io/operation/exportpdf",
            "operation": operation,
        }
    import json as _json
    import urllib.parse
    import urllib.request

    token_payload = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": "openid,AdobeID,DCAPI",
        }
    ).encode()
    token_req = urllib.request.Request("https://ims-na1.adobelogin.com/ims/token/v3", data=token_payload, method="POST")
    token_req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(token_req, timeout=30) as resp:
            token_data = _json.loads(resp.read())
            access_token = token_data.get("access_token", "")
    except Exception as exc:
        return {"provider": "adobe_pdf", "status": "error", "mode": "live", "error": f"Auth: {exc}"}
    op_map = {
        "convert": "exportpdf",
        "extract": "extractpdf",
        "compress": "compresspdf",
        "merge": "combinepdf",
        "split": "splitpdf",
        "ocr": "ocr",
        "auto": "exportpdf",
    }
    op_path = op_map.get(operation, "exportpdf")
    op_payload = _json.dumps(
        {"assetID": source_url or f"s3://raw-input/{storage_key}", "targetFormat": params.get("target_format", "docx")}
    ).encode()
    op_req = urllib.request.Request(
        f"https://pdf-services.adobe.io/operation/{op_path}", data=op_payload, method="POST"
    )
    op_req.add_header("Authorization", f"Bearer {access_token}")
    op_req.add_header("x-api-key", client_id)
    op_req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(op_req, timeout=30) as resp:
            result = _json.loads(resp.read())
            return {
                "provider": "adobe_pdf",
                "status": "processing",
                "mode": "live",
                "job_id": result.get("jobID"),
                "location": result.get("location"),
                "operation": op_path,
            }
    except Exception as exc:
        return {"provider": "adobe_pdf", "status": "error", "mode": "live", "error": str(exc)}
