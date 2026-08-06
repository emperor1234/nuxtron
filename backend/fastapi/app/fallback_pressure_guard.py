import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from .main import app


def _headers(tenant: str) -> dict[str, str]:
    return {
        'X-API-Key': os.getenv('FASTAPI_API_KEY', 'change-this-fastapi-key'),
        'X-Tenant-Id': tenant,
    }


def run_guard() -> None:
    os.environ.setdefault('FASTAPI_API_KEY', 'change-this-fastapi-key')
    snapshot_path = Path(os.getenv('FALLBACK_PRESSURE_SNAPSHOT_PATH', 'artifacts/fallback-pressure-snapshot.json'))

    prev_cap = os.environ.get('BRIDGES_MEMORY_CAP')
    prev_warn = os.environ.get('BRIDGES_WARN_UTILIZATION_PCT')
    os.environ['BRIDGES_MEMORY_CAP'] = '5'
    os.environ['BRIDGES_WARN_UTILIZATION_PCT'] = '40'

    try:
        with TestClient(app) as client:
            future_publish_at = (datetime.now(UTC) + timedelta(hours=1)).isoformat()

            # Populate a tracked fallback buffer to cross the warning threshold.
            for i in range(3):
                r = client.post(
                    '/social/schedule',
                    headers=_headers('tenant-pressure'),
                    json={
                        'platform': 'linkedin',
                        'text': f'Fallback pressure post {i}',
                        'publish_at': future_publish_at,
                    },
                )
                assert r.status_code == 200, r.text

            status = client.get('/ops/platform/status', headers=_headers('tenant-pressure'))
            assert status.status_code == 200, status.text
            payload = status.json()
            fb = payload.get('fallback_buffers', {})

            assert fb.get('max_items_per_buffer') == 5
            assert abs(float(fb.get('warning_utilization_threshold', 0.0)) - 0.4) < 0.0001
            assert fb.get('any_buffer_hot') is True
            assert 'scheduled_posts' in fb.get('hot_buffers', [])
            assert float(fb.get('utilization_ratio', {}).get('scheduled_posts', 0.0)) >= 0.4

            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot = {
                'status': payload.get('status'),
                'tenant_id': payload.get('tenant_id'),
                'fallback_buffers': fb,
                'rate_limit_active_keys': payload.get('rate_limit_active_keys'),
            }
            snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding='utf-8')
    finally:
        if prev_cap is None:
            os.environ.pop('BRIDGES_MEMORY_CAP', None)
        else:
            os.environ['BRIDGES_MEMORY_CAP'] = prev_cap

        if prev_warn is None:
            os.environ.pop('BRIDGES_WARN_UTILIZATION_PCT', None)
        else:
            os.environ['BRIDGES_WARN_UTILIZATION_PCT'] = prev_warn

    print('FastAPI fallback pressure guard passed')


if __name__ == '__main__':
    run_guard()