import json
import os
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def _warn(message: str) -> None:
    if os.getenv('GITHUB_ACTIONS') == 'true':
        print(f'::warning::{message}')
    else:
        print(f'WARNING: {message}')


def run_trend_check() -> None:
    snapshot_path = Path(os.getenv('FALLBACK_PRESSURE_SNAPSHOT_PATH', 'artifacts/fallback-pressure-snapshot.json'))
    baseline_path = Path(os.getenv('FALLBACK_PRESSURE_BASELINE_PATH', 'backend/fastapi/app/fallback_pressure_baseline.json'))
    report_path = Path(os.getenv('FALLBACK_PRESSURE_TREND_REPORT_PATH', 'artifacts/fallback-pressure-trend-report.json'))
    tolerance = float(os.getenv('FALLBACK_PRESSURE_TREND_TOLERANCE', '0.05'))

    if not snapshot_path.exists():
        raise FileNotFoundError(f'Snapshot file not found: {snapshot_path}')
    if not baseline_path.exists():
        raise FileNotFoundError(f'Baseline file not found: {baseline_path}')

    snapshot = _load_json(snapshot_path)
    baseline = _load_json(baseline_path)

    snap_fb = snapshot.get('fallback_buffers', {})
    base_fb = baseline.get('fallback_buffers', {})
    snap_ratios = snap_fb.get('utilization_ratio', {})
    base_ratios = base_fb.get('utilization_ratio', {})

    keys = sorted(set(base_ratios.keys()) | set(snap_ratios.keys()))
    worsened_buffers: list[dict[str, Any]] = []
    for key in keys:
        current = float(snap_ratios.get(key, 0.0))
        baseline_value = float(base_ratios.get(key, 0.0))
        delta = round(current - baseline_value, 4)
        if delta > tolerance:
            worsened_buffers.append(
                {
                    'buffer': key,
                    'baseline': baseline_value,
                    'current': current,
                    'delta': delta,
                }
            )

    snap_hot = sorted(snap_fb.get('hot_buffers', []))
    base_hot = sorted(base_fb.get('hot_buffers', []))
    extra_hot = sorted(set(snap_hot) - set(base_hot))

    report: dict[str, Any] = {
        'snapshot_path': str(snapshot_path),
        'baseline_path': str(baseline_path),
        'tolerance': tolerance,
        'worsened_buffers': worsened_buffers,
        'extra_hot_buffers': extra_hot,
        'snapshot_hot_buffers': snap_hot,
        'baseline_hot_buffers': base_hot,
        'snapshot_any_buffer_hot': bool(snap_fb.get('any_buffer_hot', False)),
        'baseline_any_buffer_hot': bool(base_fb.get('any_buffer_hot', False)),
        'has_trend_warning': bool(worsened_buffers or extra_hot),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')

    if worsened_buffers or extra_hot:
        details: list[str] = []
        if worsened_buffers:
            details.append(f'worsened={worsened_buffers}')
        if extra_hot:
            details.append(f'extra_hot={extra_hot}')
        _warn('Fallback pressure trend worsened versus baseline: ' + '; '.join(details))
    else:
        print('Fallback pressure trend is stable versus baseline')

    print('FastAPI fallback pressure trend check completed')


if __name__ == '__main__':
    run_trend_check()