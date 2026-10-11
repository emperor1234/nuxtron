"""Tenant-bound OAuth state and provider authorization-code exchange."""

from __future__ import annotations
from fastapi import HTTPException
from typing import Any
import base64
import hashlib
import hmac
import httpx
import json
import os
import time


def _oauth_state_secret() -> str:
    return (
        os.getenv("OAUTH_STATE_SIGNING_KEY", "").strip()
        or os.getenv("JWT_SIGNING_KEY", "").strip()
        or os.getenv("FASTAPI_API_KEY", "").strip()
    )


def _encode_oauth_state(
    *, tenant_id: str, platform: str, redirect_uri: str, expires_at: int, code_verifier: str = ""
) -> str:
    secret = _oauth_state_secret()
    if not secret:
        raise HTTPException(status_code=503, detail="OAuth state signing is not configured.")
    raw = json.dumps(
        {
            "tenant_id": tenant_id,
            "platform": platform,
            "redirect_uri": redirect_uri,
            "exp": expires_at,
            "code_verifier": code_verifier,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    encoded = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    signature = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def _decode_oauth_state(state: str, *, tenant_id: str, platform: str, redirect_uri: str) -> dict[str, Any]:
    secret = _oauth_state_secret()
    try:
        encoded, signature = state.split(".", 1)
        expected = hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not secret or not hmac.compare_digest(signature, expected):
            raise ValueError("signature")
        padded = encoded + "=" * (-len(encoded) % 4)
        claims = json.loads(base64.urlsafe_b64decode(padded).decode())
        if (
            claims.get("tenant_id") != tenant_id
            or claims.get("platform") != platform
            or claims.get("redirect_uri") != redirect_uri
            or (int(claims.get("exp", 0)) < int(time.time()))
        ):
            raise ValueError("claims")
        return claims
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.") from exc


def _exchange_oauth_code(platform: str, code: str, redirect_uri: str, code_verifier: str = "") -> dict[str, Any]:
    client_id = os.getenv(
        {
            "twitter": "TWITTER_CLIENT_ID",
            "facebook": "FACEBOOK_APP_ID",
            "instagram": "FACEBOOK_APP_ID",
            "linkedin": "LINKEDIN_CLIENT_ID",
            "tiktok": "TIKTOK_CLIENT_ID",
        }[platform],
        "",
    ).strip()
    client_secret = os.getenv(
        {
            "twitter": "TWITTER_CLIENT_SECRET",
            "facebook": "FACEBOOK_APP_SECRET",
            "instagram": "FACEBOOK_APP_SECRET",
            "linkedin": "LINKEDIN_CLIENT_SECRET",
            "tiktok": "TIKTOK_CLIENT_SECRET",
        }[platform],
        "",
    ).strip()
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail=f"{platform} OAuth client credentials are not configured.")
    if platform in {"facebook", "instagram"}:
        response = httpx.get(
            "https://graph.facebook.com/v18.0/oauth/access_token",
            params={"client_id": client_id, "client_secret": client_secret, "redirect_uri": redirect_uri, "code": code},
            timeout=10,
        )
    elif platform == "linkedin":
        response = httpx.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=10,
        )
    elif platform == "tiktok":
        response = httpx.post(
            "https://open.tiktokapis.com/v2/oauth/token/",
            data={
                "client_key": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
    else:
        response = httpx.post(
            "https://api.twitter.com/2/oauth2/token",
            data={
                "code": code,
                "grant_type": "authorization_code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
            },
            auth=(client_id, client_secret),
            timeout=10,
        )
    if not response.is_success:
        raise HTTPException(status_code=502, detail=f"{platform} OAuth token exchange failed.")
    data = response.json()
    if not isinstance(data, dict) or not str(data.get("access_token", "") or "").strip():
        raise HTTPException(status_code=502, detail=f"{platform} OAuth provider returned no access token.")
    return data
