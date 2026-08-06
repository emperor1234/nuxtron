import json
import os
from pathlib import Path
from typing import Any, cast


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def refresh_baseline() -> None:
    snapshot_path = Path(os.getenv('FALLBACK_PRESSURE_SNAPSHOT_PATH', 'artifacts/fallback-pressure-snapshot.json'))
    output_path = Path(os.getenv('FALLBACK_PRESSURE_BASELINE_OUTPUT_PATH', 'artifacts/fallback-pressure-baseline-candidate.json'))

    if not snapshot_path.exists():
        raise FileNotFoundError(f'Snapshot file not found: {snapshot_path}')

    snapshot = _load_json(snapshot_path)
    fallback_buffers_raw = snapshot.get('fallback_buffers', {})
    fallback_buffers = cast(dict[str, Any], fallback_buffers_raw) if isinstance(fallback_buffers_raw, dict) else {}
    if not fallback_buffers:
        raise ValueError('Snapshot missing fallback_buffers payload')

    baseline: dict[str, dict[str, Any]] = {
        'fallback_buffers': {
            'max_items_per_buffer': int(fallback_buffers.get('max_items_per_buffer', 0)),
            'warning_utilization_threshold': float(fallback_buffers.get('warning_utilization_threshold', 0.0)),
            'sizes': dict(fallback_buffers.get('sizes', {})),
            'utilization_ratio': dict(fallback_buffers.get('utilization_ratio', {})),
            'hot_buffers': list(fallback_buffers.get('hot_buffers', [])),
            'any_buffer_hot': bool(fallback_buffers.get('any_buffer_hot', False)),
        }
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(baseline, indent=2), encoding='utf-8')
    print(f'Wrote baseline candidate: {output_path}')


if __name__ == '__main__':
    refresh_baseline()
