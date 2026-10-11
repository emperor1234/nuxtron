from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest


def test_legacy_and_dependency_auth_aliases_are_canonical() -> None:
    from backend.fastapi.app import auth_utils, deps, legacy_main

    assert legacy_main._b64url_encode is auth_utils.b64url_encode
    assert legacy_main._b64url_decode is auth_utils.b64url_decode
    assert legacy_main._jwt_sign_hs256 is auth_utils.jwt_sign_hs256
    assert legacy_main._jwt_verify_hs256 is auth_utils.jwt_verify_hs256
    assert legacy_main._totp_secret is auth_utils.totp_secret
    assert legacy_main._totp_code is auth_utils.totp_code
    assert legacy_main._totp_verify is auth_utils.totp_verify
    assert legacy_main._hash_email is auth_utils.hash_email
    assert deps._jwt_verify_hs256 is auth_utils.jwt_verify_hs256


def test_rate_limiter_metrics_are_an_immutable_snapshot() -> None:
    from backend.fastapi.app import rate_limiter

    rate_limiter.reset_rate_limits_for_tests()
    rate_limiter.enforce_rate_limit_in_process("snapshot", 2, 60)
    snapshot = rate_limiter.rate_limit_metrics_snapshot()

    assert snapshot.active_keys == 1
    assert snapshot.sample_count == 1
    assert snapshot.bucket_sizes["snapshot"] == 1
    with pytest.raises(TypeError):
        snapshot.bucket_sizes["snapshot"] = 2  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        snapshot.active_keys = 0  # type: ignore[misc]


def test_all_shared_list_stores_have_one_canonical_identity() -> None:
    from backend.fastapi.app import legacy_main, memory_stores
    from backend.fastapi.app.routers import platform_intelligence
    from backend.fastapi.app.services import ai_providers

    aliases = (
        (legacy_main._ai_generated_assets_memory, memory_stores.ai_generated_assets),
        (legacy_main._ace_sites_memory, memory_stores.ace_sites),
        (legacy_main._ace_crawler_events_memory, memory_stores.ace_crawler_events),
        (legacy_main._ace_ssr_cache_memory, memory_stores.ace_ssr_cache),
        (legacy_main._ace_crawler_rules_memory, memory_stores.ace_crawler_rules),
        (legacy_main._ace_audit_results_memory, memory_stores.ace_audit_results),
        (legacy_main._portfolio_sites_memory, memory_stores.portfolio_sites),
        (legacy_main._portfolio_rules_memory, memory_stores.portfolio_rules),
        (legacy_main._portfolio_deployments_memory, memory_stores.portfolio_deployments),
        (legacy_main._live_editor_sessions_memory, memory_stores.live_editor_sessions),
        (legacy_main._live_editor_changes_memory, memory_stores.live_editor_changes),
        (legacy_main._live_editor_history_memory, memory_stores.live_editor_history),
        (ai_providers._ai_generated_assets_memory, memory_stores.ai_generated_assets),
        (platform_intelligence._prompt_versions, memory_stores.platform_prompt_versions),
        (platform_intelligence._lineage_events, memory_stores.platform_lineage_events),
        (platform_intelligence._recovery_queue, memory_stores.platform_recovery_queue),
        (platform_intelligence._agent_sessions, memory_stores.platform_agent_sessions),
        (platform_intelligence._agent_tool_calls, memory_stores.platform_agent_tool_calls),
    )
    assert all(alias is canonical for alias, canonical in aliases)


def test_content_generation_has_one_bootstrap_owned_instance() -> None:
    from backend.fastapi.app import legacy_main, memory_stores
    from backend.fastapi.app.bootstrap.application import create_app
    from backend.fastapi.app.services import content_generation

    create_app()
    canonical = content_generation._get_cg_svc()

    assert legacy_main._get_cg_svc() is canonical
    assert legacy_main._content_generation_jobs_memory is canonical.jobs_memory
    assert canonical.jobs_memory is memory_stores.content_generation_jobs


def test_canonical_reset_clears_shared_owners() -> None:
    from backend.fastapi.app import generated_asset_store, memory_stores
    from backend.fastapi.app.bootstrap.application import create_app
    from backend.fastapi.app.services import content_generation
    from backend.fastapi.app.testing_state import reset_process_state_for_tests

    create_app()
    memory_stores.ai_generated_assets.append({"id": "asset"})
    content_generation._get_cg_svc().jobs_memory.append({"job_id": "job"})
    content_generation._get_cg_svc().note_telemetry("fallback_attempts_total", "test")

    reset_process_state_for_tests()

    assert memory_stores.ai_generated_assets == []
    assert generated_asset_store.append_generated_asset(
        lambda asset_id: {"id": asset_id, "tenant_id": "test"}
    )["id"] == 1
    assert memory_stores.content_generation_jobs == []
    assert content_generation._get_cg_svc().telemetry["fallback_attempts_total"] == 0


def test_default_rate_limit_reset_never_contacts_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app import rate_limiter, security_redis

    def unexpected_redis_access() -> None:
        raise AssertionError("default local reset must not access Redis")

    monkeypatch.setattr(security_redis, "get_sync_redis", unexpected_redis_access)
    rate_limiter.enforce_rate_limit_in_process("local-only-reset", 2, 60)

    rate_limiter.reset_rate_limits_for_tests()

    assert rate_limiter.rate_limit_metrics_snapshot().active_keys == 0


def test_dead_legacy_wiring_surface_is_removed() -> None:
    from backend.fastapi.app import legacy_main
    from backend.fastapi.app.services import platform

    assert not hasattr(legacy_main, "_wire_extracted_services")
    assert not any(name.startswith("_configure_") for name in vars(legacy_main))
    assert "set_rate_limiter" not in platform.__all__


def test_owner_managed_generated_assets_are_reset_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app import generated_asset_store, memory_stores
    from backend.fastapi.app.testing_state import reset_process_state_for_tests

    assert all(
        store is not generated_asset_store.ai_generated_assets
        for store in memory_stores.iter_process_stores()
    )
    generated_asset_store.append_generated_asset(
        lambda asset_id: {"id": asset_id, "tenant_id": "test"}
    )

    calls = 0
    original_reset = generated_asset_store.reset_generated_assets_for_tests

    def tracked_reset() -> None:
        nonlocal calls
        calls += 1
        original_reset()

    monkeypatch.setattr(generated_asset_store, "reset_generated_assets_for_tests", tracked_reset)
    reset_process_state_for_tests()

    assert calls == 1
    assert generated_asset_store.ai_generated_assets == []
