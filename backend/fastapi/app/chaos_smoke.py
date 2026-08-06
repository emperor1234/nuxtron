import os

from fastapi.testclient import TestClient

from .main import app


def _headers(tenant: str) -> dict[str, str]:
    return {
        'X-API-Key': os.getenv('FASTAPI_API_KEY', 'change-this-fastapi-key'),
        'X-Tenant-Id': tenant,
    }


def run_chaos_smoke() -> None:
    os.environ.setdefault('FASTAPI_API_KEY', 'change-this-fastapi-key')

    prev_cap = os.environ.get('BRIDGES_MEMORY_CAP')
    prev_warn_pct = os.environ.get('BRIDGES_WARN_UTILIZATION_PCT')

    os.environ['BRIDGES_MEMORY_CAP'] = '5'
    os.environ['BRIDGES_WARN_UTILIZATION_PCT'] = '40'

    try:
        with TestClient(app) as client:
            # Force fallback buffer pressure on a tracked in-memory integration queue.
            # suitecrm_jobs is part of fallback_buffers and remains memory-backed in db-ready mode.
            for i in range(3):
                write = client.post(
                    '/integrations/suitecrm/upsert-lead',
                    headers=_headers('tenant-chaos'),
                    json={
                        'first_name': 'Chaos',
                        'last_name': f'Probe{i}',
                        'email': f'chaos{i}@example.com',
                        'company': 'Nuxtron Chaos',
                        'source': 'chaos_smoke',
                    },
                )
                assert write.status_code == 200, write.text

            anti_failure = client.get('/ops/platform/anti-failure-status', headers=_headers('tenant-chaos'))
            assert anti_failure.status_code == 200, anti_failure.text
            payload = anti_failure.json()
            defenses = payload.get('defense_systems', [])
            quality_guardian = next((d for d in defenses if d.get('id') == 'quality_guardian'), None)
            assert quality_guardian is not None
            assert quality_guardian.get('healthy') is False
            assert int(payload.get('summary', {}).get('degraded_count', 0)) >= 1

            # Fault-injection style negative-path validation.
            unknown_provider = client.post(
                '/webhooks/receive/unknown-provider',
                headers=_headers('tenant-chaos'),
                json={'provider': 'unknown-provider', 'event_type': 'fault_probe', 'payload': {}},
            )
            assert unknown_provider.status_code == 400, unknown_provider.text

    finally:
        if prev_cap is None:
            os.environ.pop('BRIDGES_MEMORY_CAP', None)
        else:
            os.environ['BRIDGES_MEMORY_CAP'] = prev_cap

        if prev_warn_pct is None:
            os.environ.pop('BRIDGES_WARN_UTILIZATION_PCT', None)
        else:
            os.environ['BRIDGES_WARN_UTILIZATION_PCT'] = prev_warn_pct

    print('FastAPI chaos smoke passed')


if __name__ == '__main__':
    run_chaos_smoke()
