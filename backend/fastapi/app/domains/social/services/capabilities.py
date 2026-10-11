"""Social Workspace capabilities service."""

from .workspace import _sw_http_error
import os


def _strict_social_mode_enabled() -> bool:
    raw = os.getenv("SOCIAL_STRICT_NO_FALLBACK")
    if raw is None:
        raw = os.getenv("NEXT_PUBLIC_STRICT_NO_MOCK")
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _require_openai_for_strict_social(feature_name: str) -> None:
    if not _strict_social_mode_enabled():
        return
    if not os.getenv("OPENAI_API_KEY", "").strip():
        raise _sw_http_error(status_code=503, detail=f"Strict social mode requires OPENAI_API_KEY for {feature_name}.")


def _require_any_env_for_strict_social(env_keys: list[str], feature_name: str) -> None:
    if not _strict_social_mode_enabled():
        return
    if any((os.getenv(key, "").strip() for key in env_keys)):
        return
    keys_label = ", ".join(env_keys)
    raise _sw_http_error(
        status_code=503, detail=f"Strict social mode requires one of [{keys_label}] for {feature_name}."
    )


def _require_hubspot_for_strict_social(feature_name: str) -> None:
    if not _strict_social_mode_enabled():
        return
    if not os.getenv("HUBSPOT_ACCESS_TOKEN", "").strip():
        raise _sw_http_error(
            status_code=503, detail=f"Strict social mode requires HUBSPOT_ACCESS_TOKEN for {feature_name}."
        )
