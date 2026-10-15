from __future__ import annotations

import httpx
import pytest

from backend.fastapi.app.domains.content.media.services import adobe_pdf
from backend.fastapi.app.domains.content.media.services import dispatch_deepgram
from backend.fastapi.app.domains.content.media.services import processing
from backend.fastapi.app.domains.content.media.services import provider_http
from backend.fastapi.app.domains.identity.secure_egress import OutboundTarget
from backend.fastapi.app.domains.identity.secure_egress import UnsafeOutboundURL


@pytest.mark.asyncio
async def test_provider_request_uses_pinned_target_and_bounded_response(monkeypatch: pytest.MonkeyPatch) -> None:
    target = OutboundTarget(
        url="https://api.example.test/v1/jobs",
        host="api.example.test",
        port=443,
        address="93.184.216.34",
    )
    resolved_urls: list[str] = []
    sent: list[tuple[str, OutboundTarget, dict[str, object]]] = []

    async def resolve(url: str) -> OutboundTarget:
        resolved_urls.append(url)
        return target

    async def send(method: str, resolved_target: OutboundTarget, **kwargs: object) -> httpx.Response:
        sent.append((method, resolved_target, kwargs))
        return httpx.Response(202, content=b"accepted")

    monkeypatch.setattr(provider_http, "resolve_outbound_target_async", resolve)
    monkeypatch.setattr(provider_http, "outbound_async_request", send)

    response = await provider_http.request_provider_api(
        "POST",
        target.url,
        headers={"Authorization": "Bearer test-token"},
        body=b"{}",
    )

    assert response.status_code == 202
    assert resolved_urls == [target.url]
    assert len(sent) == 1
    method, pinned_target, options = sent[0]
    assert method == "POST"
    assert pinned_target == target
    assert options["headers"] == {"Authorization": "Bearer test-token"}
    assert options["content"] == b"{}"
    assert options["max_response_bytes"] == provider_http.MAX_PROVIDER_RESPONSE_BYTES


@pytest.mark.asyncio
async def test_provider_source_url_must_be_present_and_public_https(monkeypatch: pytest.MonkeyPatch) -> None:
    target = OutboundTarget(
        url="https://objects.example.test/signed/source",
        host="objects.example.test",
        port=443,
        address="93.184.216.34",
    )
    resolved_urls: list[str] = []

    async def resolve(url: str) -> OutboundTarget:
        resolved_urls.append(url)
        return target

    monkeypatch.setattr(provider_http, "resolve_outbound_target_async", resolve)

    with pytest.raises(ValueError, match="MEDIA_SOURCE_URL_REQUIRED"):
        await provider_http.validate_public_media_source_url(None)
    assert await provider_http.validate_public_media_source_url(target.url) == target.url
    assert resolved_urls == [target.url]

    async def reject_private(_url: str) -> OutboundTarget:
        raise UnsafeOutboundURL("blocked")

    monkeypatch.setattr(provider_http, "resolve_outbound_target_async", reject_private)
    with pytest.raises(UnsafeOutboundURL):
        await provider_http.validate_public_media_source_url("https://127.0.0.1/private")


def test_media_validation_token_uses_domain_separated_configured_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app.domains.content.media.services.processing import _issue_validation_token
    from backend.fastapi.app.domains.content.media.services.processing import _verify_validation_token

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("FASTAPI_SECRET", raising=False)
    monkeypatch.setenv("APP_ENC_KEY", "explicit-test-root-key")
    token = _issue_validation_token("org-a", "raw-input/org-a/a.png", "image/png")
    assert _verify_validation_token(token, "org-a", "raw-input/org-a/a.png", "image/png")
    assert not _verify_validation_token(token, "org-b", "raw-input/org-b/a.png", "image/png")


