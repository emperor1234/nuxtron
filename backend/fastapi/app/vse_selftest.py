import base64
import hashlib
import hmac
import os
import secrets
import time

from fastapi.testclient import TestClient

from .main import app

DARK_SOCIAL_ATTRIBUTION_ROUTE = '/vse/dark-social/attribution'


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def _selftest_jwt(tenant: str) -> str:
    secret = os.getenv('JWT_SIGNING_KEY', '').strip() or os.getenv('FASTAPI_API_KEY', 'change-this-fastapi-key').strip()
    now = int(time.time())
    header = _b64url_encode(b'{"alg":"HS256","typ":"JWT"}')
    payload = _b64url_encode(
        (
            '{'
            f'"tenant_id":"{tenant}",'
            f'"sub":"vse-selftest-{tenant}-{secrets.token_hex(4)}",'
            f'"iat":{now},'
            f'"exp":{now + 3600}'
            '}'
        ).encode()
    )
    signing_input = f'{header}.{payload}'.encode('ascii')
    signature = _b64url_encode(hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest())
    return f'{header}.{payload}.{signature}'


def _headers(tenant: str = 'tenant-vse-selftest') -> dict[str, str]:
    return {
        'Authorization': f'Bearer {_selftest_jwt(tenant)}',
        'X-Tenant-Id': tenant,
    }


def run_vse_selftest() -> None:
    os.environ.setdefault('FASTAPI_API_KEY', 'change-this-fastapi-key')
    os.environ.setdefault('PASSWORD_PEPPER', 'selftest-pepper')
    os.environ.setdefault('APP_ENC_KEY', 'selftest-enc-key')

    with TestClient(app) as client:
        health = client.get('/healthz')
        assert health.status_code == 200, health.text

        swarm_compose = client.post(
            '/vse/swarm/compose',
            headers=_headers(),
            json={
                'post_summary': 'Backend VSE self-test post',
                'niche': 'B2B growth',
                'platforms': ['linkedin'],
                'swarm_size': 12,
            },
        )
        assert swarm_compose.status_code == 200, swarm_compose.text
        swarm_id = swarm_compose.json().get('swarm', {}).get('id')
        assert isinstance(swarm_id, str) and len(swarm_id) > 0

        swarm_missing = client.get('/vse/swarm/swarm-does-not-exist/status', headers=_headers())
        assert swarm_missing.status_code == 404, swarm_missing.text
        assert 'Swarm not found' in swarm_missing.json().get('detail', '')

        swarm_activate = client.post(
            '/vse/swarm/activate',
            headers=_headers(),
            json={'swarm_id': swarm_id, 'post_url': 'https://example.com/post'},
        )
        assert swarm_activate.status_code == 200, swarm_activate.text

        swarm_status = client.get(f'/vse/swarm/{swarm_id}/status', headers=_headers())
        assert swarm_status.status_code == 200, swarm_status.text
        assert swarm_status.json().get('swarm_status') == 'active'

        attr_empty_campaign = client.post(
            DARK_SOCIAL_ATTRIBUTION_ROUTE,
            headers=_headers(),
            json={
                'campaign_id': '   ',
                'touchpoints': ['whatsapp_share'],
                'conversions': 2,
                'conversion_value': 20,
            },
        )
        assert attr_empty_campaign.status_code == 422, attr_empty_campaign.text
        assert 'campaign_id cannot be empty' in attr_empty_campaign.json().get('detail', '')

        attr_invalid_value = client.post(
            DARK_SOCIAL_ATTRIBUTION_ROUTE,
            headers=_headers(),
            json={
                'campaign_id': 'cmp-vse-selftest-invalid',
                'touchpoints': [],
                'conversions': 0,
                'conversion_value': 50,
            },
        )
        assert attr_invalid_value.status_code == 422, attr_invalid_value.text
        assert 'conversion_value cannot be positive' in attr_invalid_value.json().get('detail', '')

        attr_normalised = client.post(
            DARK_SOCIAL_ATTRIBUTION_ROUTE,
            headers=_headers(),
            json={
                'campaign_id': 'cmp-vse-selftest-normalised',
                'touchpoints': ['whatsapp_share', '  WHATSAPP_SHARE  ', ''],
                'conversions': 6,
                'conversion_value': 120,
            },
        )
        assert attr_normalised.status_code == 200, attr_normalised.text
        normalised_payload = attr_normalised.json()
        assert normalised_payload.get('normalised_touchpoints_count') == 1
        attribution_rows = normalised_payload.get('attribution', [])
        assert len(attribution_rows) == 1
        assert attribution_rows[0].get('touchpoint') == 'whatsapp_share'
        assert normalised_payload.get('attribution_confidence') == 'medium'

        attr_default_touchpoints = client.post(
            DARK_SOCIAL_ATTRIBUTION_ROUTE,
            headers=_headers(),
            json={
                'campaign_id': 'cmp-vse-selftest-defaults',
                'touchpoints': [],
                'conversions': 3,
                'conversion_value': 45,
            },
        )
        assert attr_default_touchpoints.status_code == 200, attr_default_touchpoints.text
        defaults_payload = attr_default_touchpoints.json()
        assert defaults_payload.get('normalised_touchpoints_count') == 3
        assert len(defaults_payload.get('notes', [])) >= 1


if __name__ == '__main__':
    run_vse_selftest()
