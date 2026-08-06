from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _load_enforce_module(repo_root: Path):
    script_path = repo_root / "scripts" / "ci" / "enforce_readiness_gate.py"
    spec = importlib.util.spec_from_file_location("enforce_readiness_gate", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_enforce_readiness_gate_writes_strict_live_remediation_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    repo_root = Path(__file__).resolve().parents[4]
    module = _load_enforce_module(repo_root)

    fake_root = tmp_path
    test_results = fake_root / "test-results"
    ci_dir = fake_root / "scripts" / "ci"
    test_results.mkdir(parents=True, exist_ok=True)
    ci_dir.mkdir(parents=True, exist_ok=True)

    (test_results / "semrush-readiness-report.json").write_text(
        json.dumps(
            {
                "chart": [
                    {
                        "check": "production_gate",
                        "details": {
                            "gate": {
                                "blockers": [
                                    "integration_wiring_incomplete",
                                    "strict_live_probe_failed",
                                ]
                            },
                            "strict_live_probe": {
                                "status": "failed",
                                "reason": "live_provider_required",
                                "detail": {
                                    "provider_attempts": [
                                        {"provider": "dataforseo", "configured": False, "status": "skipped", "error_code": "not_configured"},
                                        {"provider": "serper", "configured": False, "status": "skipped", "error_code": "not_configured"},
                                        {"provider": "nuxtron_synthetic", "configured": True, "status": "success"},
                                    ]
                                },
                            },
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    (test_results / "production-31-capability-audit.json").write_text(
        json.dumps(
            {
                "summary": {"fully_validated": 11, "avg_score_pct": 79.6},
                "rows": [
                    {
                        "idx": 1,
                        "capability": "Core SEO Foundations",
                        "score_pct": 70.0,
                        "readiness_slice_ready": False,
                        "readiness_artifact": "semrush-readiness-report.json",
                    },
                    {
                        "idx": 3,
                        "capability": "SEO AI",
                        "score_pct": 70.0,
                        "readiness_slice_ready": False,
                        "readiness_artifact": "semrush-readiness-report.json",
                    },
                    {
                        "idx": 5,
                        "capability": "AIO-2",
                        "score_pct": 80.0,
                        "readiness_slice_ready": False,
                        "readiness_artifact": "semrush-readiness-report.json",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    (ci_dir / "readiness_gate_thresholds.json").write_text(
        json.dumps(
            {
                "global": {"min_validated": 11, "min_avg_score": 79.0},
                "groups": {},
                "critical_capabilities": [
                    {
                        "idx": 1,
                        "name": "Core SEO Foundations",
                        "min_score": 70.0,
                        "require_readiness": False,
                        "require_strict_live": True,
                        "strict_live_blockers": ["strict_live_probe_failed"],
                    },
                    {
                        "idx": 3,
                        "name": "SEO AI",
                        "min_score": 70.0,
                        "require_readiness": False,
                        "require_strict_live": True,
                        "strict_live_blockers": ["strict_live_probe_failed"],
                    },
                    {
                        "idx": 5,
                        "name": "AIO-2",
                        "min_score": 80.0,
                        "require_readiness": False,
                        "require_strict_live": False,
                        "strict_live_blockers": ["strict_live_probe_failed"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    module.ROOT = fake_root
    module.AUDIT_JSON = test_results / "production-31-capability-audit.json"
    module.THRESHOLDS_JSON = ci_dir / "readiness_gate_thresholds.json"
    module.REMEDIATION_JSON = test_results / "readiness-gate-remediation.json"

    monkeypatch.delenv("READINESS_CRITICAL_1_REQUIRE_STRICT_LIVE", raising=False)
    monkeypatch.delenv("READINESS_CRITICAL_3_REQUIRE_STRICT_LIVE", raising=False)
    monkeypatch.delenv("READINESS_CRITICAL_5_REQUIRE_STRICT_LIVE", raising=False)

    exit_code = module.main()
    assert exit_code == 1

    assert module.REMEDIATION_JSON.exists()
    remediation = json.loads(module.REMEDIATION_JSON.read_text(encoding="utf-8"))
    assert remediation.get("status") == "fail"
    assert remediation.get("summary", {}).get("strict_live_failures") == 2

    failures = remediation.get("strict_live_remediation", [])
    assert len(failures) == 2
    for row in failures:
        assert row.get("probe_reason") == "live_provider_required"
        assert row.get("annotation_level") == "error"
        hints = row.get("secret_hints", [])
        assert any("SERPER_API_KEY" in item for item in hints)
        assert any("DATAFORSEO_LOGIN" in item for item in hints)

    observations = remediation.get("strict_live_observations", [])
    assert len(observations) == 1
    assert observations[0].get("idx") == 5
    assert observations[0].get("annotation_level") == "warning"