@pytest.mark.parametrize("secret", ["", "short", "replace-with-at-least-32-random-characters"])
def test_production_validation_token_requires_operator_secret(
    secret: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastapi import HTTPException
    from backend.fastapi.app.domains.content.media.services.processing import _issue_validation_token

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("FASTAPI_SECRET", secret)
    monkeypatch.setenv("APP_ENC_KEY", "present-but-not-the-production-validation-key")
    with pytest.raises(HTTPException) as error:
        _issue_validation_token("org-a", "raw-input/org-a/a.png", "image/png")
    assert error.value.status_code == 503


_PROVIDER_CASES = [
    (
        "cloudinary",
        processing._dispatch_cloudinary,
        processing,
        ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"),
    ),
    ("mux", processing._dispatch_mux, processing, ("MUX_TOKEN_ID", "MUX_TOKEN_SECRET")),
    ("bunny", processing._dispatch_bunny, processing, ("BUNNY_API_KEY", "BUNNY_STORAGE_ZONE")),
    ("assemblyai", processing._dispatch_assemblyai, processing, ("ASSEMBLYAI_API_KEY",)),
    ("deepgram", dispatch_deepgram._dispatch_deepgram, dispatch_deepgram, ("DEEPGRAM_API_KEY",)),
    (
        "adobe_pdf",
        adobe_pdf._dispatch_adobe_pdf,
        adobe_pdf,
        ("ADOBE_PDF_CLIENT_ID", "ADOBE_PDF_CLIENT_SECRET"),
    ),
]


@pytest.mark.parametrize("provider,dispatch,owner,credential_vars", _PROVIDER_CASES)
@pytest.mark.asyncio
async def test_provider_without_credentials_is_unavailable_without_network(
    provider: str,
    dispatch,
    owner,
    credential_vars: tuple[str, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in credential_vars:
        monkeypatch.delenv(name, raising=False)

    async def unexpected_request(*_args, **_kwargs) -> httpx.Response:
        pytest.fail(f"{provider} attempted a request without credentials")

    monkeypatch.setattr(owner, "request_provider_api", unexpected_request)
    result = await dispatch("raw-input/org/source.bin", "auto", {}, "https://media.example.test/source.bin")

    assert result["status"] == "unavailable"
    assert result["error_code"] == "PROVIDER_CREDENTIALS_MISSING"


@pytest.mark.asyncio
async def test_bunny_does_not_send_an_empty_placeholder_upload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUNNY_API_KEY", "operator-key")
    monkeypatch.setenv("BUNNY_STORAGE_ZONE", "operator-zone")
    monkeypatch.setattr(
        processing,
        "request_provider_api",
        lambda *_args, **_kwargs: pytest.fail("unimplemented Bunny upload must not make a request"),
    )

    result = await processing._dispatch_bunny("raw-input/org/image.jpg", "auto", {}, None)

    assert result["status"] == "unavailable"
    assert result["error_code"] == "BUNNY_UPLOAD_ADAPTER_UNAVAILABLE"


@pytest.mark.asyncio
async def test_cloudinary_uses_fixed_origin_and_pinned_request_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "operator-cloud")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "operator-api-key")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "operator-api-secret")
    calls: list[tuple[str, str, dict[str, str], bytes]] = []

    async def validate_source(url: str) -> str:
        assert url == "https://objects.example.test/signed/photo.png"
        return url

    async def send(method: str, url: str, *, headers: dict[str, str], body: bytes) -> httpx.Response:
        calls.append((method, url, headers, body))
        return httpx.Response(200, json={"public_id": "photo", "secure_url": "https://res.cloudinary.com/photo"})

    monkeypatch.setattr(processing, "validate_public_media_source_url", validate_source)
    monkeypatch.setattr(processing, "request_provider_api", send)

    result = await processing._dispatch_cloudinary(
        "raw-input/org/photo.png",
        "resize",
        {"width": 800},
        "https://objects.example.test/signed/photo.png",
    )

    assert result["status"] == "complete"
    assert len(calls) == 1
    method, url, headers, body = calls[0]
    assert method == "POST"
    assert url == "https://api.cloudinary.com/v1_1/operator-cloud/auto/upload"
    assert headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert b"objects.example.test" in body
