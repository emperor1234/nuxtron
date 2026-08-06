from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module(repo_root: Path):
    script_path = repo_root / "scripts" / "ci" / "emit_readiness_annotations.py"
    spec = importlib.util.spec_from_file_location("emit_readiness_annotations", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_emit_readiness_annotations_from_remediation_payload(tmp_path: Path, capsys):
    repo_root = Path(__file__).resolve().parents[4]
    module = _load_module(repo_root)

    test_results = tmp_path / "test-results"
    test_results.mkdir(parents=True, exist_ok=True)

    remediation_path = test_results / "readiness-gate-remediation.json"
    remediation_path.write_text(
        json.dumps(
            {
                "status": "fail",
                "strict_live_remediation": [
                    {
                        "idx": 1,
                        "capability": "Core SEO Foundations",
                        "probe_reason": "live_provider_required",
                        "blockers": ["strict_live_probe_failed"],
                        "not_configured_providers": ["serper"],
                        "secret_hints": ["serper: SERPER_API_KEY"],
                    }
                ],
                "strict_live_observations": [
                    {
                        "idx": 5,
                        "capability": "AIO-2",
                        "probe_reason": "live_provider_required",
                        "blockers": ["strict_live_probe_failed"],
                        "not_configured_providers": ["dataforseo"],
                        "secret_hints": ["dataforseo: DATAFORSEO_LOGIN, DATAFORSEO_API_KEY"],
                        "annotation_level": "warning",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    module.REMEDIATION_JSON = remediation_path
    exit_code = module.main()
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "::error title=Readiness Gate Strict-Live idx=1::" in out
    assert "::warning title=Readiness Gate Strict-Live Observation idx=5::" in out
    assert "SERPER_API_KEY" in out
    assert "Emitted strict-live annotations: errors=1, warnings=1" in out
