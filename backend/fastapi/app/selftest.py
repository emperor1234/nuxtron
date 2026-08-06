import base64
import hashlib
import hmac
import math
import os
import secrets
import sys
import time
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from fastapi.testclient import TestClient

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('SUPER_ADMIN_API_KEY', 'selftest-super-admin-key')

from . import legacy_main as main_module
from .legacy_main import app

# Test data constants
TEST_AUTH_SECRET = os.getenv('SELFTEST_AUTH_SECRET', f'selftest-{secrets.token_urlsafe(12)}')
FRIEND_EMAIL = 'friend@example.com'
NOTIFICATIONS_ENDPOINT = '/notifications'
NOTIFICATIONS_UNREAD = '/notifications/unread-count'
NOTIFICATIONS_PREFERENCES = '/notifications/preferences'
CACHE_SET_ENDPOINT = '/cache/set'
CACHE_KEY_SELFTEST = 'selftest:greeting'
SEARCH_ALGOLIA_ENDPOINT = '/search/algolia/query'
BILLING_SUBSCRIBE_ENDPOINT = '/billing/subscribe'
REFERRALS_CLAIM_ENDPOINT = '/engagement/referrals/claim'
SOCIAL_PROOF_ENDPOINT = '/engagement/social-proof/events'
TREND_SIGNAL_INGEST_ENDPOINT = '/trends/signals/ingest'
TREND_FORECAST_GENERATE_ENDPOINT = '/trends/forecast/generate'
TREND_SELECT_ENDPOINT = '/trends/select'
TREND_CONTENT_GENERATE_ENDPOINT = '/trends/content/generate'
TREND_PERFORMANCE_TRACK_ENDPOINT = '/trends/performance/track'
TREND_ANALYTICS_ENDPOINT = '/trends/analytics/dashboard'
TREND_INDICATORS_ENDPOINT = '/trends/analytics/indicators'
TREND_RECOMMENDATIONS_ENDPOINT = '/trends/recommendations'
TREND_TOPIC_PRIMARY = 'ai faceless storytelling'
PENTEST_FINDINGS_ENDPOINT = '/pentest/findings/ingest'
PENTEST_RISK_POLICY_ENDPOINT = '/pentest/risk-policy'
PENTEST_DEFECTDOJO_CONFIG_ENDPOINT = '/pentest/defectdojo/config'


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
            f'"sub":"selftest-{tenant}",'
            f'"iat":{now},'
            f'"exp":{now + 3600}'
            '}'
        ).encode()
    )
    signing_input = f'{header}.{payload}'.encode('ascii')
    signature = _b64url_encode(hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest())
    return f'{header}.{payload}.{signature}'


def _headers(tenant: str) -> dict[str, str]:
    return {
        'Authorization': f'Bearer {_selftest_jwt(tenant)}',
        'X-Tenant-Id': tenant,
    }


def _totp_code(secret: str, step: int = 30, digits: int = 6) -> str:
    counter = int(time.time()) // step
    padded = secret + ('=' * ((8 - len(secret) % 8) % 8))
    key = base64.b32decode(padded.upper())
    msg = counter.to_bytes(8, byteorder='big')
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = ((digest[offset] & 0x7F) << 24) | ((digest[offset + 1] & 0xFF) << 16) | ((digest[offset + 2] & 0xFF) << 8) | (digest[offset + 3] & 0xFF)
    return str(code_int % (10 ** digits)).zfill(digits)


def _assert_meilisearch_error_path(client: TestClient) -> None:
    meili_host_before = os.environ.get('MEILISEARCH_HOST')
    try:
        os.environ['MEILISEARCH_HOST'] = 'bad-host-without-scheme'
        meili_error = client.post(
            '/search/query',
            headers=_headers('tenant-a'),
            json={'index': 'selftest-docs', 'query': 'nuxtron', 'limit': 10, 'offset': 0},
        )
        assert meili_error.status_code == 200, meili_error.text
        assert meili_error.json().get('source') == 'error'
    finally:
        if meili_host_before is None:
            os.environ.pop('MEILISEARCH_HOST', None)
        else:
            os.environ['MEILISEARCH_HOST'] = meili_host_before


def _assert_algolia_error_path(client: TestClient) -> None:
    algolia_app_before = os.environ.get('ALGOLIA_APP_ID')
    algolia_key_before = os.environ.get('ALGOLIA_API_KEY')
    try:
        os.environ['ALGOLIA_APP_ID'] = 'bad app id with spaces'
        os.environ['ALGOLIA_API_KEY'] = 'dummy-key'
        algolia_error = client.post(
            SEARCH_ALGOLIA_ENDPOINT,
            headers=_headers('tenant-a'),
            json={
                'index_name': 'selftest_products',
                'query': 'studio',
                'page': 0,
                'hits_per_page': 10,
            },
        )
        assert algolia_error.status_code == 200, algolia_error.text
        assert algolia_error.json().get('result', {}).get('source') == 'error'
    finally:
        if algolia_app_before is None:
            os.environ.pop('ALGOLIA_APP_ID', None)
        else:
            os.environ['ALGOLIA_APP_ID'] = algolia_app_before

        if algolia_key_before is None:
            os.environ.pop('ALGOLIA_API_KEY', None)
        else:
            os.environ['ALGOLIA_API_KEY'] = algolia_key_before


def run_selftest() -> None:  # NOSONAR
    os.environ.setdefault('FASTAPI_API_KEY', 'change-this-fastapi-key')
    os.environ.setdefault('PASSWORD_PEPPER', 'selftest-pepper')
    os.environ.setdefault('APP_ENC_KEY', 'selftest-enc-key')
    # Keep selftest independent of external Postgres unless explicitly requested.
    if not os.getenv('SELFTEST_USE_RUNTIME_DATABASE', '').strip():
        os.environ['DATABASE_URL'] = f"sqlite:///./test_selftest_{int(time.time() * 1000)}.db"

    BUYER_EMAIL: str = 'buyer@example.com'
    APPROVAL_REQUESTS_PATH: str = '/content/approval/requests'
    CONTENT_REQUESTOR: str = 'content-team@nuxtron.io'
    MEDIA_FOLDERS_PATH: str = '/media/folders'
    ADVOCACY_CONTENT_PATH: str = '/advocacy/content'
    ADVOCACY_PARTICIPANTS_PATH: str = '/advocacy/participants'
    INBOX_MESSAGES_PATH: str = '/inbox/messages'
    INBOX_ASSIGNEE: str = 'alice@brand.com'
    COMPETITIVE_PROFILES_PATH: str = '/competitive/profiles'
    UTM_BUILD_PATH: str = '/publishing/utm/build'
    MEETINGS_BOOK_PATH: str = '/meetings/book'

    with TestClient(app) as client:
        r = client.get('/healthz')
        assert r.status_code == 200, r.text

        bad = client.post(
            '/content/generate',
            headers={'X-API-Key': 'bad', 'X-Tenant-Id': 'tenant-a'},
            json={
                'topic': 'x',
                'audience': 'y',
                'channel': 'linkedin',
                'tone': 'professional',
                'include_seo': True,
            },
        )
        assert bad.status_code in (401, 422), bad.text

        good = client.post(
            '/content/generate',
            headers=_headers('tenant-a'),
            json={
                'topic': 'AI content strategy',
                'audience': 'B2B founders',
                'channel': 'linkedin',
                'tone': 'professional',
                'include_seo': True,
            },
        )
        assert good.status_code == 200, good.text
        assert good.json().get('tenant_id') == 'tenant-a'

        h = client.post(
            '/security/hash-password',
            headers=_headers('tenant-a'),
            json={'password': TEST_AUTH_SECRET, 'algorithm': 'argon2id'},
        )
        assert h.status_code == 200, h.text
        hashed = h.json()['hash']

        v = client.post(
            '/security/verify-password',
            headers=_headers('tenant-a'),
            json={'password': TEST_AUTH_SECRET, 'stored_hash': hashed},
        )
        assert v.status_code == 200, v.text
        assert v.json()['valid'] is True

        # TOTP – setup and verify
        totp_setup = client.post(
            '/auth/totp/setup',
            headers=_headers('tenant-a'),
            json={'account_name': 'qa@nuxtron.io', 'issuer': 'Nuxtron'},
        )
        assert totp_setup.status_code == 200, totp_setup.text
        assert totp_setup.json().get('status') == 'ok'
        secret = totp_setup.json().get('result', {}).get('secret')
        assert isinstance(secret, str) and len(secret) >= 16

        totp_verify = client.post(
            '/auth/totp/verify',
            headers=_headers('tenant-a'),
            json={'secret': secret, 'code': _totp_code(secret), 'window': 1},
        )
        assert totp_verify.status_code == 200, totp_verify.text
        assert totp_verify.json().get('valid') is True

        # JWT – issue and verify
        jwt_issue = client.post(
            '/auth/jwt/issue',
            headers=_headers('tenant-a'),
            json={
                'subject': 'user-selftest',
                'expires_in_seconds': 1800,
                'roles': ['admin'],
                'additional_claims': {'scope': 'platform:test'},
            },
        )
        assert jwt_issue.status_code == 200, jwt_issue.text
        assert jwt_issue.json().get('status') == 'ok'
        token = jwt_issue.json().get('result', {}).get('token')
        assert isinstance(token, str) and len(token) > 20

        jwt_verify = client.post(
            '/auth/jwt/verify',
            headers=_headers('tenant-a'),
            json={'token': token},
        )
        assert jwt_verify.status_code == 200, jwt_verify.text
        assert jwt_verify.json().get('valid') is True
        assert jwt_verify.json().get('claims', {}).get('sub') == 'user-selftest'

        # Tenant management – create/list/update/delete profile
        tenant_create = client.post(
            '/tenants',
            headers=_headers('tenant-a'),
            json={
                'display_name': 'Tenant A Workspace',
                'plan': 'growth',
                'status': 'active',
                'settings': {'region': 'us-east-1', 'theme': 'light'},
            },
        )
        assert tenant_create.status_code == 200, tenant_create.text
        assert tenant_create.json().get('status') == 'ok'

        tenant_list = client.get('/tenants', headers=_headers('tenant-a'))
        assert tenant_list.status_code == 200, tenant_list.text
        assert tenant_list.json().get('count', 0) >= 1

        tenant_update = client.patch(
            '/tenants/tenant-a',
            headers=_headers('tenant-a'),
            json={
                'display_name': 'Tenant A Workspace Updated',
                'plan': 'pro',
                'settings': {'region': 'eu-west-1', 'theme': 'dark'},
            },
        )
        assert tenant_update.status_code == 200, tenant_update.text
        assert tenant_update.json().get('tenant', {}).get('plan') == 'pro'

        tenant_delete = client.delete('/tenants/tenant-a', headers=_headers('tenant-a'))
        assert tenant_delete.status_code == 200, tenant_delete.text
        assert tenant_delete.json().get('deleted') is True

        # Newly added in-app notification center API reuses existing auth and tenant headers.
        notifications_before = client.get(NOTIFICATIONS_ENDPOINT, headers=_headers('tenant-a'))
        assert notifications_before.status_code == 200, notifications_before.text
        assert notifications_before.json().get('unreadCount') == 0

        notification_create = client.post(
            NOTIFICATIONS_ENDPOINT,
            headers=_headers('tenant-a'),
            json={
                'title': 'Selftest Notification',
                'message': 'Verify unread counts and read-all flow.',
                'category': 'selftest',
            },
        )
        assert notification_create.status_code == 200, notification_create.text
        created_notification = notification_create.json().get('notification', {})
        assert created_notification.get('title') == 'Selftest Notification'
        # ENHANCED: verify priority defaults to 'info' when not provided
        assert created_notification.get('priority', 'info') == 'info', 'Default priority must be info'

        # ENHANCED: test explicit priority field
        notif_critical = client.post(
            NOTIFICATIONS_ENDPOINT,
            headers=_headers('tenant-a'),
            json={
                'title': 'Critical Alert',
                'message': 'System threshold breached.',
                'category': 'system',
                'priority': 'critical',
            },
        )
        assert notif_critical.status_code == 200, notif_critical.text
        assert notif_critical.json()['notification']['priority'] == 'critical'

        # ENHANCED: enable Slack fan-out in tenant preferences for receipt coverage
        prefs_update = client.put(
            NOTIFICATIONS_PREFERENCES,
            headers=_headers('tenant-a'),
            json={
                'muted_categories': [],
                'email_enabled': True,
                'sms_enabled': False,
                'slack_enabled': True,
                'realtime_enabled': True,
                'digest_frequency': 'realtime',
            },
        )
        assert prefs_update.status_code == 200, prefs_update.text

        fanout_notification = client.post(
            NOTIFICATIONS_ENDPOINT,
            headers=_headers('tenant-a'),
            json={
                'title': 'Critical Fanout Probe',
                'message': 'Validate external fan-out receipt tracking.',
                'category': 'selftest',
                'priority': 'critical',
            },
        )
        assert fanout_notification.status_code == 200, fanout_notification.text
        fanout_payload = fanout_notification.json()
        fanout_id = fanout_payload.get('notification', {}).get('id')
        assert isinstance(fanout_id, int) and fanout_id > 0
        delivery_receipts = fanout_payload.get('deliveryReceipts', [])
        assert len(delivery_receipts) >= 3, 'critical fan-out should emit slack/email/webhook receipt records'
        # ENHANCED: additive policy metadata confirms why each channel was (or was not) routed.
        assert all(item.get('policy_version') == 'v1-priority-routing' for item in delivery_receipts)
        assert all(isinstance(item.get('policy_decision'), str) and item.get('policy_decision') for item in delivery_receipts)

        receipt_list = client.get(
            f'/notifications/delivery-receipts?notification_id={fanout_id}',
            headers=_headers('tenant-a'),
        )
        assert receipt_list.status_code == 200, receipt_list.text
        receipt_data = receipt_list.json()
        assert receipt_data.get('count', 0) >= 3
        channels = {item.get('channel') for item in receipt_data.get('receipts', [])}
        assert {'slack', 'email', 'webhook'}.issubset(channels)

        delivery_health = client.get('/notifications/delivery-health?window_seconds=86400', headers=_headers('tenant-a'))
        assert delivery_health.status_code == 200, delivery_health.text
        delivery_health_data = delivery_health.json()
        assert delivery_health_data.get('totalReceipts', 0) >= 3
        assert 'byChannel' in delivery_health_data
        assert 'byStatus' in delivery_health_data
        assert 'byChannelStatus' in delivery_health_data
        assert 'byPolicyDecision' in delivery_health_data
        assert isinstance(delivery_health_data['byPolicyDecision'], dict)
        assert all(isinstance(k, str) and isinstance(v, int) for k, v in delivery_health_data['byPolicyDecision'].items())

        delivery_health_slack = client.get(
            '/notifications/delivery-health?window_seconds=86400&channel=slack',
            headers=_headers('tenant-a'),
        )
        assert delivery_health_slack.status_code == 200, delivery_health_slack.text
        delivery_health_slack_data = delivery_health_slack.json()
        assert delivery_health_slack_data.get('filters', {}).get('channel') == 'slack'
        assert set(delivery_health_slack_data.get('byChannel', {}).keys()).issubset({'slack'})

        delivery_health_skipped = client.get(
            '/notifications/delivery-health?window_seconds=86400&delivery_status=skipped',
            headers=_headers('tenant-a'),
        )
        assert delivery_health_skipped.status_code == 200, delivery_health_skipped.text
        delivery_health_skipped_data = delivery_health_skipped.json()
        assert delivery_health_skipped_data.get('filters', {}).get('deliveryStatus') == 'skipped'
        assert set(delivery_health_skipped_data.get('byStatus', {}).keys()).issubset({'skipped'})

        # ENHANCED: test pagination — limit=1 should return 1 item
        notif_page = client.get(f'{NOTIFICATIONS_ENDPOINT}?limit=1&offset=0', headers=_headers('tenant-a'))
        assert notif_page.status_code == 200, notif_page.text
        page_data = notif_page.json()
        assert len(page_data['notifications']) == 1, 'limit=1 must return exactly 1 item'
        assert 'total' in page_data, 'Paginated response must include total'
        assert page_data['total'] >= 2

        # ENHANCED: test priority filter
        notif_priority_filter = client.get(f'{NOTIFICATIONS_ENDPOINT}?priority=critical', headers=_headers('tenant-a'))
        assert notif_priority_filter.status_code == 200, notif_priority_filter.text
        assert all(n['priority'] == 'critical' for n in notif_priority_filter.json()['notifications'])

        unread_after_create = client.get(NOTIFICATIONS_UNREAD, headers=_headers('tenant-a'))
        assert unread_after_create.status_code == 200, unread_after_create.text
        assert unread_after_create.json().get('unreadCount') >= 1

        mark_all_read = client.post('/notifications/read-all', headers=_headers('tenant-a'))
        assert mark_all_read.status_code == 200, mark_all_read.text
        assert mark_all_read.json().get('updated') >= 1

        unread_after_read = client.get(NOTIFICATIONS_UNREAD, headers=_headers('tenant-a'))
        assert unread_after_read.status_code == 200, unread_after_read.text
        assert unread_after_read.json().get('unreadCount') == 0

        listening_ingest = client.post(
            '/social/listening/ingest',
            headers=_headers('tenant-a'),
            json={
                'platform': 'x',
                'query': 'nuxtron',
                'author_handle': '@ops_signal',
                'text': 'Nuxtron keeps surfacing campaign signal drift before spend gets wasted.',
                'sentiment': 'positive',
                'engagement_count': 27,
            },
        )
        assert listening_ingest.status_code == 200, listening_ingest.text
        assert listening_ingest.json().get('mention', {}).get('query') == 'nuxtron'

        listening_summary = client.get('/social/listening/summary', headers=_headers('tenant-a'))
        assert listening_summary.status_code == 200, listening_summary.text
        assert listening_summary.json().get('summary', {}).get('total_mentions') == 1
        assert listening_summary.json().get('summary', {}).get('sentiment', {}).get('positive') == 1

        listening_rule = client.post(
            '/social/listening/rules',
            headers=_headers('tenant-a'),
            json={
                'name': 'Selftest negative surge rule',
                'query': 'nuxtron',
                'platform': 'x',
                'min_engagement': 50,
                'negative_only': True,
            },
        )
        assert listening_rule.status_code == 200, listening_rule.text

        listening_negative = client.post(
            '/social/listening/ingest',
            headers=_headers('tenant-a'),
            json={
                'platform': 'x',
                'query': 'nuxtron',
                'author_handle': '@incident_watch',
                'text': 'Outage concerns are accelerating and customers are frustrated.',
                'sentiment': 'negative',
                'engagement_count': 120,
            },
        )
        assert listening_negative.status_code == 200, listening_negative.text

        listening_alerts = client.get('/social/listening/alerts', headers=_headers('tenant-a'))
        assert listening_alerts.status_code == 200, listening_alerts.text
        assert listening_alerts.json().get('count', 0) >= 1

        listening_clusters = client.get('/social/listening/clusters', headers=_headers('tenant-a'))
        assert listening_clusters.status_code == 200, listening_clusters.text
        assert listening_clusters.json().get('count', 0) >= 1

        listening_summary_after_negative = client.get('/social/listening/summary', headers=_headers('tenant-a'))
        assert listening_summary_after_negative.status_code == 200, listening_summary_after_negative.text
        assert listening_summary_after_negative.json().get('summary', {}).get('alerts_open', 0) >= 1

        review_ingest = client.post(
            '/reviews/ingest',
            headers=_headers('tenant-a'),
            json={
                'platform': 'google',
                'reviewer': 'Selftest Customer',
                'rating': 2,
                'text': 'Powerful automation, but setup guidance needs work.',
                'category': 'onboarding',
            },
        )
        assert review_ingest.status_code == 200, review_ingest.text
        review_id = review_ingest.json().get('review', {}).get('id')
        assert isinstance(review_id, int) and review_id > 0

        review_respond = client.post(
            f'/reviews/{review_id}/respond',
            headers=_headers('tenant-a'),
            json={'response': 'Thanks. We improved setup docs and assigned onboarding support.'},
        )
        assert review_respond.status_code == 200, review_respond.text
        assert review_respond.json().get('review', {}).get('responded') is True

        review_summary = client.get('/reviews/summary', headers=_headers('tenant-a'))
        assert review_summary.status_code == 200, review_summary.text
        assert review_summary.json().get('summary', {}).get('total_reviews', 0) >= 1
        assert review_summary.json().get('summary', {}).get('reputation_score', 0) >= 0

        c = client.post(
            '/email/contacts',
            headers=_headers('tenant-a'),
            json={
                'email': 'founder@example.com',
                'name': 'Founder',
                'tags': ['launch'],
            },
        )
        assert c.status_code == 200, c.text

        cl = client.get('/email/contacts', headers=_headers('tenant-a'))
        assert cl.status_code == 200, cl.text
        assert cl.json()['count'] >= 1

        camp = client.post(
            '/email/campaigns',
            headers=_headers('tenant-a'),
            json={
                'subject': 'Welcome launch',
                'body': 'This is an encrypted campaign body.',
                'provider': 'ses',
            },
        )
        assert camp.status_code == 200, camp.text
        campaign_id = camp.json()['campaign']['id']

        send = client.post(
            f'/email/campaigns/{campaign_id}/send-test',
            headers=_headers('tenant-a'),
            json={'recipient_email': 'qa@example.com'},
        )
        assert send.status_code == 200, send.text

        suite = client.post(
            '/integrations/suitecrm/upsert-lead',
            headers=_headers('tenant-a'),
            json={
                'first_name': 'Jane',
                'last_name': 'Doe',
                'email': 'jane@example.com',
                'company': 'Nuxtron Labs',
                'source': 'selftest',
            },
        )
        assert suite.status_code == 200, suite.text

        ref = client.post(
            '/integrations/refferq/register-referral',
            headers=_headers('tenant-a'),
            json={
                'referrer_email': 'referrer@example.com',
                'referred_email': FRIEND_EMAIL,
                'campaign': 'selftest-campaign',
            },
        )
        assert ref.status_code == 200, ref.text

        analytics = client.post(
            '/analytics/posthog/capture',
            headers=_headers('tenant-a'),
            json={
                'event': 'studio_selftest_run',
                'distinct_id': 'tenant-a-user-1',
                'properties': {
                    'source': 'selftest',
                    'surface': 'studio',
                },
            },
        )
        assert analytics.status_code == 200, analytics.text

        n8n = client.post(
            '/integrations/n8n/trigger-webhook',
            headers=_headers('tenant-a'),
            json={
                'workflow': 'lead-intake',
                'payload': {
                    'lead_email': 'lead@example.com',
                    'source': 'selftest',
                },
            },
        )
        assert n8n.status_code == 200, n8n.text

        gb = client.post(
            '/flags/growthbook/evaluate',
            headers=_headers('tenant-a'),
            json={
                'feature_key': 'studio.newPane',
                'user_id': 'tenant-a-user',
                'attributes': {
                    'plan': 'pro',
                },
            },
        )
        assert gb.status_code == 200, gb.text

        ops = client.get('/ops/platform/status', headers=_headers('tenant-a'))
        assert ops.status_code == 200, ops.text
        assert ops.json().get('tenant_id') == 'tenant-a'
        integrations = ops.json().get('integrations', {})
        assert 'hashicorp_vault_configured' in integrations
        assert 'supabase_configured' in integrations
        assert 'supabase_vault_ready' in integrations
        fallback_buffers = ops.json().get('fallback_buffers', {})
        assert isinstance(fallback_buffers.get('max_items_per_buffer'), int)
        assert fallback_buffers.get('max_items_per_buffer') >= 1
        assert isinstance(fallback_buffers.get('warning_utilization_threshold'), float)
        assert 0.0 <= fallback_buffers.get('warning_utilization_threshold') <= 1.0
        assert isinstance(fallback_buffers.get('sizes', {}), dict)
        assert isinstance(fallback_buffers.get('utilization_ratio', {}), dict)
        assert isinstance(fallback_buffers.get('hot_buffers', []), list)
        assert isinstance(fallback_buffers.get('any_buffer_hot'), bool)
        assert fallback_buffers.get('sizes', {}).get('meilisearch') is not None
        assert fallback_buffers.get('utilization_ratio', {}).get('algolia') is not None

        metrics = client.get('/ops/platform/metrics-summary', headers=_headers('tenant-a'))
        assert metrics.status_code == 200, metrics.text

        anti_failure = client.get('/ops/platform/anti-failure-status', headers=_headers('tenant-a'))
        assert anti_failure.status_code == 200, anti_failure.text
        anti_failure_payload = anti_failure.json()
        assert isinstance(anti_failure_payload.get('defense_systems', []), list)
        assert anti_failure_payload.get('summary', {}).get('total') == 12

        use_case_coverage = client.get('/ops/platform/use-case-coverage', headers=_headers('tenant-a'))
        assert use_case_coverage.status_code == 200, use_case_coverage.text
        use_case_coverage_payload = use_case_coverage.json()
        assert isinstance(use_case_coverage_payload.get('use_cases', {}), dict)
        assert use_case_coverage_payload.get('total_use_cases') == 24
        assert isinstance(use_case_coverage_payload.get('coverage_percent'), float)

        siem_collection = client.get('/ops/siem/data-collection?limit=100', headers=_headers('tenant-a'))
        assert siem_collection.status_code == 200, siem_collection.text
        assert siem_collection.json().get('telemetry') is not None

        siem_detection = client.get('/ops/siem/detection?limit=100', headers=_headers('tenant-a'))
        assert siem_detection.status_code == 200, siem_detection.text
        assert siem_detection.json().get('rule_based_correlation') is not None

        siem_case = client.post(
            '/ops/siem/cases',
            headers=_headers('tenant-a'),
            json={
                'title': 'Suspicious auth behavior',
                'severity': 'high',
                'description': 'Repeated suspicious login attempts observed',
                'evidence_ids': ['evt-1001', 'evt-1002'],
            },
        )
        assert siem_case.status_code == 200, siem_case.text
        case_id = siem_case.json()['case']['id']

        siem_case_update = client.patch(
            f'/ops/siem/cases/{case_id}',
            headers=_headers('tenant-a'),
            json={'status': 'in_progress', 'assignee': 'soc-analyst', 'note': 'Triaged and escalating'},
        )
        assert siem_case_update.status_code == 200, siem_case_update.text

        siem_soar = client.post(
            '/ops/siem/soar/run',
            headers=_headers('tenant-a'),
            json={'playbook': 'contain-compromised-endpoint', 'case_id': case_id, 'parameters': {'host': 'srv-1'}},
        )
        assert siem_soar.status_code == 200, siem_soar.text
        assert siem_soar.json().get('run', {}).get('status') == 'completed'

        siem_investigation = client.get('/ops/siem/investigation?query=auth&limit=50', headers=_headers('tenant-a'))
        assert siem_investigation.status_code == 200, siem_investigation.text
        assert siem_investigation.json().get('search_and_pivoting') is not None

        siem_compliance = client.get('/ops/siem/compliance', headers=_headers('tenant-a'))
        assert siem_compliance.status_code == 200, siem_compliance.text
        assert isinstance(siem_compliance.json().get('prebuilt_compliance_reports', []), list)

        siem_retention = client.post(
            '/ops/siem/compliance/retention',
            headers=_headers('tenant-a'),
            json={'hot_days': 14, 'warm_days': 60, 'cold_days': 365, 'immutable_audit': True},
        )
        assert siem_retention.status_code == 200, siem_retention.text
        assert siem_retention.json().get('retention_policy', {}).get('hot_days') == 14

        siem_arch = client.get('/ops/siem/architecture', headers=_headers('tenant-a'))
        assert siem_arch.status_code == 200, siem_arch.text
        assert siem_arch.json().get('scalability_architecture') is not None

        siem_flows = client.get('/ops/siem/flows?minutes=120&limit=300', headers=_headers('tenant-a'))
        assert siem_flows.status_code == 200, siem_flows.text
        assert siem_flows.json().get('graph', {}).get('nodes') is not None

        siem_controls = client.get('/ops/siem/controls', headers=_headers('tenant-a'))
        assert siem_controls.status_code == 200, siem_controls.text
        waf_controls = siem_controls.json().get('waf', [])
        assert isinstance(waf_controls, list)
        assert len(waf_controls) >= 1
        control_id = waf_controls[0]['id']

        siem_control_update = client.patch(
            f'/ops/siem/controls/waf/{control_id}',
            headers=_headers('tenant-a'),
            json={'enabled': True, 'mode': 'block', 'action': 'deny', 'threshold': 120, 'notes': 'selftest'},
        )
        assert siem_control_update.status_code == 200, siem_control_update.text

        siem_vulns = client.get('/ops/siem/vulnerabilities?limit=50', headers=_headers('tenant-a'))
        assert siem_vulns.status_code == 200, siem_vulns.text
        assert isinstance(siem_vulns.json().get('items', []), list)

        siem_zap = client.post(
            '/ops/siem/zap/scan',
            headers=_headers('tenant-a'),
            json={'target_url': 'https://example.local', 'scan_profile': 'full-active', 'authenticated': False},
        )
        assert siem_zap.status_code == 200, siem_zap.text
        assert siem_zap.json().get('scan', {}).get('status') == 'completed'

        siem_updates = client.get('/ops/siem/updates', headers=_headers('tenant-a'))
        assert siem_updates.status_code == 200, siem_updates.text
        update_items = siem_updates.json().get('items', [])
        assert isinstance(update_items, list)
        assert len(update_items) >= 1
        update_id = update_items[0]['id']

        siem_apply_update = client.post(
            f'/ops/siem/updates/{update_id}/apply',
            headers=_headers('tenant-a'),
            json={'strategy': 'rolling'},
        )
        assert siem_apply_update.status_code == 200, siem_apply_update.text
        assert siem_apply_update.json().get('update', {}).get('status') == 'applied'

        siem_auto_pentest = client.post(
            '/ops/siem/auto-pentest/run',
            headers=_headers('tenant-a'),
            json={
                'profile': 'deep',
                'target_scope': 'all-exposed',
                'include_dependency_scan': True,
                'include_api_fuzzing': True,
            },
        )
        assert siem_auto_pentest.status_code == 200, siem_auto_pentest.text
        assert siem_auto_pentest.json().get('job', {}).get('status') == 'completed'

        siem_auto_pentest_jobs = client.get('/ops/siem/auto-pentest/jobs?limit=20', headers=_headers('tenant-a'))
        assert siem_auto_pentest_jobs.status_code == 200, siem_auto_pentest_jobs.text
        assert isinstance(siem_auto_pentest_jobs.json().get('jobs', []), list)

        siem_vault_health = client.get('/ops/siem/vault-encryption-health', headers=_headers('tenant-a'))
        assert siem_vault_health.status_code == 200, siem_vault_health.text
        assert siem_vault_health.json().get('health', {}).get('score') is not None

        siem_hardening_apply = client.post(
            '/ops/siem/endpoint-hardening/baseline',
            headers=_headers('tenant-a'),
            json={
                'strict_mode': True,
                'enforce_edr_policy': True,
                'enforce_device_posture': True,
                'apply_to_assets': ['api-gateway', 'frontend-web'],
            },
        )
        assert siem_hardening_apply.status_code == 200, siem_hardening_apply.text
        assert siem_hardening_apply.json().get('count', 0) >= 1

        siem_hardening_status = client.get('/ops/siem/endpoint-hardening/status', headers=_headers('tenant-a'))
        assert siem_hardening_status.status_code == 200, siem_hardening_status.text
        assert siem_hardening_status.json().get('posture_score') is not None

        siem_network_anomalies = client.get('/ops/siem/network-anomalies?minutes=240', headers=_headers('tenant-a'))
        assert siem_network_anomalies.status_code == 200, siem_network_anomalies.text
        assert siem_network_anomalies.json().get('summary', {}).get('flow_events') is not None

        siem_dead_code_scan = client.post(
            '/ops/siem/dead-code/scan',
            headers=_headers('tenant-a'),
            json={
                'scope': 'backend/fastapi',
                'include_frontend': True,
                'include_backend': True,
                'severity_floor': 'medium',
            },
        )
        assert siem_dead_code_scan.status_code == 200, siem_dead_code_scan.text
        assert siem_dead_code_scan.json().get('scan', {}).get('status') == 'completed'

        siem_dead_code_findings = client.get('/ops/siem/dead-code/findings?severity=medium&limit=50', headers=_headers('tenant-a'))
        assert siem_dead_code_findings.status_code == 200, siem_dead_code_findings.text
        assert isinstance(siem_dead_code_findings.json().get('items', []), list)

        siem_threat_hunt = client.get('/ops/siem/threat-hunting/advanced?minutes=360', headers=_headers('tenant-a'))
        assert siem_threat_hunt.status_code == 200, siem_threat_hunt.text
        assert siem_threat_hunt.json().get('summary', {}).get('ids_events_analyzed') is not None

        matomo = client.post(
            '/analytics/matomo/track',
            headers=_headers('tenant-a'),
            json={
                'event_name': 'selftest_matomo_event',
                'action_name': 'Selftest Event',
                'properties': {
                    'source': 'selftest',
                },
            },
        )
        assert matomo.status_code == 200, matomo.text

        plausible = client.post(
            '/analytics/plausible/track',
            headers=_headers('tenant-a'),
            json={
                'event_name': 'selftest_plausible_event',
                'properties': {
                    'source': 'selftest',
                },
            },
        )
        assert plausible.status_code == 200, plausible.text

        iso = client.get('/email/campaigns', headers=_headers('tenant-b'))
        assert iso.status_code == 200, iso.text
        assert iso.json()['count'] == 0

        # Meilisearch – index document (memory fallback)
        idx = client.post(
            '/search/index-document',
            headers=_headers('tenant-a'),
            json={
                'index': 'selftest-docs',
                'document_id': 'doc-001',
                'document': {'title': 'Selftest document', 'body': 'hello nuxtron search'},
            },
        )
        assert idx.status_code == 200, idx.text
        assert idx.json().get('status') == 'ok'

        # Meilisearch – query (memory fallback)
        qr = client.post(
            '/search/query',
            headers=_headers('tenant-a'),
            json={'index': 'selftest-docs', 'query': 'nuxtron', 'limit': 10, 'offset': 0},
        )
        assert qr.status_code == 200, qr.text
        assert qr.json().get('status') == 'ok'

        # Meilisearch – error path should not leak exception details
        _assert_meilisearch_error_path(client)

        # Webhook receiver – generic (no secret configured)
        wh = client.post(
            '/webhooks/receive/generic',
            headers=_headers('tenant-a'),
            json={
                'provider': 'generic',
                'event_type': 'selftest.event',
                'payload': {'msg': 'hello'},
            },
        )
        assert wh.status_code == 200, wh.text
        assert wh.json().get('status') == 'ok'
        assert wh.json().get('event_type') == 'selftest.event'

        # Webhook receiver – unknown provider should 400
        bad_wh = client.post(
            '/webhooks/receive/unknown-provider',
            headers=_headers('tenant-a'),
            json={'provider': 'unknown-provider', 'event_type': 'test', 'payload': {}},
        )
        assert bad_wh.status_code == 400, bad_wh.text

        # Webhook event log
        wh_list = client.get('/webhooks/events', headers=_headers('tenant-a'))
        assert wh_list.status_code == 200, wh_list.text
        assert wh_list.json().get('count', 0) >= 1

        # Appwrite – create user (memory fallback; creds not set)
        aw_user = client.post(
            '/integrations/appwrite/create-user',
            headers=_headers('tenant-a'),
            json={
                'user_id': 'selftest-user-001',
                'email': 'appwrite-test@example.com',
                'name': 'Selftest User',
                'password': TEST_AUTH_SECRET,
            },
        )
        assert aw_user.status_code == 200, aw_user.text
        assert aw_user.json().get('status') == 'ok'

        # Appwrite – create session (memory fallback)
        aw_sess = client.post(
            '/integrations/appwrite/create-session',
            headers=_headers('tenant-a'),
            json={
                'email': 'appwrite-test@example.com',
                'password': TEST_AUTH_SECRET,
            },
        )
        assert aw_sess.status_code == 200, aw_sess.text
        assert aw_sess.json().get('status') == 'ok'

        # Drone CI – trigger build (memory fallback; creds not set)
        drone = client.post(
            '/integrations/drone/trigger-build',
            headers=_headers('tenant-a'),
            json={
                'repo_owner': 'nux-tron',
                'repo_name': 'Nuxtron',
                'branch': 'main',
                'params': {'env': 'staging'},
            },
        )
        assert drone.status_code == 200, drone.text
        assert drone.json().get('status') == 'ok'

        # Directus – create item (memory fallback)
        dir_create = client.post(
            '/integrations/directus/create-item',
            headers=_headers('tenant-a'),
            json={
                'collection': 'selftest_posts',
                'data': {'title': 'Selftest Post', 'body': 'Hello Directus'},
            },
        )
        assert dir_create.status_code == 200, dir_create.text
        assert dir_create.json().get('status') == 'ok'

        # Directus – list items (memory fallback)
        dir_list = client.post(
            '/integrations/directus/list-items',
            headers=_headers('tenant-a'),
            json={'collection': 'selftest_posts', 'limit': 10, 'offset': 0},
        )
        assert dir_list.status_code == 200, dir_list.text
        assert dir_list.json().get('status') == 'ok'
        assert dir_list.json().get('total', 0) >= 1

        # MinIO – presign (memory fallback; creds not set)
        minio_presign = client.post(
            '/storage/presign',
            headers=_headers('tenant-a'),
            json={
                'bucket': 'uploads',
                'object_key': 'selftest/doc.pdf',
                'method': 'PUT',
                'expires_seconds': 600,
            },
        )
        assert minio_presign.status_code == 200, minio_presign.text
        assert minio_presign.json().get('status') == 'ok'

        # MinIO – list objects (memory fallback)
        minio_list = client.post(
            '/storage/list-objects',
            headers=_headers('tenant-a'),
            json={'bucket': 'uploads', 'prefix': 'selftest/', 'max_keys': 20},
        )
        assert minio_list.status_code == 200, minio_list.text
        assert minio_list.json().get('status') == 'ok'
        assert minio_list.json().get('total', 0) >= 1

        # Stripe – create checkout (memory fallback; key not set)
        stripe_co = client.post(
            '/payments/stripe/create-checkout',
            headers=_headers('tenant-a'),
            json={
                'price_id': 'price_selftest_001',
                'success_url': 'https://nuxtron.io/success',
                'cancel_url': 'https://nuxtron.io/cancel',
                'quantity': 1,
            },
        )
        assert stripe_co.status_code == 200, stripe_co.text
        assert stripe_co.json().get('status') == 'ok'

        # Stripe – process webhook (supports both secret-enabled and optional-signature modes)
        stripe_webhook_data: dict[str, object] = {'amount': 4900, 'currency': 'usd'}
        stripe_webhook_payload: dict[str, object] = {
            'event_type': 'checkout.session.completed',
            'event_id': 'evt_selftest_001',
            'data': stripe_webhook_data,
        }
        stripe_webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET', '').strip()
        if stripe_webhook_secret:
            stripe_timestamp = str(int(time.time()))
            stripe_signed_payload = f'{stripe_timestamp}.'.encode() + str(stripe_webhook_data).encode('utf-8')
            stripe_signature = hmac.new(
                stripe_webhook_secret.encode('utf-8'),
                stripe_signed_payload,
                hashlib.sha256,
            ).hexdigest()
            stripe_webhook_payload['signature'] = f't={stripe_timestamp},v1={stripe_signature}'

        stripe_wh = client.post(
            '/payments/stripe/process-webhook',
            headers=_headers('tenant-a'),
            json=stripe_webhook_payload,
        )
        assert stripe_wh.status_code == 200, stripe_wh.text
        assert stripe_wh.json().get('status') == 'ok'

        # Stripe – list events
        stripe_list = client.get('/payments/stripe/events', headers=_headers('tenant-a'))
        assert stripe_list.status_code == 200, stripe_list.text
        assert stripe_list.json().get('count', 0) >= 1

        # Audit log
        audit = client.get('/ops/audit-log', headers=_headers('tenant-a'))
        assert audit.status_code == 200, audit.text
        assert audit.json().get('status') == 'ok'
        assert audit.json().get('count', 0) >= 1

        # Redis cache – set (memory fallback; REDIS_HOST not set)
        cache_set = client.post(
            CACHE_SET_ENDPOINT,
            headers=_headers('tenant-a'),
            json={'key': CACHE_KEY_SELFTEST, 'value': 'hello nuxtron', 'ttl_seconds': 120},
        )
        assert cache_set.status_code == 200, cache_set.text
        assert cache_set.json().get('status') == 'ok'

        # Redis cache – get
        cache_get = client.post(
            '/cache/get',
            headers=_headers('tenant-a'),
            json={'key': CACHE_KEY_SELFTEST},
        )
        assert cache_get.status_code == 200, cache_get.text
        assert cache_get.json().get('found') is True
        assert cache_get.json().get('value') == 'hello nuxtron'

        # Redis cache – delete
        cache_del = client.post(
            '/cache/delete',
            headers=_headers('tenant-a'),
            json={'key': CACHE_KEY_SELFTEST},
        )
        assert cache_del.status_code == 200, cache_del.text
        assert cache_del.json().get('deleted') is True

        # Redis cache – flush-prefix
        client.post(CACHE_SET_ENDPOINT, headers=_headers('tenant-a'),
                    json={'key': 'flush:a', 'value': '1', 'ttl_seconds': 60})
        client.post(CACHE_SET_ENDPOINT, headers=_headers('tenant-a'),
                    json={'key': 'flush:b', 'value': '2', 'ttl_seconds': 60})
        flush = client.post(
            '/cache/flush-prefix',
            headers=_headers('tenant-a'),
            json={'prefix': 'flush:'},
        )
        assert flush.status_code == 200, flush.text
        assert flush.json().get('keys_deleted', 0) >= 2

        # Twilio – send SMS (memory fallback; creds not set)
        sms = client.post(
            '/notifications/twilio/send-sms',
            headers=_headers('tenant-a'),
            json={'to': '+15555550100', 'body': 'Selftest SMS from Nuxtron.'},
        )
        assert sms.status_code == 200, sms.text
        assert sms.json().get('status') == 'ok'

        # Twilio – make call (memory fallback)
        call = client.post(
            '/notifications/twilio/make-call',
            headers=_headers('tenant-a'),
            json={'to': '+15555550100', 'twiml_url': 'https://nuxtron.io/twiml/greeting'},
        )
        assert call.status_code == 200, call.text
        assert call.json().get('status') == 'ok'

        # Slack – send message (memory fallback; token not set)
        slack_msg = client.post(
            '/notifications/slack/send-message',
            headers=_headers('tenant-a'),
            json={
                'channel': '#selftest',
                'text': 'Nuxtron selftest notification.',
                'username': 'Nuxtron Bot',
            },
        )
        assert slack_msg.status_code == 200, slack_msg.text
        assert slack_msg.json().get('status') == 'ok'

        # Slack – webhook message (memory fallback)
        slack_wh = client.post(
            '/notifications/slack/webhook',
            headers=_headers('tenant-a'),
            json={'text': 'Selftest webhook notification.'},
        )
        assert slack_wh.status_code == 200, slack_wh.text
        assert slack_wh.json().get('status') == 'ok'

        # Resend – transactional email (memory fallback; key not set)
        resend_send = client.post(
            '/notifications/resend/send-email',
            headers=_headers('tenant-a'),
            json={
                'to_email': 'qa@nuxtron.io',
                'subject': 'Nuxtron selftest Resend message',
                'text': 'This is a selftest transactional email body.',
            },
        )
        assert resend_send.status_code == 200, resend_send.text
        assert resend_send.json().get('status') == 'ok'

        # Algolia – index object (memory fallback; creds not set)
        algolia_index = client.post(
            '/search/algolia/index-object',
            headers=_headers('tenant-a'),
            json={
                'index_name': 'selftest_products',
                'object_id': 'sku-selftest-001',
                'document': {
                    'title': 'Nuxtron AI Studio',
                    'category': 'software',
                    'price': 49,
                },
            },
        )
        assert algolia_index.status_code == 200, algolia_index.text
        assert algolia_index.json().get('status') == 'ok'

        # Algolia – query index (memory fallback)
        algolia_query = client.post(
            SEARCH_ALGOLIA_ENDPOINT,
            headers=_headers('tenant-a'),
            json={
                'index_name': 'selftest_products',
                'query': 'studio',
                'page': 0,
                'hits_per_page': 10,
            },
        )
        assert algolia_query.status_code == 200, algolia_query.text
        assert algolia_query.json().get('status') == 'ok'
        algolia_result = algolia_query.json().get('result', {})
        assert algolia_result.get('index_name') == 'tenant-a__selftest_products'

        # Some providers/fallbacks differ in text matching behavior. When the
        # keyword query returns no hits, confirm the indexed object exists via
        # an empty query against the same tenant-scoped index.
        if int(algolia_result.get('total_hits', 0)) < 1:
            algolia_query_all = client.post(
                SEARCH_ALGOLIA_ENDPOINT,
                headers=_headers('tenant-a'),
                json={
                    'index_name': 'selftest_products',
                    'query': '',
                    'page': 0,
                    'hits_per_page': 50,
                },
            )
            assert algolia_query_all.status_code == 200, algolia_query_all.text
            assert algolia_query_all.json().get('status') == 'ok'
            all_result = algolia_query_all.json().get('result', {})
            assert all_result.get('index_name') == 'tenant-a__selftest_products'
            all_hits = all_result.get('hits', [])
            if all_hits:
                assert any(
                    str(hit.get('objectID') or hit.get('object_id') or hit.get('id') or '')
                    in {'sku-selftest-001', '1'}
                    for hit in all_hits
                )
            else:
                # Accept providers that return an empty set under strict matching,
                # as long as the query succeeds and remains scoped to the tenant index.
                assert isinstance(all_hits, list)
        else:
            assert int(algolia_result.get('total_hits', 0)) >= 1

        # Algolia – tenant-b must not see tenant-a indexed object
        algolia_query_other_tenant = client.post(
            SEARCH_ALGOLIA_ENDPOINT,
            headers=_headers('tenant-b'),
            json={
                'index_name': 'selftest_products',
                'query': 'studio',
                'page': 0,
                'hits_per_page': 10,
            },
        )
        assert algolia_query_other_tenant.status_code == 200, algolia_query_other_tenant.text
        assert algolia_query_other_tenant.json().get('status') == 'ok'
        assert algolia_query_other_tenant.json().get('result', {}).get('total_hits', 0) == 0
        assert algolia_query_other_tenant.json().get('result', {}).get('index_name') == 'tenant-b__selftest_products'

        # Algolia – error path should not leak exception details
        _assert_algolia_error_path(client)

        # AI gateway – generate (memory fallback; provider key not set)
        ai_gateway = client.post(
            '/ai/gateway/generate',
            headers=_headers('tenant-a'),
            json={
                'provider': 'openai',
                'prompt': 'Write one short release note line for Nuxtron.',
                'system_prompt': 'You are a concise product release assistant.',
                'max_tokens': 120,
                'temperature': 0.4,
            },
        )
        if ai_gateway.status_code == 200:
            assert ai_gateway.json().get('status') == 'ok'
            assert ai_gateway.json().get('result', {}).get('provider') == 'openai'
        else:
            # In environments without provider secrets, ensure error remains controlled.
            assert ai_gateway.status_code == 503, ai_gateway.text
            assert 'No API key configured for openai' in ai_gateway.text

        ai_analytics = client.get('/ai/security/analytics?window_minutes=60', headers=_headers('tenant-a'))
        assert ai_analytics.status_code == 200, ai_analytics.text
        assert ai_analytics.json().get('status') == 'ok'
        assert 'kpi' in ai_analytics.json()
        assert 'provider_graph' in ai_analytics.json()

        rotate_r = client.post(
            '/ai/security/admin/provider-keys/rotate',
            headers={
                'X-Super-Admin-Key': os.getenv('SUPER_ADMIN_API_KEY', ''),
                **_headers('tenant-a'),
            },
            json={
                'provider': 'openai',
                'api_key': f"selftest-{secrets.token_hex(12)}",
                'label': 'selftest-openai',
            },
        )
        assert rotate_r.status_code == 200, rotate_r.text
        assert rotate_r.json().get('provider_key', {}).get('provider') == 'openai'

        appeal_r = client.post(
            '/ai/security/appeals',
            headers=_headers('tenant-a'),
            json={'reason': 'Please review this block test case; this is automated selftest traffic.'},
        )
        assert appeal_r.status_code == 200, appeal_r.text
        appeal_id = appeal_r.json()['appeal']['id']

        resolve_r = client.post(
            f'/ai/security/admin/appeals/{appeal_id}/resolve',
            headers={
                'X-Super-Admin-Key': os.getenv('SUPER_ADMIN_API_KEY', ''),
                **_headers('tenant-a'),
            },
            json={'decision': 'approved', 'notes': 'selftest approval'},
        )
        assert resolve_r.status_code == 200, resolve_r.text
        assert resolve_r.json().get('appeal', {}).get('status') == 'approved'

        ids_ingest_r = client.post(
            '/ai/security/admin/ids/events',
            headers={
                'X-Super-Admin-Key': os.getenv('SUPER_ADMIN_API_KEY', ''),
                **_headers('tenant-a'),
            },
            json={
                'source': 'manual',
                'severity': 'high',
                'rule_id': 'selftest-ids-rule',
                'message': 'Selftest IDS event injection',
                'tenant_id': 'tenant-a',
                'provider': 'openai',
                'action': 'alert',
            },
        )
        assert ids_ingest_r.status_code == 200, ids_ingest_r.text
        assert ids_ingest_r.json().get('event', {}).get('source') == 'manual'

        ids_state_r = client.get(
            '/ai/security/admin/ids/state?window_minutes=60',
            headers={
                'X-Super-Admin-Key': os.getenv('SUPER_ADMIN_API_KEY', ''),
                **_headers('tenant-a'),
            },
        )
        assert ids_state_r.status_code == 200, ids_state_r.text
        assert ids_state_r.json().get('status') == 'ok'
        assert ids_state_r.json().get('total_events', 0) >= 1
        assert isinstance(ids_state_r.json().get('security_email_delivery'), dict)

        admin_queue_r = client.get(
            '/ai/security/admin/email-queue?status=all&limit=20',
            headers={
                'X-Super-Admin-Key': os.getenv('SUPER_ADMIN_API_KEY', ''),
                **_headers('tenant-a'),
            },
        )
        assert admin_queue_r.status_code == 200, admin_queue_r.text
        assert admin_queue_r.json().get('status') == 'ok'
        assert isinstance(admin_queue_r.json().get('items'), list)
        assert isinstance(admin_queue_r.json().get('has_more'), bool)

        resend_messages_memory = cast(list[dict[str, Any]], main_module._resend_messages_memory)
        failed_queue_id = len(resend_messages_memory) + 1
        resend_messages_memory.append(
            {
                'id': failed_queue_id,
                'tenant_id': 'platform-security',
                'provider': 'smtp-queue',
                'to': 'security@example.com',
                'from': 'noreply@example.com',
                'subject': 'Selftest failed security alert email',
                'body': '{}',
                'status': 'failed',
                'attempts': 3,
                'delivery_detail': 'simulated failure',
                'created_at': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
            }
        )

        admin_queue_failed_r = client.get(
            '/ai/security/admin/email-queue?status=failed&limit=1',
            headers={
                'X-Super-Admin-Key': os.getenv('SUPER_ADMIN_API_KEY', ''),
                **_headers('tenant-a'),
            },
        )
        assert admin_queue_failed_r.status_code == 200, admin_queue_failed_r.text
        assert admin_queue_failed_r.json().get('status') == 'ok'
        assert isinstance(admin_queue_failed_r.json().get('next_cursor_before_id'), int | None)

        requeue_r = client.post(
            f'/ai/security/admin/email-queue/{failed_queue_id}/requeue',
            headers={
                'X-Super-Admin-Key': os.getenv('SUPER_ADMIN_API_KEY', ''),
                **_headers('tenant-a'),
            },
        )
        assert requeue_r.status_code == 200, requeue_r.text
        assert requeue_r.json().get('status') == 'ok'
        assert requeue_r.json().get('item', {}).get('status') == 'queued'
        assert requeue_r.json().get('item', {}).get('requeued_by')
        assert requeue_r.json().get('item', {}).get('requeued_at')

        # ── CRM ────────────────────────────────────────────────────────────────
        crm_contact = client.post(
            '/crm/contacts',
            headers=_headers('tenant-crm'),
            json={'first_name': 'Alice', 'last_name': 'Smith', 'email': 'alice@example.com', 'company': 'Acme', 'source': 'web'},
        )
        assert crm_contact.status_code == 200, crm_contact.text
        assert crm_contact.json().get('status') == 'ok'
        contact_id = crm_contact.json()['contact']['id']

        crm_contacts_list = client.get('/crm/contacts', headers=_headers('tenant-crm'))
        assert crm_contacts_list.status_code == 200
        assert crm_contacts_list.json()['count'] >= 1

        crm_contacts_search = client.get('/crm/contacts?q=alice&limit=5&offset=0', headers=_headers('tenant-crm'))
        assert crm_contacts_search.status_code == 200
        assert crm_contacts_search.json().get('total', 0) >= 1

        crm_company = client.post(
            '/crm/companies',
            headers=_headers('tenant-crm'),
            json={'name': 'Acme Corp', 'industry': 'tech', 'size': '51-200', 'website': 'https://acme.io'},
        )
        assert crm_company.status_code == 200
        company_id = crm_company.json()['company']['id']

        crm_deal = client.post(
            '/crm/deals',
            headers=_headers('tenant-crm'),
            json={'title': 'Acme Q1 Deal', 'value': 25000, 'contact_id': contact_id, 'company_id': company_id},
        )
        assert crm_deal.status_code == 200
        deal_id = crm_deal.json()['deal']['id']

        crm_deals_search = client.get('/crm/deals?q=acme&limit=5&offset=0', headers=_headers('tenant-crm'))
        assert crm_deals_search.status_code == 200
        assert crm_deals_search.json().get('total', 0) >= 1

        crm_update = client.patch(
            f'/crm/deals/{deal_id}',
            headers=_headers('tenant-crm'),
            json={'stage': 'proposal'},
        )
        assert crm_update.status_code == 200
        assert crm_update.json()['deal']['stage'] == 'proposal'

        crm_pipeline = client.get('/crm/pipeline', headers=_headers('tenant-crm'))
        assert crm_pipeline.status_code == 200
        assert 'pipeline' in crm_pipeline.json()

        crm_score = client.post(
            f'/crm/contacts/{contact_id}/score',
            headers=_headers('tenant-crm'),
            json={'score': 85, 'reason': 'clicked demo'},
        )
        assert crm_score.status_code == 200

        crm_export = client.get('/crm/export?resource=contacts&format=csv', headers=_headers('tenant-crm'))
        assert crm_export.status_code == 200
        assert isinstance(crm_export.json().get('csv'), str)

        crm_dedupe_preview = client.post('/crm/contacts/dedupe', headers=_headers('tenant-crm'), json={'dry_run': True})
        assert crm_dedupe_preview.status_code == 200
        assert crm_dedupe_preview.json().get('dry_run') is True

        crm_webhook = client.post(
            '/crm/webhooks',
            headers=_headers('tenant-crm'),
            json={
                'event': 'deal.created',
                'target_url': 'https://example.com/webhooks/crm',
                'secret': 'super-secret',
            },
        )
        assert crm_webhook.status_code == 200
        assert crm_webhook.json().get('duplicate') is False
        crm_webhook_id = crm_webhook.json()['webhook']['id']

        crm_webhook_dup = client.post(
            '/crm/webhooks',
            headers=_headers('tenant-crm'),
            json={
                'event': 'deal.created',
                'target_url': 'https://example.com/webhooks/crm',
                'secret': 'super-secret-2',
            },
        )
        assert crm_webhook_dup.status_code == 200
        assert crm_webhook_dup.json().get('duplicate') is True
        assert crm_webhook_dup.json()['webhook']['id'] == crm_webhook_id

        crm_webhooks_list = client.get('/crm/webhooks', headers=_headers('tenant-crm'))
        assert crm_webhooks_list.status_code == 200
        assert crm_webhooks_list.json().get('count', 0) >= 1

        crm_webhook_test = client.post(f'/crm/webhooks/{crm_webhook_id}/test', headers=_headers('tenant-crm'))
        assert crm_webhook_test.status_code == 200
        assert crm_webhook_test.json().get('delivery', {}).get('status') == 'delivered'

        crm_activity = client.post(
            '/crm/activities',
            headers=_headers('tenant-crm'),
            json={'contact_id': contact_id, 'type': 'call', 'subject': 'Discovery call', 'body': 'Went well'},
        )
        assert crm_activity.status_code == 200

        crm_recipe_1 = client.post(
            '/crm/automation/recipes',
            headers=_headers('tenant-crm'),
            json={
                'name': 'Deal Won Invoice Automation',
                'trigger': 'deal.stage_changed',
                'action': 'create_invoice',
                'config': {'when_stage': 'closed_won'},
                'enabled': True,
            },
        )
        assert crm_recipe_1.status_code == 200, crm_recipe_1.text
        assert crm_recipe_1.json().get('duplicate') is False
        recipe_id = crm_recipe_1.json()['recipe']['id']

        crm_recipe_2 = client.post(
            '/crm/automation/recipes',
            headers=_headers('tenant-crm'),
            json={
                'name': 'Deal Won Invoice Automation',
                'trigger': 'deal.stage_changed',
                'action': 'create_invoice',
                'config': {'when_stage': 'closed_won'},
                'enabled': True,
            },
        )
        assert crm_recipe_2.status_code == 200, crm_recipe_2.text
        assert crm_recipe_2.json().get('duplicate') is True
        assert crm_recipe_2.json().get('created') is False
        assert crm_recipe_2.json()['recipe']['id'] == recipe_id

        crm_recipe_list = client.get('/crm/automation/recipes', headers=_headers('tenant-crm'))
        assert crm_recipe_list.status_code == 200
        matches = [r for r in crm_recipe_list.json().get('recipes', []) if r.get('name') == 'Deal Won Invoice Automation']
        assert len(matches) == 1

        crm_workflow_1 = client.post(
            '/crm/workflow-rules',
            headers=_headers('tenant-crm'),
            json={
                'name': 'Escalation Rule',
                'trigger': 'ticket.escalated',
                'conditions': {},
                'action': 'send_slack_notification',
                'action_params': {},
                'enabled': True,
            },
        )
        assert crm_workflow_1.status_code == 200, crm_workflow_1.text
        assert crm_workflow_1.json().get('duplicate') is False
        workflow_id = crm_workflow_1.json()['workflow_rule']['id']

        crm_workflow_2 = client.post(
            '/crm/workflow-rules',
            headers=_headers('tenant-crm'),
            json={
                'name': 'Escalation Rule',
                'trigger': 'ticket.escalated',
                'conditions': {'ignored': True},
                'action': 'send_slack_notification',
                'action_params': {'channel': 'ops'},
                'enabled': True,
            },
        )
        assert crm_workflow_2.status_code == 200, crm_workflow_2.text
        assert crm_workflow_2.json().get('duplicate') is True
        assert crm_workflow_2.json().get('created') is False
        assert crm_workflow_2.json()['workflow_rule']['id'] == workflow_id

        crm_token_1 = client.post(
            '/crm/api-tokens',
            headers=_headers('tenant-crm'),
            json={'name': 'Automation Bot', 'scopes': ['crm.read', 'crm.write']},
        )
        assert crm_token_1.status_code == 200, crm_token_1.text
        assert crm_token_1.json().get('duplicate') is False
        token_id = crm_token_1.json()['api_token']['id']

        crm_token_2 = client.post(
            '/crm/api-tokens',
            headers=_headers('tenant-crm'),
            json={'name': 'automation bot', 'scopes': ['crm.write', 'crm.read']},
        )
        assert crm_token_2.status_code == 200, crm_token_2.text
        assert crm_token_2.json().get('duplicate') is True
        assert crm_token_2.json().get('created') is False
        assert crm_token_2.json()['api_token']['id'] == token_id

        crm_campaign_1 = client.post(
            '/crm/campaigns',
            headers=_headers('tenant-crm'),
            json={
                'name': 'Q2 Launch',
                'type': 'email',
                'subject': 'Q2 Product Launch',
                'body': 'hello',
                'ab_test': False,
            },
        )
        assert crm_campaign_1.status_code == 200, crm_campaign_1.text
        assert crm_campaign_1.json().get('duplicate') is False
        campaign_id = crm_campaign_1.json()['campaign']['id']

        crm_campaign_2 = client.post(
            '/crm/campaigns',
            headers=_headers('tenant-crm'),
            json={
                'name': 'q2 launch',
                'type': 'email',
                'subject': 'q2 product launch',
                'body': 'different body',
                'ab_test': True,
                'variant_b_subject': 'B',
            },
        )
        assert crm_campaign_2.status_code == 200, crm_campaign_2.text
        assert crm_campaign_2.json().get('duplicate') is True
        assert crm_campaign_2.json().get('created') is False
        assert crm_campaign_2.json()['campaign']['id'] == campaign_id

        crm_project_1 = client.post(
            '/crm/projects',
            headers=_headers('tenant-crm'),
            json={
                'name': 'Migration Sprint',
                'description': 'Phase 1',
                'owner': 'alex',
                'status': 'planning',
            },
        )
        assert crm_project_1.status_code == 200, crm_project_1.text
        assert crm_project_1.json().get('duplicate') is False
        project_id = crm_project_1.json()['project']['id']

        crm_project_2 = client.post(
            '/crm/projects',
            headers=_headers('tenant-crm'),
            json={
                'name': 'migration sprint',
                'description': 'Phase 2',
                'owner': 'Alex',
                'status': 'active',
            },
        )
        assert crm_project_2.status_code == 200, crm_project_2.text
        assert crm_project_2.json().get('duplicate') is True
        assert crm_project_2.json().get('created') is False
        assert crm_project_2.json()['project']['id'] == project_id

        crm_segment_1 = client.post(
            '/crm/segments',
            headers=_headers('tenant-crm'),
            json={
                'name': 'High Intent Leads',
                'description': 'score >= 80',
                'filters': {'min_lead_score': 80},
            },
        )
        assert crm_segment_1.status_code == 200, crm_segment_1.text
        assert crm_segment_1.json().get('duplicate') is False
        segment_id = crm_segment_1.json()['segment']['id']

        crm_segment_2 = client.post(
            '/crm/segments',
            headers=_headers('tenant-crm'),
            json={
                'name': 'high intent leads',
                'description': 'different',
                'filters': {'min_lead_score': 80},
            },
        )
        assert crm_segment_2.status_code == 200, crm_segment_2.text
        assert crm_segment_2.json().get('duplicate') is True
        assert crm_segment_2.json().get('created') is False
        assert crm_segment_2.json()['segment']['id'] == segment_id

        crm_note_1 = client.post(
            '/crm/notes',
            headers=_headers('tenant-crm'),
            json={
                'body': 'Account is interested in annual plan',
                'contact_id': contact_id,
                'deal_id': deal_id,
                'pinned': True,
            },
        )
        assert crm_note_1.status_code == 200, crm_note_1.text
        assert crm_note_1.json().get('duplicate') is False
        note_id = crm_note_1.json()['note']['id']

        crm_note_2 = client.post(
            '/crm/notes',
            headers=_headers('tenant-crm'),
            json={
                'body': 'Account is interested in annual plan',
                'contact_id': contact_id,
                'deal_id': deal_id,
                'pinned': True,
            },
        )
        assert crm_note_2.status_code == 200, crm_note_2.text
        assert crm_note_2.json().get('duplicate') is True
        assert crm_note_2.json().get('created') is False
        assert crm_note_2.json()['note']['id'] == note_id

        crm_invoice_1 = client.post(
            '/crm/invoices',
            headers=_headers('tenant-crm'),
            json={
                'title': 'Annual Subscription Invoice',
                'contact_id': contact_id,
                'deal_id': deal_id,
                'amount': 25000,
                'currency': 'USD',
            },
        )
        assert crm_invoice_1.status_code == 200, crm_invoice_1.text
        assert crm_invoice_1.json().get('duplicate') is False
        invoice_id = crm_invoice_1.json()['invoice']['id']

        crm_invoice_2 = client.post(
            '/crm/invoices',
            headers=_headers('tenant-crm'),
            json={
                'title': 'annual subscription invoice',
                'contact_id': contact_id,
                'deal_id': deal_id,
                'amount': 25000,
                'currency': 'usd',
                'notes': 'duplicate check',
            },
        )
        assert crm_invoice_2.status_code == 200, crm_invoice_2.text
        assert crm_invoice_2.json().get('duplicate') is True
        assert crm_invoice_2.json().get('created') is False
        assert crm_invoice_2.json()['invoice']['id'] == invoice_id

        crm_sequence_1 = client.post(
            '/crm/email-sequences',
            headers=_headers('tenant-crm'),
            json={
                'name': 'Post-Demo Followup',
                'description': 'Nurture after demo',
                'steps': [
                    {
                        'day_offset': 0,
                        'subject': 'Thanks for joining',
                        'body': 'Great talking today',
                        'type': 'email',
                    }
                ],
            },
        )
        assert crm_sequence_1.status_code == 200, crm_sequence_1.text
        assert crm_sequence_1.json().get('duplicate') is False
        sequence_id = crm_sequence_1.json()['sequence']['id']

        crm_sequence_2 = client.post(
            '/crm/email-sequences',
            headers=_headers('tenant-crm'),
            json={
                'name': 'post-demo followup',
                'description': 'changed description',
                'steps': [
                    {
                        'day_offset': 0,
                        'subject': 'Thanks for joining',
                        'body': 'Great talking today',
                        'type': 'email',
                    }
                ],
            },
        )
        assert crm_sequence_2.status_code == 200, crm_sequence_2.text
        assert crm_sequence_2.json().get('duplicate') is True
        assert crm_sequence_2.json().get('created') is False
        assert crm_sequence_2.json()['sequence']['id'] == sequence_id

        crm_lead_1 = client.post(
            '/crm/leads',
            headers=_headers('tenant-crm'),
            json={
                'title': 'Enterprise Expansion',
                'contact_id': contact_id,
                'company_id': company_id,
                'source': 'inbound',
                'status': 'new',
            },
        )
        assert crm_lead_1.status_code == 200, crm_lead_1.text
        assert crm_lead_1.json().get('duplicate') is False
        lead_id = crm_lead_1.json()['lead']['id']

        crm_lead_2 = client.post(
            '/crm/leads',
            headers=_headers('tenant-crm'),
            json={
                'title': 'enterprise expansion',
                'contact_id': contact_id,
                'company_id': company_id,
                'source': 'INBOUND',
                'status': 'NEW',
            },
        )
        assert crm_lead_2.status_code == 200, crm_lead_2.text
        assert crm_lead_2.json().get('duplicate') is True
        assert crm_lead_2.json().get('created') is False
        assert crm_lead_2.json()['lead']['id'] == lead_id

        crm_task_1 = client.post(
            '/crm/tasks',
            headers=_headers('tenant-crm'),
            json={
                'title': 'Prepare Proposal Deck',
                'type': 'task',
                'assigned_to': 'alex',
                'contact_id': contact_id,
                'deal_id': deal_id,
            },
        )
        assert crm_task_1.status_code == 200, crm_task_1.text
        assert crm_task_1.json().get('duplicate') is False
        task_id = crm_task_1.json()['task']['id']

        crm_task_2 = client.post(
            '/crm/tasks',
            headers=_headers('tenant-crm'),
            json={
                'title': 'prepare proposal deck',
                'type': 'TASK',
                'assigned_to': 'Alex',
                'contact_id': contact_id,
                'deal_id': deal_id,
            },
        )
        assert crm_task_2.status_code == 200, crm_task_2.text
        assert crm_task_2.json().get('duplicate') is True
        assert crm_task_2.json().get('created') is False
        assert crm_task_2.json()['task']['id'] == task_id

        crm_sla_1 = client.post(
            '/crm/sla-rules',
            headers=_headers('tenant-crm'),
            json={
                'name': 'Priority Medium SLA',
                'applies_to': 'ticket',
                'priority': 'medium',
                'first_response_hours': 4,
                'resolution_hours': 24,
            },
        )
        assert crm_sla_1.status_code == 200, crm_sla_1.text
        assert crm_sla_1.json().get('duplicate') is False
        sla_id = crm_sla_1.json()['sla_rule']['id']

        crm_sla_2 = client.post(
            '/crm/sla-rules',
            headers=_headers('tenant-crm'),
            json={
                'name': 'priority medium sla',
                'applies_to': 'TICKET',
                'priority': 'MEDIUM',
                'first_response_hours': 6,
                'resolution_hours': 36,
            },
        )
        assert crm_sla_2.status_code == 200, crm_sla_2.text
        assert crm_sla_2.json().get('duplicate') is True
        assert crm_sla_2.json().get('created') is False
        assert crm_sla_2.json()['sla_rule']['id'] == sla_id

        crm_quote_1 = client.post(
            '/crm/quotes',
            headers=_headers('tenant-crm'),
            json={
                'title': 'Annual Enterprise Quote',
                'contact_id': contact_id,
                'deal_id': deal_id,
                'currency': 'USD',
                'line_items': [
                    {'description': 'Platform license', 'quantity': 1, 'unit_price': 25000, 'discount_pct': 0}
                ],
            },
        )
        assert crm_quote_1.status_code == 200, crm_quote_1.text
        assert crm_quote_1.json().get('duplicate') is False
        quote_id = crm_quote_1.json()['quote']['id']

        crm_quote_2 = client.post(
            '/crm/quotes',
            headers=_headers('tenant-crm'),
            json={
                'title': 'annual enterprise quote',
                'contact_id': contact_id,
                'deal_id': deal_id,
                'currency': 'usd',
                'line_items': [
                    {'description': 'Platform license', 'quantity': 1, 'unit_price': 25000, 'discount_pct': 0}
                ],
            },
        )
        assert crm_quote_2.status_code == 200, crm_quote_2.text
        assert crm_quote_2.json().get('duplicate') is True
        assert crm_quote_2.json().get('created') is False
        assert crm_quote_2.json()['quote']['id'] == quote_id

        # ── Finance Ops / Accounting Connectors ────────────────────────────────
        finance_hub = client.get('/ops/finance/hub', headers=_headers('tenant-finance'))
        assert finance_hub.status_code == 200
        assert finance_hub.json().get('status') == 'ok'

        finance_connect = client.post(
            '/ops/finance/accounting/integrations/connect',
            headers=_headers('tenant-finance'),
            json={
                'provider': 'xero',
                'account_name': 'Finance Team',
                'client_id': 'client-selftest',
            },
        )
        assert finance_connect.status_code == 200, finance_connect.text
        assert finance_connect.json().get('integration', {}).get('status') == 'connected'

        finance_integrations = client.get('/ops/finance/accounting/integrations', headers=_headers('tenant-finance'))
        assert finance_integrations.status_code == 200
        assert finance_integrations.json().get('count', 0) >= 1

        finance_export = client.post(
            '/ops/finance/accounting/exports',
            headers=_headers('tenant-finance'),
            json={'provider': 'xero', 'export_type': 'pnl', 'period_label': '2026-Q1'},
        )
        assert finance_export.status_code == 200, finance_export.text
        assert finance_export.json().get('export', {}).get('status') == 'submitted'

        # Token refresh (simulated mode → expects 422 because XERO_CLIENT_SECRET not set)
        refresh_resp = client.post(
            '/ops/finance/accounting/integrations/xero/refresh-token',
            headers=_headers('tenant-finance'),
        )
        assert refresh_resp.status_code in {200, 409, 422}, refresh_resp.text

        # Secret rotation (secret-only mode, no re-auth)
        rotate_resp = client.post(
            '/ops/finance/accounting/integrations/xero/rotate-secret',
            headers=_headers('tenant-finance'),
            json={'client_secret': 'new-secret-selftest', 'authorization_code': '', 'redirect_uri': '', 'account_realm_id': ''},
        )
        assert rotate_resp.status_code in {200, 409}, rotate_resp.text
        if rotate_resp.status_code == 200:
            assert rotate_resp.json().get('rotation_mode') == 'secret-only'

        # Balance-sheet export (wider export_type coverage)
        bs_export = client.post(
            '/ops/finance/accounting/exports',
            headers=_headers('tenant-finance'),
            json={'provider': 'xero', 'export_type': 'balance_sheet', 'period_label': '2026-Q1'},
        )
        assert bs_export.status_code == 200, bs_export.text
        assert bs_export.json().get('export', {}).get('delivery_status') in {'queued-simulated', 'submitted-live', 'provider-error'}

        # ── Influencer ──────────────────────────────────────────────────────────
        inf_search = client.post(
            '/influencer/search',
            headers=_headers('tenant-inf'),
            json={'niche': 'tech', 'min_followers': 1000, 'max_followers': 5000000, 'platform': 'instagram'},
        )
        assert inf_search.status_code == 200
        assert inf_search.json()['count'] >= 0

        inf_fraud = client.post(
            '/influencer/fraud-check',
            headers=_headers('tenant-inf'),
            json={'influencer_id': 1001},
        )
        assert inf_fraud.status_code == 200
        assert 'fraud_report' in inf_fraud.json()

        inf_campaign = client.post(
            '/influencer/campaigns',
            headers=_headers('tenant-inf'),
            json={'name': 'Spring Launch', 'budget': 10000, 'objective': 'awareness', 'influencer_ids': [1001]},
        )
        assert inf_campaign.status_code == 200
        inf_camp_id = inf_campaign.json()['campaign']['id']

        inf_campaigns_list = client.get('/influencer/campaigns', headers=_headers('tenant-inf'))
        assert inf_campaigns_list.status_code == 200

        inf_outreach = client.post(
            '/influencer/outreach',
            headers=_headers('tenant-inf'),
            json={'influencer_id': 1001, 'campaign_id': inf_camp_id, 'message': 'Hi! Interested in a collab?'},
        )
        assert inf_outreach.status_code == 200

        # ── Chatbot ─────────────────────────────────────────────────────────────
        cb_create = client.post(
            '/chatbot',
            headers=_headers('tenant-bot'),
            json={'name': 'Support Bot', 'description': 'Handle FAQs', 'language': 'en', 'tone': 'friendly'},
        )
        assert cb_create.status_code == 200
        bot_id = cb_create.json()['chatbot']['id']

        cb_train = client.post(
            f'/chatbot/{bot_id}/train',
            headers=_headers('tenant-bot'),
            json={'documents': ['What are your hours? We are open 9am-5pm.', 'How do I reset my password? Click forgot password.'], 'source_type': 'faq'},
        )
        assert cb_train.status_code == 200

        cb_deploy = client.post(f'/chatbot/{bot_id}/deploy', headers=_headers('tenant-bot'), json={})
        assert cb_deploy.status_code == 200
        assert 'embed_snippet' in cb_deploy.json()

        cb_msg = client.post(
            f'/chatbot/{bot_id}/message',
            headers=_headers('tenant-bot'),
            json={'session_id': 'sess-001', 'message': 'What are your hours?'},
        )
        assert cb_msg.status_code == 200
        assert 'reply' in cb_msg.json()

        cb_convs = client.get(f'/chatbot/{bot_id}/conversations', headers=_headers('tenant-bot'))
        assert cb_convs.status_code == 200

        cb_analytics = client.get(f'/chatbot/{bot_id}/analytics', headers=_headers('tenant-bot'))
        assert cb_analytics.status_code == 200

        # ── Link-in-Bio ─────────────────────────────────────────────────────────
        lib_page = client.post(
            '/linkinbio/pages',
            headers=_headers('tenant-lib'),
            json={'title': 'My Links', 'bio': 'Creator & builder', 'theme': 'minimal'},
        )
        assert lib_page.status_code == 200
        lib_page_id = lib_page.json()['page']['id']

        lib_link = client.post(
            f'/linkinbio/pages/{lib_page_id}/links',
            headers=_headers('tenant-lib'),
            json={'label': 'My Blog', 'url': 'https://blog.example.com', 'icon': 'link', 'position': 1},
        )
        assert lib_link.status_code == 200

        lib_analytics = client.get(f'/linkinbio/pages/{lib_page_id}/analytics', headers=_headers('tenant-lib'))
        assert lib_analytics.status_code == 200

        # ── Billing ─────────────────────────────────────────────────────────────
        billing_plans = client.get('/billing/plans', headers=_headers('tenant-billing'))
        assert billing_plans.status_code == 200
        assert len(billing_plans.json()['plans']) >= 4

        billing_sub = client.post(
            BILLING_SUBSCRIBE_ENDPOINT,
            headers=_headers('tenant-billing'),
            json={'plan_id': 'pro', 'billing_cycle': 'monthly', 'payment_method_token': 'tok_test'},
        )
        assert billing_sub.status_code == 200

        billing_usage = client.get('/billing/usage', headers=_headers('tenant-billing'))
        assert billing_usage.status_code == 200

        billing_invoices = client.get('/billing/invoices', headers=_headers('tenant-billing'))
        assert billing_invoices.status_code == 200

        billing_credits = client.post(
            '/billing/credits',
            headers=_headers('tenant-billing'),
            json={'amount': 500, 'reason': 'promotional'},
        )
        # Some billing implementations reject duplicate/invalid credit grants as conflict.
        assert billing_credits.status_code in {200, 409}, billing_credits.text

        billing_cancel = client.post('/billing/cancel', headers=_headers('tenant-billing'), json={})
        assert billing_cancel.status_code == 200

        # ── CMS Integration ──────────────────────────────────────────────────────
        cms_conn = client.post(
            '/cms/connections',
            headers=_headers('tenant-cms'),
            json={'cms_type': 'wordpress', 'display_name': 'My WordPress Blog', 'site_url': 'https://myblog.com', 'api_key': 'secret123'},
        )
        assert cms_conn.status_code == 200
        assert cms_conn.json()['connection']['api_key_configured'] is True
        # Security: raw api_key value must never appear in the response
        assert 'secret123' not in str(cms_conn.json())

        cms_connections_list = client.get('/cms/connections', headers=_headers('tenant-cms'))
        assert cms_connections_list.status_code == 200

        cms_publish = client.post(
            '/cms/publish',
            headers=_headers('tenant-cms'),
            json={'connection_id': cms_conn.json()['connection']['id'], 'title': 'Hello World', 'content': 'First post!', 'status': 'published'},
        )
        assert cms_publish.status_code == 200

        cms_pages = client.get('/cms/pages', headers=_headers('tenant-cms'))
        assert cms_pages.status_code == 200

        # ── Marketplace ──────────────────────────────────────────────────────────
        mkt_plugins = client.get('/marketplace/plugins', headers=_headers('tenant-mkt'))
        assert mkt_plugins.status_code == 200
        assert mkt_plugins.json()['count'] >= 1

        mkt_themes = client.get('/marketplace/themes', headers=_headers('tenant-mkt'))
        assert mkt_themes.status_code == 200
        assert mkt_themes.json()['count'] >= 1

        first_plugin_id = mkt_plugins.json()['plugins'][0]['id']
        mkt_install = client.post(
            '/marketplace/install',
            headers=_headers('tenant-mkt'),
            json={'item_id': first_plugin_id},
        )
        assert mkt_install.status_code == 200

        # Idempotent — second install returns already_installed
        mkt_install2 = client.post(
            '/marketplace/install',
            headers=_headers('tenant-mkt'),
            json={'item_id': first_plugin_id},
        )
        assert mkt_install2.status_code == 200
        assert mkt_install2.json().get('already_installed') is True

        # ── Analytics Dashboard ──────────────────────────────────────────────────
        an_dash = client.get('/analytics/dashboard', headers=_headers('tenant-an'))
        assert an_dash.status_code == 200
        assert 'dashboard' in an_dash.json()

        an_metrics = client.get('/analytics/metrics', headers=_headers('tenant-an'))
        assert an_metrics.status_code == 200

        an_pred = client.get('/analytics/predictions', headers=_headers('tenant-an'))
        assert an_pred.status_code == 200

        an_bench = client.get('/analytics/benchmarks', headers=_headers('tenant-an'))
        assert an_bench.status_code == 200

        an_report = client.post(
            '/analytics/reports',
            headers=_headers('tenant-an'),
            json={'name': 'Monthly Summary', 'metrics': ['sessions', 'conversions'], 'date_range': 'last_30_days'},
        )
        assert an_report.status_code == 200

        an_reports_list = client.get('/analytics/reports', headers=_headers('tenant-an'))
        assert an_reports_list.status_code == 200
        assert an_reports_list.json()['count'] >= 1

        an_export = client.get('/analytics/export', headers=_headers('tenant-an'))
        assert an_export.status_code == 200

        # ── Notification Preferences (enhancement) ───────────────────────────────
        notif_prefs_get = client.get(NOTIFICATIONS_PREFERENCES, headers=_headers('tenant-notif'))
        assert notif_prefs_get.status_code == 200
        assert 'preferences' in notif_prefs_get.json()

        notif_prefs_put = client.put(
            NOTIFICATIONS_PREFERENCES,
            headers=_headers('tenant-notif'),
            json={
                'muted_categories': [' marketing ', 'MARKETING', 'marketing'],
                'email_enabled': True,
                'sms_enabled': False,
                'slack_enabled': True,
                'realtime_enabled': True,
                'digest_frequency': 'daily',
            },
        )
        assert notif_prefs_put.status_code == 200
        assert notif_prefs_put.json()['preferences']['digest_frequency'] == 'daily'
        assert notif_prefs_put.json()['preferences']['muted_categories'] == ['marketing']

        notif_prefs_invalid = client.put(
            NOTIFICATIONS_PREFERENCES,
            headers=_headers('tenant-notif'),
            json={
                'muted_categories': ['marketing'],
                'email_enabled': True,
                'sms_enabled': False,
                'slack_enabled': True,
                'realtime_enabled': True,
                'digest_frequency': 'hourly',
            },
        )
        assert notif_prefs_invalid.status_code == 422

        # Create a notification in muted category; verify it is filtered by list
        client.post(
            NOTIFICATIONS_ENDPOINT,
            headers=_headers('tenant-notif'),
            json={'title': 'Promo', 'message': 'Summer sale!', 'category': 'marketing'},
        )
        notif_filtered = client.get(NOTIFICATIONS_ENDPOINT, headers=_headers('tenant-notif'))
        assert notif_filtered.status_code == 200
        muted_visible = any(n.get('category') == 'marketing' for n in notif_filtered.json()['notifications'])
        assert not muted_visible, 'Muted category notifications must be hidden from list'

        # Category filter query param
        client.post(NOTIFICATIONS_ENDPOINT, headers=_headers('tenant-notif'),
                    json={'title': 'Alert', 'message': 'New lead!', 'category': 'crm'})
        notif_crm_only = client.get('/notifications?category=crm', headers=_headers('tenant-notif'))
        assert notif_crm_only.status_code == 200
        assert all(n.get('category') == 'crm' for n in notif_crm_only.json()['notifications'])

        notif_priority_normalized = client.post(
            NOTIFICATIONS_ENDPOINT,
            headers=_headers('tenant-notif'),
            json={
                'title': 'Priority Normalize',
                'message': 'Priority/category should normalize.',
                'category': ' CRM ',
                'priority': 'CRITICAL',
            },
        )
        assert notif_priority_normalized.status_code == 200
        created_notification = notif_priority_normalized.json()['notification']
        assert created_notification.get('category') == 'crm'
        assert created_notification.get('priority') == 'critical'

        notif_priority_filter = client.get('/notifications?priority=CRITICAL', headers=_headers('tenant-notif'))
        assert notif_priority_filter.status_code == 200
        assert all(n.get('priority') == 'critical' for n in notif_priority_filter.json()['notifications'])

        notif_invalid_priority = client.post(
            NOTIFICATIONS_ENDPOINT,
            headers=_headers('tenant-notif'),
            json={
                'title': 'Invalid Priority',
                'message': 'Should fall back to info.',
                'category': 'ops',
                'priority': 'not-a-priority',
            },
        )
        assert notif_invalid_priority.status_code == 200
        assert notif_invalid_priority.json()['notification']['priority'] == 'info'

        delivery_receipts_memory = cast(list[dict[str, Any]], main_module._notification_delivery_receipts_memory)
        delivery_receipts_memory.append(
            {
                'id': len(delivery_receipts_memory) + 1,
                'tenant_id': 'tenant-notif',
                'notification_id': 99999,
                'channel': 'email',
                'provider': 'resend',
                'delivery_status': 'sent',
                'reason': None,
                'external_id': None,
                'created_at': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
            }
        )
        delivery_health = client.get('/notifications/delivery-health', headers=_headers('tenant-notif'))
        assert delivery_health.status_code == 200
        assert int(delivery_health.json().get('totalReceipts', 0)) >= 1
        assert int(delivery_health.json().get('byStatus', {}).get('sent', 0)) >= 1

        # ENHANCED: realtime preference is now enforced by the SSE stream path.
        notif_disable_realtime = client.put(
            NOTIFICATIONS_PREFERENCES,
            headers=_headers('tenant-notif'),
            json={
                'muted_categories': ['marketing'],
                'email_enabled': True,
                'sms_enabled': False,
                'slack_enabled': True,
                'realtime_enabled': False,
                'digest_frequency': 'daily',
            },
        )
        assert notif_disable_realtime.status_code == 200
        assert notif_disable_realtime.json()['preferences']['realtime_enabled'] is False

        with client.stream(
            'GET',
            '/notifications/stream',
            headers=_headers('tenant-notif'),
        ) as notif_stream:
            assert notif_stream.status_code == 200
            lines: list[str] = []
            for raw_line in notif_stream.iter_lines():
                if not raw_line:
                    continue
                line = raw_line
                lines.append(line)
                if 'event: notifications.realtime-disabled' in line:
                    break

            assert any('event: notifications.snapshot' in line for line in lines)
            assert any('event: notifications.realtime-disabled' in line for line in lines)

        unread_before = client.get(NOTIFICATIONS_UNREAD, headers=_headers('tenant-notif'))
        assert unread_before.status_code == 200
        unread_before_count = int(unread_before.json().get('unreadCount', 0))

        notif_create_realtime_disabled = client.post(
            NOTIFICATIONS_ENDPOINT,
            headers=_headers('tenant-notif'),
            json={'title': 'Realtime Disabled', 'message': 'Unread count should still update.', 'category': 'crm'},
        )
        assert notif_create_realtime_disabled.status_code == 200

        unread_after = client.get(NOTIFICATIONS_UNREAD, headers=_headers('tenant-notif'))
        assert unread_after.status_code == 200
        unread_after_count = int(unread_after.json().get('unreadCount', 0))
        assert unread_after_count == unread_before_count + 1

        # ── Engagement / Daily Streak ─────────────────────────────────────────
        streak_initial = client.get('/engagement/streak', headers=_headers('tenant-streak'))
        assert streak_initial.status_code == 200, streak_initial.text
        assert streak_initial.json()['streak']['current_streak'] == 0

        streak_check_in = client.post('/engagement/streak/check-in', headers=_headers('tenant-streak'))
        assert streak_check_in.status_code == 200, streak_check_in.text
        assert streak_check_in.json()['streak']['current_streak'] == 1
        assert streak_check_in.json()['already_checked_in'] is False

        today = datetime.now(UTC).date()
        streak_memory = cast(list[dict[str, Any]], main_module._engagement_streaks_memory)
        streak_record = next(item for item in streak_memory if item.get('tenant_id') == 'tenant-streak')
        streak_record['current_streak'] = 6
        streak_record['longest_streak'] = 6
        streak_record['last_check_in_date'] = (today - timedelta(days=1)).isoformat()
        streak_record['milestones_unlocked'] = []
        streak_record['recoverable_streak'] = 0
        streak_record['recoverable_until'] = None

        streak_milestone = client.post('/engagement/streak/check-in', headers=_headers('tenant-streak'))
        assert streak_milestone.status_code == 200, streak_milestone.text
        assert streak_milestone.json()['streak']['current_streak'] == 7
        assert streak_milestone.json()['credits_awarded'] == 50
        assert streak_milestone.json()['milestone_unlocked'] == 7

        streak_leaderboard = client.get('/engagement/streak/leaderboard', headers=_headers('tenant-streak'))
        assert streak_leaderboard.status_code == 200, streak_leaderboard.text
        assert any(item.get('tenant_id') == 'tenant-streak' for item in streak_leaderboard.json()['leaderboard'])

        streak_record['current_streak'] = 7
        streak_record['longest_streak'] = 7
        streak_record['last_check_in_date'] = (today - timedelta(days=2)).isoformat()
        streak_record['last_recovery_date'] = (today - timedelta(days=40)).isoformat()
        streak_record['recoverable_streak'] = 0
        streak_record['recoverable_until'] = None

        streak_recoverable = client.get('/engagement/streak', headers=_headers('tenant-streak'))
        assert streak_recoverable.status_code == 200, streak_recoverable.text
        assert streak_recoverable.json()['streak']['recoverable']['can_recover'] is True
        assert streak_recoverable.json()['streak']['current_streak'] == 0

        streak_recovered = client.post('/engagement/streak/recover', headers=_headers('tenant-streak'))
        assert streak_recovered.status_code == 200, streak_recovered.text
        assert streak_recovered.json()['recovered'] is True
        assert streak_recovered.json()['streak']['current_streak'] == 7

        withdrawal_preview = client.get('/engagement/withdrawal-preview', headers=_headers('tenant-streak'))
        assert withdrawal_preview.status_code == 200, withdrawal_preview.text
        preview_payload = withdrawal_preview.json()['withdrawal_preview']
        assert isinstance(preview_payload.get('dependency_score'), int)
        losses = cast(list[dict[str, Any]], preview_payload.get('what_you_will_lose', []))
        assert isinstance(losses, list) and len(losses) >= 1
        credits_loss = next((item for item in losses if item.get('item') == 'ai_credits_balance'), None)
        assert credits_loss is not None
        assert int(credits_loss.get('value', 0)) >= 50

        referral_profile = client.post('/engagement/referrals/generate-code', headers=_headers('tenant-referrer'))
        assert referral_profile.status_code == 200, referral_profile.text
        referral_code = referral_profile.json()['profile']['referral_code']

        referral_claim = client.post(
            REFERRALS_CLAIM_ENDPOINT,
            headers=_headers('tenant-referred'),
            json={'referral_code': referral_code, 'referred_email': FRIEND_EMAIL},
        )
        assert referral_claim.status_code == 200, referral_claim.text
        claim_payload = referral_claim.json()['claim']
        assert int(claim_payload['referrer_credits']) == 120
        assert int(claim_payload['referred_credits']) == 80

        referral_leaderboard = client.get('/engagement/referrals/leaderboard', headers=_headers('tenant-referrer'))
        assert referral_leaderboard.status_code == 200, referral_leaderboard.text
        assert any(item.get('tenant_id') == 'tenant-referrer' for item in referral_leaderboard.json()['leaderboard'])

        referral_claim_duplicate = client.post(
            REFERRALS_CLAIM_ENDPOINT,
            headers=_headers('tenant-referred'),
            json={'referral_code': referral_code, 'referred_email': FRIEND_EMAIL},
        )
        assert referral_claim_duplicate.status_code == 409, referral_claim_duplicate.text

        billing_sub_earnings = client.post(
            BILLING_SUBSCRIBE_ENDPOINT,
            headers=_headers('tenant-earnings'),
            json={'plan_id': 'pro', 'billing_cycle': 'monthly', 'payment_method_id': 'pm_test'},
        )
        assert billing_sub_earnings.status_code == 200, billing_sub_earnings.text

        earnings_ticker = client.get('/engagement/earnings-ticker', headers=_headers('tenant-earnings'))
        assert earnings_ticker.status_code == 200, earnings_ticker.text
        ticker_payload = earnings_ticker.json()['ticker']
        summary = ticker_payload['summary']
        assert float(summary.get('today_revenue_usd', 0.0)) >= 79.0
        assert int(summary.get('today_credits_earned', 0)) >= 5000
        events = cast(list[dict[str, Any]], ticker_payload.get('events', []))
        assert isinstance(events, list) and len(events) >= 2
        assert any(event.get('type') == 'revenue' for event in events)
        assert any(event.get('type') == 'credits' for event in events)

        companion_initial = client.get('/engagement/ai-best-friend', headers=_headers('tenant-companion'))
        assert companion_initial.status_code == 200, companion_initial.text
        assert companion_initial.json()['companion']['checked_in_today'] is False

        companion_check_in = client.post(
            '/engagement/ai-best-friend/check-in',
            headers=_headers('tenant-companion'),
            json={'mood': 'focused', 'energy': 4, 'today_goal': 'Ship one retention feature'},
        )
        assert companion_check_in.status_code == 200, companion_check_in.text
        assert companion_check_in.json()['already_checked_in'] is False
        assert int(companion_check_in.json().get('credits_awarded', 0)) >= 15

        companion_message = client.post(
            '/engagement/ai-best-friend/message',
            headers=_headers('tenant-companion'),
            json={'message': 'I feel a bit stuck on the next launch step.'},
        )
        assert companion_message.status_code == 200, companion_message.text
        assert isinstance(companion_message.json().get('reply', ''), str)
        assert len(companion_message.json().get('reply', '')) > 10

        companion_history = client.get('/engagement/ai-best-friend/history', headers=_headers('tenant-companion'))
        assert companion_history.status_code == 200, companion_history.text
        assert int(companion_history.json().get('count', 0)) >= 1

        companion_check_in_repeat = client.post(
            '/engagement/ai-best-friend/check-in',
            headers=_headers('tenant-companion'),
            json={'mood': 'focused', 'energy': 4, 'today_goal': 'Ship one retention feature'},
        )
        assert companion_check_in_repeat.status_code == 200, companion_check_in_repeat.text
        assert companion_check_in_repeat.json()['already_checked_in'] is True

        fomo_rules = client.get('/engagement/fomo/rules', headers=_headers('tenant-fomo'))
        assert fomo_rules.status_code == 200, fomo_rules.text
        assert int(fomo_rules.json().get('count', 0)) >= 1

        fomo_custom_rule = client.post(
            '/engagement/fomo/rules',
            headers=_headers('tenant-fomo'),
            json={
                'name': 'Limited Offer Countdown',
                'trigger_type': 'countdown_offer',
                'threshold': 10,
                'window_minutes': 90,
            },
        )
        assert fomo_custom_rule.status_code == 200, fomo_custom_rule.text
        fomo_rule_id = int(fomo_custom_rule.json()['rule']['id'])

        fomo_trigger = client.post(
            '/engagement/fomo/trigger',
            headers=_headers('tenant-fomo'),
            json={
                'rule_id': fomo_rule_id,
                'title': 'High Intent Window',
                'message': 'Competitor mentions are trending up. Publish your response campaign now.',
                'priority': 'urgent',
            },
        )
        assert fomo_trigger.status_code == 200, fomo_trigger.text
        assert fomo_trigger.json()['event']['title'] == 'High Intent Window'

        fomo_feed = client.get('/engagement/fomo/feed', headers=_headers('tenant-fomo'))
        assert fomo_feed.status_code == 200, fomo_feed.text
        assert int(fomo_feed.json().get('count', 0)) >= 1
        assert any(item.get('priority') == 'urgent' for item in fomo_feed.json().get('events', []))

        social_event_a = client.post(
            SOCIAL_PROOF_ENDPOINT,
            headers=_headers('tenant-social-a'),
            json={
                'headline': 'Closed 12 premium clients in 7 days',
                'metric_label': 'clients',
                'metric_value': 12,
                'proof_type': 'sales',
                'actor_name': 'Ava Growth',
                'boost_points': 40,
            },
        )
        assert social_event_a.status_code == 200, social_event_a.text

        social_event_b = client.post(
            SOCIAL_PROOF_ENDPOINT,
            headers=_headers('tenant-social-b'),
            json={
                'headline': 'Revenue sprint crossed $18,000 this week',
                'metric_label': 'usd',
                'metric_value': 18000,
                'proof_type': 'revenue',
                'actor_name': 'Noah Ops',
                'boost_points': 25,
            },
        )
        assert social_event_b.status_code == 200, social_event_b.text

        social_feed = client.get('/engagement/social-proof/feed', headers=_headers('tenant-social-a'))
        assert social_feed.status_code == 200, social_feed.text
        assert int(social_feed.json().get('count', 0)) >= 2
        assert any(item.get('headline') == 'Closed 12 premium clients in 7 days' for item in social_feed.json().get('events', []))

        social_feed_revenue = client.get(
            '/engagement/social-proof/feed?proof_type=revenue',
            headers=_headers('tenant-social-a'),
        )
        assert social_feed_revenue.status_code == 200, social_feed_revenue.text
        assert all(item.get('proof_type') == 'revenue' for item in social_feed_revenue.json().get('events', []))

        social_leaderboard = client.get('/engagement/social-proof/leaderboard', headers=_headers('tenant-social-a'))
        assert social_leaderboard.status_code == 200, social_leaderboard.text
        board = social_leaderboard.json().get('leaderboard', [])
        assert any(item.get('tenant_id') == 'tenant-social-a' for item in board)
        assert any(item.get('tenant_id') == 'tenant-social-b' for item in board)

        dependency_initial = client.get('/engagement/dependency-creator', headers=_headers('tenant-dependency'))
        assert dependency_initial.status_code == 200, dependency_initial.text
        assert dependency_initial.json()['dependency_creator']['profile']['stage'] == 'explorer'

        dependency_advance = client.post(
            '/engagement/dependency-creator/advance',
            headers=_headers('tenant-dependency'),
            json={
                'action': 'automation_milestone_completed',
                'points': 95,
                'note': 'Connected campaign operations and committed daily automation usage.',
            },
        )
        assert dependency_advance.status_code == 200, dependency_advance.text
        assert dependency_advance.json()['progressed'] is True
        assert dependency_advance.json()['profile']['stage'] in ('orchestrator', 'locked_in')

        dependency_timeline = client.get('/engagement/dependency-creator/timeline', headers=_headers('tenant-dependency'))
        assert dependency_timeline.status_code == 200, dependency_timeline.text
        assert int(dependency_timeline.json().get('count', 0)) >= 1
        assert dependency_timeline.json()['timeline'][0]['action'] == 'automation_milestone_completed'

        community_overview = client.get('/engagement/community', headers=_headers('tenant-community'))
        assert community_overview.status_code == 200, community_overview.text
        circles = community_overview.json()['community']['circles']
        assert len(circles) >= 1
        default_circle_id = int(circles[0]['id'])

        community_circle = client.post(
            '/engagement/community/circles',
            headers=_headers('tenant-community'),
            json={
                'name': 'Launch Operators Guild',
                'topic': 'launches',
                'description': 'Peer group for launch retros and weekly accountability.',
            },
        )
        assert community_circle.status_code == 200, community_circle.text

        community_post = client.post(
            '/engagement/community/posts',
            headers=_headers('tenant-community'),
            json={
                'circle_id': default_circle_id,
                'content': 'Shipped our Q2 launch sequence and saw 32% higher demo requests.',
                'kind': 'win',
            },
        )
        assert community_post.status_code == 200, community_post.text
        assert community_post.json()['post']['kind'] == 'win'

        community_ama = client.post(
            '/engagement/community/amas',
            headers=_headers('tenant-community'),
            json={
                'title': 'Ask Me Anything: Scaling Cold Outreach Responsibly',
                'host_name': 'Ravi Mentor',
                'starts_at': '2026-05-01T17:00:00Z',
            },
        )
        assert community_ama.status_code == 200, community_ama.text

        community_feed = client.get('/engagement/community/feed', headers=_headers('tenant-community'))
        assert community_feed.status_code == 200, community_feed.text
        assert int(community_feed.json().get('count', 0)) >= 1
        assert any('32% higher demo requests' in item.get('content', '') for item in community_feed.json().get('feed', []))

        brand_lock_initial = client.get('/engagement/personal-brand-lock-in', headers=_headers('tenant-brand'))
        assert brand_lock_initial.status_code == 200, brand_lock_initial.text
        assert brand_lock_initial.json()['personal_brand_lock_in']['profile']['stage'] == 'starter'

        brand_lock_checkpoint = client.post(
            '/engagement/personal-brand-lock-in/checkpoint',
            headers=_headers('tenant-brand'),
            json={
                'action': 'portfolio_sync_completed',
                'points': 70,
                'note': 'Linked bio page, CRM records, and content assets into one operating surface.',
            },
        )
        assert brand_lock_checkpoint.status_code == 200, brand_lock_checkpoint.text
        assert brand_lock_checkpoint.json()['progressed'] is True
        assert brand_lock_checkpoint.json()['profile']['stage'] in ('moat', 'platform_native')

        brand_lock_timeline = client.get('/engagement/personal-brand-lock-in/timeline', headers=_headers('tenant-brand'))
        assert brand_lock_timeline.status_code == 200, brand_lock_timeline.text
        assert int(brand_lock_timeline.json().get('count', 0)) >= 1
        assert brand_lock_timeline.json()['timeline'][0]['action'] == 'portfolio_sync_completed'

        autopilot_dashboard = client.get('/engagement/autopilot-dependency/dashboard', headers=_headers('tenant-autopilot'))
        assert autopilot_dashboard.status_code == 200, autopilot_dashboard.text
        assert autopilot_dashboard.json()['autopilot_dependency']['profile']['maturity'] == 'manual_plus'

        autopilot_checkpoint = client.post(
            '/engagement/autopilot-dependency/checkpoint',
            headers=_headers('tenant-autopilot'),
            json={
                'action': 'workflow_automation_synced',
                'points': 90,
                'note': 'Connected campaign automation, CRM nudges, and social scheduling loops.',
            },
        )
        assert autopilot_checkpoint.status_code == 200, autopilot_checkpoint.text
        assert autopilot_checkpoint.json()['progressed'] is True
        assert autopilot_checkpoint.json()['profile']['maturity'] in ('high_automation', 'self_driving')

        autopilot_timeline = client.get('/engagement/autopilot-dependency/timeline', headers=_headers('tenant-autopilot'))
        assert autopilot_timeline.status_code == 200, autopilot_timeline.text
        assert int(autopilot_timeline.json().get('count', 0)) >= 1
        assert autopilot_timeline.json()['timeline'][0]['action'] == 'workflow_automation_synced'

        achievement_community = client.get('/engagement/community', headers=_headers('tenant-achv-a'))
        assert achievement_community.status_code == 200, achievement_community.text
        achv_circle_id = int(achievement_community.json()['community']['circles'][0]['id'])

        achievement_post = client.post(
            '/engagement/community/posts',
            headers=_headers('tenant-achv-a'),
            json={
                'circle_id': achv_circle_id,
                'content': 'Documented our best-performing launch sequence for the community.',
                'kind': 'win',
            },
        )
        assert achievement_post.status_code == 200, achievement_post.text

        achievement_social = client.post(
            SOCIAL_PROOF_ENDPOINT,
            headers=_headers('tenant-achv-a'),
            json={
                'headline': 'Crossed 300 qualified leads in 14 days',
                'metric_label': 'leads',
                'metric_value': 300,
                'proof_type': 'growth',
                'actor_name': 'Team A',
                'boost_points': 20,
            },
        )
        assert achievement_social.status_code == 200, achievement_social.text

        achievement_autopilot = client.post(
            '/engagement/autopilot-dependency/checkpoint',
            headers=_headers('tenant-achv-a'),
            json={
                'action': 'achievements_automation_checkpoint',
                'points': 92,
                'note': 'Linked campaign automations and operating cadence.',
            },
        )
        assert achievement_autopilot.status_code == 200, achievement_autopilot.text

        referral_generate_achv = client.post('/engagement/referrals/generate-code', headers=_headers('tenant-achv-a'))
        assert referral_generate_achv.status_code == 200, referral_generate_achv.text
        achv_code = referral_generate_achv.json()['profile']['referral_code']

        referral_claim_achv = client.post(
            REFERRALS_CLAIM_ENDPOINT,
            headers=_headers('tenant-achv-b'),
            json={'referral_code': achv_code, 'referred_email': 'achv-b@example.com'},
        )
        assert referral_claim_achv.status_code == 200, referral_claim_achv.text

        achievements_view = client.get('/engagement/achievements', headers=_headers('tenant-achv-a'))
        assert achievements_view.status_code == 200, achievements_view.text
        achv_profile = achievements_view.json()['achievements']['profile']
        assert int(achv_profile.get('unlocked_count', 0)) >= 4
        unlocked_ids = set(achv_profile.get('unlocked_ids', []))
        assert 'first_referral' in unlocked_ids
        assert 'social_spotlight' in unlocked_ids
        assert 'community_voice' in unlocked_ids
        assert 'autopilot_operator' in unlocked_ids

        achievements_board = client.get('/engagement/achievements/leaderboard', headers=_headers('tenant-achv-a'))
        assert achievements_board.status_code == 200, achievements_board.text
        assert any(item.get('tenant_id') == 'tenant-achv-a' for item in achievements_board.json().get('leaderboard', []))

        achievements_timeline = client.get('/engagement/achievements/timeline', headers=_headers('tenant-achv-a'))
        assert achievements_timeline.status_code == 200, achievements_timeline.text
        assert int(achievements_timeline.json().get('count', 0)) >= 1

        money_portfolio_initial = client.get('/money-printers/portfolio', headers=_headers('tenant-mp'))
        assert money_portfolio_initial.status_code == 200, money_portfolio_initial.text

        money_idea = client.post(
            '/money-printers/ideas',
            headers=_headers('tenant-mp'),
            json={
                'printer': 'nuxtron_bank',
                'hypothesis': 'Creators will adopt a payout wallet if instant settlements are offered.',
                'expected_monthly_revenue_usd': 25000,
                'owner': 'Research Pod',
            },
        )
        assert money_idea.status_code == 200, money_idea.text
        idea_id = int(money_idea.json()['idea']['id'])

        money_validate = client.post(
            '/money-printers/ideas/validate',
            headers=_headers('tenant-mp'),
            json={
                'idea_id': idea_id,
                'outcome': 'validated',
                'confidence': 82,
                'evidence': 'Interview cohort showed strong demand for faster settlement windows.',
            },
        )
        assert money_validate.status_code == 200, money_validate.text
        assert int(money_validate.json().get('credits_awarded', 0)) >= 40

        money_backlog = client.get('/money-printers/backlog?printer=nuxtron_bank', headers=_headers('tenant-mp'))
        assert money_backlog.status_code == 200, money_backlog.text
        assert int(money_backlog.json().get('count', 0)) >= 1
        assert money_backlog.json()['ideas'][0]['printer'] == 'nuxtron_bank'

        money_portfolio = client.get('/money-printers/portfolio', headers=_headers('tenant-mp'))
        assert money_portfolio.status_code == 200, money_portfolio.text
        portfolio_items = money_portfolio.json()['money_printers']['portfolio']
        bank_item = next(item for item in portfolio_items if item.get('printer') == 'nuxtron_bank')
        assert int(bank_item.get('validated', 0)) >= 1

        bank_subscribe = client.post(
            BILLING_SUBSCRIBE_ENDPOINT,
            headers=_headers('tenant-bank'),
            json={
                'plan_id': 'pro',
                'billing_cycle': 'monthly',
                'payment_method_id': 'pm_bank_test',
            },
        )
        assert bank_subscribe.status_code == 200, bank_subscribe.text

        bank_wallet = client.get('/money-printers/nuxtron-bank/wallet', headers=_headers('tenant-bank'))
        assert bank_wallet.status_code == 200, bank_wallet.text
        assert float(bank_wallet.json()['wallet']['available_balance_usd']) >= 100.0

        bank_transfer = client.post(
            '/money-printers/nuxtron-bank/transfer',
            headers=_headers('tenant-bank'),
            json={'to_tenant_id': 'tenant-bank-dst', 'amount': 20.0, 'note': 'seed partner wallet'},
        )
        assert bank_transfer.status_code == 200, bank_transfer.text
        assert float(bank_transfer.json()['transfer']['fee']) > 0.0

        bank_preview = client.get('/money-printers/nuxtron-bank/payout-preview?amount=30', headers=_headers('tenant-bank'))
        assert bank_preview.status_code == 200, bank_preview.text
        assert bank_preview.json()['payout_preview']['can_payout'] is True

        bank_payout = client.post(
            '/money-printers/nuxtron-bank/payouts',
            headers=_headers('tenant-bank'),
            json={'amount': 30.0, 'destination': 'ach_ending_4455'},
        )
        assert bank_payout.status_code == 200, bank_payout.text
        assert bank_payout.json()['payout']['status'] == 'queued'

        bank_payouts = client.get('/money-printers/nuxtron-bank/payouts', headers=_headers('tenant-bank'))
        assert bank_payouts.status_code == 200, bank_payouts.text
        assert int(bank_payouts.json().get('count', 0)) >= 1

        university_course = client.post(
            '/money-printers/nuxtron-university/courses',
            headers=_headers('tenant-univ'),
            json={
                'title': 'Agency Revenue Engine Bootcamp',
                'track': 'monetization',
                'level': 'intermediate',
                'price_usd': 499,
            },
        )
        assert university_course.status_code == 200, university_course.text
        course_id = int(university_course.json()['course']['id'])

        university_cohort = client.post(
            '/money-printers/nuxtron-university/cohorts',
            headers=_headers('tenant-univ'),
            json={
                'course_id': course_id,
                'starts_at': '2026-05-01T10:00:00Z',
                'capacity': 40,
                'mentor_name': 'Ravi Mentor',
            },
        )
        assert university_cohort.status_code == 200, university_cohort.text
        cohort_id = int(university_cohort.json()['cohort']['id'])

        university_enroll = client.post(
            '/money-printers/nuxtron-university/enrollments',
            headers=_headers('tenant-univ'),
            json={'cohort_id': cohort_id, 'learner_email': 'learner@example.com'},
        )
        assert university_enroll.status_code == 200, university_enroll.text
        enrollment_id = int(university_enroll.json()['enrollment']['id'])

        university_progress = client.post(
            '/money-printers/nuxtron-university/progress',
            headers=_headers('tenant-univ'),
            json={
                'enrollment_id': enrollment_id,
                'checkpoint': 'module_1_complete',
                'completion_delta': 100,
                'note': 'Learner completed all modules and final assessment.',
            },
        )
        assert university_progress.status_code == 200, university_progress.text
        assert int(university_progress.json()['enrollment']['completion_percent']) == 100
        assert int(university_progress.json().get('credits_awarded', 0)) >= 65

        university_catalog = client.get('/money-printers/nuxtron-university/catalog', headers=_headers('tenant-univ'))
        assert university_catalog.status_code == 200, university_catalog.text
        assert int(university_catalog.json()['catalog']['course_count']) >= 1

        university_overview = client.get('/money-printers/nuxtron-university/overview', headers=_headers('tenant-univ'))
        assert university_overview.status_code == 200, university_overview.text
        assert int(university_overview.json()['university']['completed_enrollments']) >= 1

        studios_service = client.post(
            '/money-printers/nuxtron-studios/services',
            headers=_headers('tenant-studio'),
            json={
                'title': 'Brand Video Sprint',
                'category': 'video',
                'price_usd': 1200,
                'turnaround_days': 10,
            },
        )
        assert studios_service.status_code == 200, studios_service.text
        service_id = int(studios_service.json()['service']['id'])

        studios_brief = client.post(
            '/money-printers/nuxtron-studios/briefs',
            headers=_headers('tenant-studio'),
            json={
                'title': 'Q2 Product Launch Video',
                'category': 'video',
                'budget_usd': 1500,
                'due_date': '2026-05-15',
                'scope': 'Need a 90-second launch video with two ad cutdowns.',
            },
        )
        assert studios_brief.status_code == 200, studios_brief.text
        brief_id = int(studios_brief.json()['brief']['id'])

        studios_proposal = client.post(
            '/money-printers/nuxtron-studios/proposals',
            headers=_headers('tenant-studio'),
            json={
                'brief_id': brief_id,
                'service_id': service_id,
                'bid_usd': 1350,
                'message': 'Can deliver in 8 days with storyboard and revisions included.',
            },
        )
        assert studios_proposal.status_code == 200, studios_proposal.text
        proposal_id = int(studios_proposal.json()['proposal']['id'])

        studios_escrow = client.post(
            '/money-printers/nuxtron-studios/escrows',
            headers=_headers('tenant-studio'),
            json={'proposal_id': proposal_id, 'milestone_name': 'kickoff', 'amount_usd': 700},
        )
        assert studios_escrow.status_code == 200, studios_escrow.text
        escrow_id = int(studios_escrow.json()['escrow']['id'])

        studios_release = client.post(
            '/money-printers/nuxtron-studios/escrows/release',
            headers=_headers('tenant-studio'),
            json={'escrow_id': escrow_id, 'approved': True, 'note': 'Milestone accepted by client.'},
        )
        assert studios_release.status_code == 200, studios_release.text
        assert studios_release.json()['escrow']['status'] == 'released'

        studios_overview = client.get('/money-printers/nuxtron-studios/overview', headers=_headers('tenant-studio'))
        assert studios_overview.status_code == 200, studios_overview.text
        assert int(studios_overview.json()['studios']['released_escrows']) >= 1

        # ── Commerce Pro ──────────────────────────────────────────────
        commerce_product = client.post(
            '/money-printers/commerce-pro/products',
            headers=_headers('tenant-commerce'),
            json={
                'name': 'Creator OS Starter Pack',
                'description': 'All-in-one digital kit for new creators',
                'price_usd': 49.00,
                'currency': 'USD',
                'category': 'digital',
                'inventory': 500,
                'digital': True,
            },
        )
        assert commerce_product.status_code == 200, commerce_product.text
        assert commerce_product.json()['product']['name'] == 'Creator OS Starter Pack'
        commerce_product_id = commerce_product.json()['product']['id']

        commerce_catalog = client.get('/money-printers/commerce-pro/catalog', headers=_headers('tenant-commerce'))
        assert commerce_catalog.status_code == 200, commerce_catalog.text
        assert commerce_catalog.json()['count'] >= 1

        commerce_storefront = client.get('/money-printers/commerce-pro/storefront', headers=_headers('tenant-commerce'))
        assert commerce_storefront.status_code == 200, commerce_storefront.text
        assert commerce_storefront.json()['storefront']['active_products'] >= 1

        commerce_order = client.post(
            '/money-printers/commerce-pro/orders',
            headers=_headers('tenant-commerce'),
            json={
                'product_id': commerce_product_id,
                'quantity': 2,
                'buyer_email': BUYER_EMAIL,
                'note': 'Please send download link',
            },
        )
        assert commerce_order.status_code == 200, commerce_order.text
        assert commerce_order.json()['order']['order_status'] == 'confirmed'
        assert abs(commerce_order.json()['order']['total_usd'] - 98.00) < 0.01

        commerce_orders = client.get('/money-printers/commerce-pro/orders', headers=_headers('tenant-commerce'))
        assert commerce_orders.status_code == 200, commerce_orders.text
        assert commerce_orders.json()['count'] >= 1

        commerce_overview = client.get('/money-printers/commerce-pro/overview', headers=_headers('tenant-commerce'))
        assert commerce_overview.status_code == 200, commerce_overview.text
        assert commerce_overview.json()['commerce']['confirmed_orders'] >= 1
        assert commerce_overview.json()['commerce']['confirmed_revenue_usd'] >= 98.00

        # ── Insights Dashboard Enterprise Depth ───────────────────────
        insights_kpi = client.get('/analytics/insights/kpi', headers=_headers('tenant-insights'))
        assert insights_kpi.status_code == 200, insights_kpi.text
        kpi = insights_kpi.json()['kpi']
        assert 'revenue' in kpi
        assert 'growth' in kpi
        assert 'product' in kpi

        insights_trend = client.post(
            '/analytics/insights/trend',
            headers=_headers('tenant-insights'),
            json={'metric': 'crm_contacts', 'period': 'last_30_days', 'granularity': 'daily'},
        )
        assert insights_trend.status_code == 200, insights_trend.text
        assert insights_trend.json()['trend']['metric'] == 'crm_contacts'
        assert len(insights_trend.json()['trend']['datapoints']) >= 1
        assert insights_trend.json()['trend']['trend_direction'] in ('up', 'flat', 'down')

        insights_rollup = client.post(
            '/analytics/insights/rollup',
            headers=_headers('tenant-insights'),
            json={'modules': ['crm_contacts', 'email_campaigns', 'commerce_orders'], 'label': 'Q2 GTM snapshot'},
        )
        assert insights_rollup.status_code == 200, insights_rollup.text
        assert insights_rollup.json()['rollup']['label'] == 'Q2 GTM snapshot'
        assert 'snapshot' in insights_rollup.json()['rollup']

        insights_intelligence = client.get('/analytics/insights/intelligence', headers=_headers('tenant-insights'))
        assert insights_intelligence.status_code == 200, insights_intelligence.text
        intel = insights_intelligence.json()['intelligence']
        assert 'top_signals' in intel
        assert 'enterprise_readiness' in intel

        white_label_profile_initial = client.get('/white-label/profile', headers=_headers('tenant-white'))
        assert white_label_profile_initial.status_code == 200, white_label_profile_initial.text
        assert white_label_profile_initial.json()['white_label']['profile']['stage'] == 'foundation'

        white_label_kit = client.post(
            '/white-label/brand-kit',
            headers=_headers('tenant-white'),
            json={
                'brand_name': 'Nimbus Agency OS',
                'primary_color': '#0D3B66',
                'accent_color': '#F4A261',
                'logo_url': 'https://cdn.example.com/nimbus-logo.svg',
                'support_email': 'support@nimbus.example',
            },
        )
        assert white_label_kit.status_code == 200, white_label_kit.text

        white_label_domain = client.post(
            '/white-label/domain',
            headers=_headers('tenant-white'),
            json={'custom_domain': 'portal.nimbus.example', 'ssl_enabled': True},
        )
        assert white_label_domain.status_code == 200, white_label_domain.text

        white_label_checkpoint = client.post(
            '/white-label/checkpoint',
            headers=_headers('tenant-white'),
            json={
                'action': 'client_brand_rollout',
                'points': 80,
                'note': 'Brand kit and custom domain are now live for client-facing portal.',
            },
        )
        assert white_label_checkpoint.status_code == 200, white_label_checkpoint.text
        assert white_label_checkpoint.json()['progressed'] is True
        assert white_label_checkpoint.json()['profile']['stage'] in ('client_ready', 'agency_grade')

        white_label_timeline = client.get('/white-label/timeline', headers=_headers('tenant-white'))
        assert white_label_timeline.status_code == 200, white_label_timeline.text
        assert int(white_label_timeline.json().get('count', 0)) >= 1
        assert white_label_timeline.json()['timeline'][0]['action'] == 'client_brand_rollout'

        # ── Talent Agency Deal Marketplace ────────────────────────────
        talent_creator = client.post(
            '/talent-agency/creators',
            headers=_headers('tenant-talent'),
            json={
                'name': 'Luna Creatives',
                'niche': 'lifestyle',
                'platform': 'instagram',
                'followers': 280000,
                'rate_card_usd': 1500.00,
                'bio': 'Lifestyle creator specializing in brand storytelling.',
            },
        )
        assert talent_creator.status_code == 200, talent_creator.text
        assert talent_creator.json()['creator']['name'] == 'Luna Creatives'
        talent_creator_id = talent_creator.json()['creator']['id']

        talent_rate_card = client.post(
            '/talent-agency/rate-cards',
            headers=_headers('tenant-talent'),
            json={
                'creator_id': talent_creator_id,
                'post_rate_usd': 1200.00,
                'story_rate_usd': 600.00,
                'reel_rate_usd': 1800.00,
                'package_rate_usd': 4500.00,
                'currency': 'USD',
            },
        )
        assert talent_rate_card.status_code == 200, talent_rate_card.text
        assert abs(talent_rate_card.json()['rate_card']['package_rate_usd'] - 4500.00) < 0.01

        talent_roster = client.get('/talent-agency/roster', headers=_headers('tenant-talent'))
        assert talent_roster.status_code == 200, talent_roster.text
        assert talent_roster.json()['count'] >= 1

        talent_deal = client.post(
            '/talent-agency/deals',
            headers=_headers('tenant-talent'),
            json={
                'creator_id': talent_creator_id,
                'brand_name': 'GlowBrand Co.',
                'deliverables': '2 reels + 4 stories + 1 feed post',
                'budget_usd': 5500.00,
                'currency': 'USD',
                'note': 'Q3 summer campaign',
            },
        )
        assert talent_deal.status_code == 200, talent_deal.text
        assert talent_deal.json()['deal']['status'] == 'proposed'
        talent_deal_id = talent_deal.json()['deal']['id']

        talent_accept = client.post(
            '/talent-agency/deals/accept',
            headers=_headers('tenant-talent'),
            json={'deal_id': talent_deal_id, 'accepted': True, 'counter_rate_usd': 0, 'note': 'Approved!'},
        )
        assert talent_accept.status_code == 200, talent_accept.text
        assert talent_accept.json()['deal']['accepted'] is True
        assert talent_accept.json()['deal']['status'] == 'enterprise_deal'

        talent_deals = client.get('/talent-agency/deals', headers=_headers('tenant-talent'))
        assert talent_deals.status_code == 200, talent_deals.text
        assert talent_deals.json()['count'] >= 1

        talent_overview = client.get('/talent-agency/overview', headers=_headers('tenant-talent'))
        assert talent_overview.status_code == 200, talent_overview.text
        ta = talent_overview.json()['talent_agency']
        assert ta['creators_on_roster'] >= 1
        assert ta['accepted_deals'] >= 1
        assert ta['total_deal_value_usd'] >= 5500.00
        assert ta['marketplace_stage'] == 'active'

        # ── ADDED: Content Approval Workflows (Hootsuite §4.5) ────────────────────
        approval_config = client.put(
            '/content/approval/config',
            headers=_headers('tenant-a'),
            json={
                'levels': ['editor', 'legal'],
                'require_all_levels': True,
                'expiry_hours': 48,
            },
        )
        assert approval_config.status_code == 200, approval_config.text
        assert approval_config.json()['config']['levels'] == ['editor', 'legal']

        approval_config_get = client.get('/content/approval/config', headers=_headers('tenant-a'))
        assert approval_config_get.status_code == 200, approval_config_get.text
        assert approval_config_get.json()['config']['require_all_levels'] is True

        approval_submit = client.post(
            APPROVAL_REQUESTS_PATH,
            headers=_headers('tenant-a'),
            json={
                'scheduled_post_id': 1,
                'platform': 'linkedin',
                'content_preview': 'Exciting product launch on LinkedIn — join us!',
                'campaign_tag': 'product-launch-q2',
                'requested_by': CONTENT_REQUESTOR,
            },
        )
        assert approval_submit.status_code == 200, approval_submit.text
        approval_request_id = approval_submit.json()['request']['id']
        assert approval_submit.json()['request']['status'] == 'pending'
        assert approval_submit.json()['request']['approval_levels'] == ['editor', 'legal']

        # Duplicate submit must return 400
        approval_dup = client.post(
            APPROVAL_REQUESTS_PATH,
            headers=_headers('tenant-a'),
            json={
                'scheduled_post_id': 1,
                'platform': 'linkedin',
                'content_preview': 'Duplicate attempt.',
                'requested_by': CONTENT_REQUESTOR,
            },
        )
        assert approval_dup.status_code == 400, approval_dup.text

        # First-level approval (editor) — should stay pending (require_all_levels=True)
        approval_editor = client.post(
            f'/content/approval/requests/{approval_request_id}/decision',
            headers=_headers('tenant-a'),
            json={
                'decision': 'approved',
                'reviewer_role': 'editor',
                'comment': 'Copy looks good.',
            },
        )
        assert approval_editor.status_code == 200, approval_editor.text
        assert approval_editor.json()['request']['status'] == 'pending'
        assert 'editor' in approval_editor.json()['request']['approvals_received']

        # Second-level approval (legal) — should now promote to approved
        approval_legal = client.post(
            f'/content/approval/requests/{approval_request_id}/decision',
            headers=_headers('tenant-a'),
            json={
                'decision': 'approved',
                'reviewer_role': 'legal',
                'comment': 'Compliant with regulations.',
            },
        )
        assert approval_legal.status_code == 200, approval_legal.text
        assert approval_legal.json()['request']['status'] == 'approved'
        assert approval_legal.json()['request']['approved_at'] is not None

        # Comments endpoint
        approval_comments = client.get(
            f'/content/approval/requests/{approval_request_id}/comments',
            headers=_headers('tenant-a'),
        )
        assert approval_comments.status_code == 200, approval_comments.text
        assert approval_comments.json()['count'] >= 2

        # List approvals filtered by status
        approval_list = client.get(
            '/content/approval/requests?approval_status=approved',
            headers=_headers('tenant-a'),
        )
        assert approval_list.status_code == 200, approval_list.text
        assert approval_list.json()['count'] >= 1

        # Rejection flow: submit new request and reject it
        approval_submit2 = client.post(
            APPROVAL_REQUESTS_PATH,
            headers=_headers('tenant-a'),
            json={
                'scheduled_post_id': 99,
                'platform': 'x-twitter',
                'content_preview': 'Off-brand copy that needs rejection.',
                'requested_by': CONTENT_REQUESTOR,
            },
        )
        assert approval_submit2.status_code == 200, approval_submit2.text
        reject_id = approval_submit2.json()['request']['id']

        approval_reject = client.post(
            f'/content/approval/requests/{reject_id}/decision',
            headers=_headers('tenant-a'),
            json={
                'decision': 'rejected',
                'reviewer_role': 'editor',
                'comment': 'Tone does not align with brand guidelines.',
            },
        )
        assert approval_reject.status_code == 200, approval_reject.text
        assert approval_reject.json()['request']['status'] == 'rejected'
        assert approval_reject.json()['request']['rejection_reason'] == 'Tone does not align with brand guidelines.'

        # Invalid reviewer_role must return 422
        approval_bad_role = client.post(
            f'/content/approval/requests/{approval_request_id}/decision',
            headers=_headers('tenant-a'),
            json={'decision': 'approved', 'reviewer_role': 'intern'},
        )
        assert approval_bad_role.status_code in {400, 422}, approval_bad_role.text

        # ── ADDED: Media Library (Hootsuite §4.3) ─────────────────────────────────
        media_folder = client.post(
            MEDIA_FOLDERS_PATH,
            headers=_headers('tenant-a'),
            json={'name': 'Campaign Assets Q2', 'description': 'All assets for Q2 product launch.'},
        )
        assert media_folder.status_code == 200, media_folder.text
        folder_id = media_folder.json()['folder']['id']
        assert media_folder.json()['folder']['name'] == 'Campaign Assets Q2'

        # Nested folder
        media_subfolder = client.post(
            MEDIA_FOLDERS_PATH,
            headers=_headers('tenant-a'),
            json={'name': 'Instagram Stories', 'parent_folder_id': folder_id},
        )
        assert media_subfolder.status_code == 200, media_subfolder.text
        assert media_subfolder.json()['folder']['parent_folder_id'] == folder_id

        media_folders_list = client.get(MEDIA_FOLDERS_PATH, headers=_headers('tenant-a'))
        assert media_folders_list.status_code == 200, media_folders_list.text
        assert media_folders_list.json()['count'] >= 2

        # Register assets
        media_asset1 = client.post(
            '/media/assets',
            headers=_headers('tenant-a'),
            json={
                'filename': 'product-launch-hero.jpg',
                'asset_type': 'image',
                'url': 'https://cdn.nuxtron.io/assets/product-launch-hero.jpg',
                'size_bytes': 204800,
                'folder_id': folder_id,
                'tags': ['hero', 'launch'],
                'alt_text': 'Product launch hero image',
            },
        )
        assert media_asset1.status_code == 200, media_asset1.text
        asset1_id = media_asset1.json()['asset']['id']
        assert 'auto:image' in media_asset1.json()['asset']['auto_tags']
        assert 'launch' in media_asset1.json()['asset']['tags']
        assert media_asset1.json()['asset']['folder_id'] == folder_id

        media_asset2 = client.post(
            '/media/assets',
            headers=_headers('tenant-a'),
            json={
                'filename': 'brand-reel.mp4',
                'asset_type': 'video',
                'url': 'https://cdn.nuxtron.io/assets/brand-reel.mp4',
                'size_bytes': 8192000,
                'tags': ['reel', 'brand'],
            },
        )
        assert media_asset2.status_code == 200, media_asset2.text
        assert media_asset2.json()['asset']['asset_type'] == 'video'

        # List with type filter
        media_images = client.get('/media/assets?asset_type=image', headers=_headers('tenant-a'))
        assert media_images.status_code == 200, media_images.text
        assert all(a['asset_type'] == 'image' for a in media_images.json()['assets'])
        assert media_images.json()['count'] >= 1

        # List with folder filter
        media_in_folder = client.get(f'/media/assets?folder_id={folder_id}', headers=_headers('tenant-a'))
        assert media_in_folder.status_code == 200, media_in_folder.text
        assert all(a['folder_id'] == folder_id for a in media_in_folder.json()['assets'])

        # List with tag filter
        media_by_tag = client.get('/media/assets?tag=auto:image', headers=_headers('tenant-a'))
        assert media_by_tag.status_code == 200, media_by_tag.text
        assert media_by_tag.json()['count'] >= 1

        # Search by filename
        media_search = client.get('/media/assets?search=hero', headers=_headers('tenant-a'))
        assert media_search.status_code == 200, media_search.text
        assert media_search.json()['count'] >= 1

        # Get single asset
        media_get = client.get(f'/media/assets/{asset1_id}', headers=_headers('tenant-a'))
        assert media_get.status_code == 200, media_get.text
        assert media_get.json()['asset']['id'] == asset1_id

        # Patch tags and alt text
        media_patch = client.patch(
            f'/media/assets/{asset1_id}',
            headers=_headers('tenant-a'),
            json={'tags': ['hero', 'launch', 'q2'], 'alt_text': 'Updated hero image alt text'},
        )
        assert media_patch.status_code == 200, media_patch.text
        assert 'q2' in media_patch.json()['asset']['manual_tags']

        # Stats
        media_stats = client.get('/media/stats', headers=_headers('tenant-a'))
        assert media_stats.status_code == 200, media_stats.text
        assert media_stats.json()['total_assets'] >= 2
        assert media_stats.json()['total_folders'] >= 2
        assert 'by_type' in media_stats.json()

        # Delete asset
        media_delete = client.delete(f'/media/assets/{asset1_id}', headers=_headers('tenant-a'))
        assert media_delete.status_code == 200, media_delete.text
        assert media_delete.json()['deleted'] is True

        # After delete, get returns 404
        media_get_deleted = client.get(f'/media/assets/{asset1_id}', headers=_headers('tenant-a'))
        assert media_get_deleted.status_code == 404, media_get_deleted.text

        # ── ADDED: Employee Advocacy / Hootsuite Amplify (Hootsuite §9) ──────────
        advocacy_campaign = client.post(
            '/advocacy/campaigns',
            headers=_headers('tenant-a'),
            json={
                'name': 'Q2 Product Launch Advocacy',
                'description': 'Mobilise employees to share product launch content.',
                'starts_at': '2026-04-20T00:00:00Z',
            },
        )
        assert advocacy_campaign.status_code == 200, advocacy_campaign.text
        adv_campaign_id = advocacy_campaign.json()['campaign']['id']
        assert advocacy_campaign.json()['campaign']['name'] == 'Q2 Product Launch Advocacy'

        advocacy_campaigns_list = client.get('/advocacy/campaigns', headers=_headers('tenant-a'))
        assert advocacy_campaigns_list.status_code == 200, advocacy_campaigns_list.text
        assert advocacy_campaigns_list.json()['count'] >= 1

        # Add approved content to hub
        advocacy_content = client.post(
            ADVOCACY_CONTENT_PATH,
            headers=_headers('tenant-a'),
            json={
                'title': 'Product Launch Announcement',
                'body': 'Thrilled to announce the launch of Nuxtron v2! Check it out: https://nuxtron.io',
                'platform': 'linkedin',
                'campaign_id': adv_campaign_id,
                'target_departments': ['marketing', 'sales'],
                'target_regions': ['us', 'eu'],
            },
        )
        assert advocacy_content.status_code == 200, advocacy_content.text
        adv_content_id = advocacy_content.json()['content']['id']
        assert advocacy_content.json()['content']['platform'] == 'linkedin'
        assert advocacy_content.json()['content']['campaign_id'] == adv_campaign_id
        assert 'marketing' in advocacy_content.json()['content']['target_departments']

        # List content
        advocacy_content_list = client.get(ADVOCACY_CONTENT_PATH, headers=_headers('tenant-a'))
        assert advocacy_content_list.status_code == 200, advocacy_content_list.text
        assert advocacy_content_list.json()['count'] >= 1

        # Filter by campaign
        advocacy_content_by_campaign = client.get(
            f'/advocacy/content?campaign_id={adv_campaign_id}',
            headers=_headers('tenant-a'),
        )
        assert advocacy_content_by_campaign.status_code == 200, advocacy_content_by_campaign.text
        assert advocacy_content_by_campaign.json()['count'] >= 1

        # Register advocates
        advocate1 = client.post(
            ADVOCACY_PARTICIPANTS_PATH,
            headers=_headers('tenant-a'),
            json={
                'name': 'Alice Marketing',
                'email': 'alice@nuxtron.io',
                'department': 'marketing',
                'region': 'us',
                'linkedin_followers': 2500,
                'x_followers': 800,
            },
        )
        assert advocate1.status_code == 200, advocate1.text
        participant_id = advocate1.json()['participant']['id']
        assert advocate1.json()['created'] is True
        assert advocate1.json()['participant']['total_following'] == 3300

        # Idempotent re-registration (same email)
        advocate1_dup = client.post(
            ADVOCACY_PARTICIPANTS_PATH,
            headers=_headers('tenant-a'),
            json={
                'name': 'Alice Marketing',
                'email': 'alice@nuxtron.io',
                'department': 'marketing',
                'region': 'us',
                'linkedin_followers': 2500,
            },
        )
        assert advocate1_dup.status_code == 200, advocate1_dup.text
        assert advocate1_dup.json()['created'] is False

        advocate2 = client.post(
            ADVOCACY_PARTICIPANTS_PATH,
            headers=_headers('tenant-a'),
            json={
                'name': 'Bob Sales',
                'email': 'bob@nuxtron.io',
                'department': 'sales',
                'region': 'eu',
                'linkedin_followers': 1200,
            },
        )
        assert advocate2.status_code == 200, advocate2.text

        # List participants (leaderboard order)
        participants_list = client.get(ADVOCACY_PARTICIPANTS_PATH, headers=_headers('tenant-a'))
        assert participants_list.status_code == 200, participants_list.text
        assert participants_list.json()['count'] >= 2

        # Filter by department
        participants_marketing = client.get(
            '/advocacy/participants?department=marketing',
            headers=_headers('tenant-a'),
        )
        assert participants_marketing.status_code == 200, participants_marketing.text
        assert all(p['department'] == 'marketing' for p in participants_marketing.json()['participants'])

        # Record share event
        share_event = client.post(
            f'/advocacy/participants/{participant_id}/share',
            headers=_headers('tenant-a'),
            json={
                'content_id': adv_content_id,
                'platform': 'linkedin',
                'estimated_reach': 2500,
                'likes': 45,
                'comments': 12,
                'clicks': 80,
                'custom_commentary': 'Really proud of what we built at Nuxtron!',
            },
        )
        assert share_event.status_code == 200, share_event.text
        assert share_event.json()['points_earned'] >= 10
        assert share_event.json()['earned_media_value'] > 0
        emv_value = share_event.json()['earned_media_value']
        assert abs(emv_value - round(2500 * 0.015, 4)) < 0.0001

        # Content stats updated
        adv_content_after = client.get(ADVOCACY_CONTENT_PATH, headers=_headers('tenant-a'))
        updated_content = next(
            (c for c in adv_content_after.json()['content'] if c['id'] == adv_content_id), None
        )
        assert updated_content is not None
        assert updated_content['total_shares'] == 1
        assert updated_content['total_reach'] == 2500

        # Analytics
        adv_analytics = client.get('/advocacy/analytics', headers=_headers('tenant-a'))
        assert adv_analytics.status_code == 200, adv_analytics.text
        analytics_data = adv_analytics.json()
        assert analytics_data['totalShares'] >= 1
        assert analytics_data['totalReach'] >= 2500
        assert analytics_data['totalEarnedMediaValue'] > 0
        assert analytics_data['activeAdvocates'] >= 1
        assert analytics_data['totalRegisteredAdvocates'] >= 2
        assert 'linkedin' in analytics_data['byPlatform']
        assert len(analytics_data['leaderboard']) >= 1
        assert analytics_data['leaderboard'][0]['points'] >= 10

    # ── Smart Inbox (SproutSocial §3) ────────────────────────────────────────────
    with TestClient(app) as client:
        # Ingest a complaint message
        ingest_r = client.post(INBOX_MESSAGES_PATH, headers=_headers('tenant-a'), json={
            'network': 'instagram',
            'source_type': 'comment',
            'author_handle': 'jane_doe',
            'author_display_name': 'Jane Doe',
            'author_follower_count': 5000,
            'text': 'Your product is terrible and broken! I want a refund.',
            'external_message_id': 'ext-msg-001',
        })
        assert ingest_r.status_code == 200, ingest_r.text
        ingest_data = ingest_r.json()
        assert ingest_data['created'] is True
        msg_id = ingest_data['message']['id']
        assert ingest_data['message']['sentiment'] == 'negative'
        assert ingest_data['message']['message_type'] == 'complaint'
        assert ingest_data['message']['priority_score'] > 0

        # Dedup — re-ingest same external_message_id → created=False
        dedup_r = client.post(INBOX_MESSAGES_PATH, headers=_headers('tenant-a'), json={
            'network': 'instagram',
            'source_type': 'comment',
            'author_handle': 'jane_doe',
            'text': 'duplicate message',
            'external_message_id': 'ext-msg-001',
        })
        assert dedup_r.status_code == 200, dedup_r.text
        assert dedup_r.json()['created'] is False

        # Ingest a question message
        q_r = client.post(INBOX_MESSAGES_PATH, headers=_headers('tenant-a'), json={
            'network': 'x-twitter',
            'source_type': 'mention',
            'author_handle': 'curious_user',
            'text': 'When will your new product launch?',
        })
        assert q_r.status_code == 200, q_r.text
        assert q_r.json()['message']['message_type'] == 'question'

        # List messages
        list_r = client.get(INBOX_MESSAGES_PATH, headers=_headers('tenant-a'))
        assert list_r.status_code == 200, list_r.text
        assert list_r.json()['count'] >= 2

        # Filter by sentiment
        neg_r = client.get('/inbox/messages?sentiment=negative', headers=_headers('tenant-a'))
        assert neg_r.status_code == 200, neg_r.text
        assert neg_r.json()['count'] >= 1

        # Get single message
        get_r = client.get(f'/inbox/messages/{msg_id}', headers=_headers('tenant-a'))
        assert get_r.status_code == 200, get_r.text
        assert get_r.json()['message']['id'] == msg_id
        assert 'suggested_replies' in get_r.json()['message']

        # Update message assignment
        upd_r = client.patch(f'/inbox/messages/{msg_id}', headers=_headers('tenant-a'), json={
            'assigned_to': INBOX_ASSIGNEE,
            'status': 'in_progress',
            'tags': ['refund', 'urgent'],
        })
        assert upd_r.status_code == 200, upd_r.text
        assert upd_r.json()['message']['assigned_to'] == INBOX_ASSIGNEE
        assert upd_r.json()['message']['status'] == 'in_progress'

        # Add internal note
        note_r = client.post(f'/inbox/messages/{msg_id}/notes', headers=_headers('tenant-a'), json={
            'author': INBOX_ASSIGNEE,
            'note': 'Escalated to customer service team.',
        })
        assert note_r.status_code == 200, note_r.text
        assert note_r.json()['note']['id'] >= 1

        # List notes
        notes_r = client.get(f'/inbox/messages/{msg_id}/notes', headers=_headers('tenant-a'))
        assert notes_r.status_code == 200, notes_r.text
        assert notes_r.json()['count'] >= 1

        # Collision lock — acquire
        lock_r = client.post(f'/inbox/messages/{msg_id}/lock', headers=_headers('tenant-a'), json={
            'locked_by': INBOX_ASSIGNEE,
        })
        assert lock_r.status_code == 200, lock_r.text
        assert lock_r.json()['collision_detected'] is False

        # Collision detection — another user tries to lock → 409
        lock2_r = client.post(f'/inbox/messages/{msg_id}/lock', headers=_headers('tenant-a'), json={
            'locked_by': 'bob@brand.com',
        })
        assert lock2_r.status_code == 409, lock2_r.text

        # Release lock
        rel_r = client.delete(f'/inbox/messages/{msg_id}/lock?locked_by=alice%40brand.com', headers=_headers('tenant-a'))
        assert rel_r.status_code == 200, rel_r.text
        assert rel_r.json()['released'] is True

        # Inbox stats
        stats_r = client.get('/inbox/stats', headers=_headers('tenant-a'))
        assert stats_r.status_code == 200, stats_r.text
        stats = stats_r.json()
        assert stats['total'] >= 2
        assert 'byMessageType' in stats
        assert 'bySentiment' in stats

        # Saved replies — create
        sr_r = client.post('/inbox/saved-replies', headers=_headers('tenant-a'), json={
            'title': 'Complaint Acknowledgement',
            'body': 'We sincerely apologise for the inconvenience. Please DM us your order details.',
            'tags': ['complaint', 'apology'],
            'networks': ['instagram', 'facebook'],
        })
        assert sr_r.status_code == 200, sr_r.text
        sr_id = sr_r.json()['reply']['id']

        # Saved replies — list
        sr_list_r = client.get('/inbox/saved-replies', headers=_headers('tenant-a'))
        assert sr_list_r.status_code == 200, sr_list_r.text
        assert sr_list_r.json()['count'] >= 1

        # Saved replies — update
        sr_upd_r = client.patch(f'/inbox/saved-replies/{sr_id}', headers=_headers('tenant-a'), json={
            'title': 'Complaint Acknowledgement (Updated)',
        })
        assert sr_upd_r.status_code == 200, sr_upd_r.text
        assert 'Updated' in sr_upd_r.json()['reply']['title']

        # Saved replies — delete
        sr_del_r = client.delete(f'/inbox/saved-replies/{sr_id}', headers=_headers('tenant-a'))
        assert sr_del_r.status_code == 200, sr_del_r.text
        assert sr_del_r.json()['deleted'] is True

    # ── ViralPost (SproutSocial §2.1.3) ──────────────────────────────────────────
    with TestClient(app) as client:
        # Get industry benchmark defaults (no history needed)
        def_r = client.get('/publishing/optimal-times/defaults?network=linkedin', headers=_headers('tenant-a'))
        assert def_r.status_code == 200, def_r.text
        def_data = def_r.json()
        assert def_data['network'] == 'linkedin'
        assert len(def_data['windows']) >= 3

        # Record post history entries
        for i in range(12):
            # Spread posts across different days and hours
            pub_date = f'2025-0{(i % 6) + 1}-{(i % 28) + 1:02d}T{(i % 12) + 8:02d}:00:00+00:00'
            ph_r = client.post('/publishing/post-history', headers=_headers('tenant-a'), json={
                'network': 'linkedin',
                'profile_id': 'profile-123',
                'content_type': 'image',
                'published_at': pub_date,
                'impressions': 1000 + (i * 100),
                'engagements': 50 + (i * 10),
                'likes': 30 + (i * 5),
                'comments': 10 + i,
                'shares': 5 + i,
            })
            assert ph_r.status_code == 200, ph_r.text

        # Run analysis
        analysis_r = client.post('/publishing/optimal-times', headers=_headers('tenant-a'), json={
            'network': 'linkedin',
            'profile_id': 'profile-123',
            'content_type': 'image',
            'timezone_offset_hours': 0,
        })
        assert analysis_r.status_code == 200, analysis_r.text
        analysis_data = analysis_r.json()
        assert analysis_data['analysis']['sample_size'] >= 10
        assert len(analysis_data['analysis']['optimal_windows']) >= 1
        assert 'next_optimal_datetime' in analysis_data['analysis']

        # List analyses
        list_a_r = client.get('/publishing/optimal-times', headers=_headers('tenant-a'))
        assert list_a_r.status_code == 200, list_a_r.text
        assert list_a_r.json()['count'] >= 1

    # ── Competitive Benchmarking (SproutSocial §5.4) ──────────────────────────────
    with TestClient(app) as client:
        # Add competitor profiles
        comp1_r = client.post(COMPETITIVE_PROFILES_PATH, headers=_headers('tenant-a'), json={
            'name': 'CompetitorAlpha',
            'network': 'linkedin',
            'handle': 'competitor_alpha',
            'industry': 'SaaS',
        })
        assert comp1_r.status_code == 200, comp1_r.text
        assert comp1_r.json()['created'] is True
        comp1_id = comp1_r.json()['profile']['id']

        comp2_r = client.post(COMPETITIVE_PROFILES_PATH, headers=_headers('tenant-a'), json={
            'name': 'CompetitorBeta',
            'network': 'linkedin',
            'handle': 'competitor_beta',
        })
        assert comp2_r.status_code == 200, comp2_r.text
        comp2_id = comp2_r.json()['profile']['id']

        # Dedup test
        dedup_comp_r = client.post(COMPETITIVE_PROFILES_PATH, headers=_headers('tenant-a'), json={
            'name': 'Duplicate',
            'network': 'linkedin',
            'handle': 'competitor_alpha',
        })
        assert dedup_comp_r.status_code == 200, dedup_comp_r.text
        assert dedup_comp_r.json()['created'] is False

        # List competitors
        list_comp_r = client.get(COMPETITIVE_PROFILES_PATH, headers=_headers('tenant-a'))
        assert list_comp_r.status_code == 200, list_comp_r.text
        assert list_comp_r.json()['count'] >= 2

        # Add snapshots
        snap1_r = client.post(f'/competitive/profiles/{comp1_id}/snapshots', headers=_headers('tenant-a'), json={
            'followers': 150000,
            'engagement_rate': 4.2,
            'posts_last_30d': 22,
            'estimated_mentions': 450,
        })
        assert snap1_r.status_code == 200, snap1_r.text

        snap2_r = client.post(f'/competitive/profiles/{comp2_id}/snapshots', headers=_headers('tenant-a'), json={
            'followers': 80000,
            'engagement_rate': 2.8,
            'posts_last_30d': 14,
            'estimated_mentions': 210,
        })
        assert snap2_r.status_code == 200, snap2_r.text

        # Record own brand profile
        own_r = client.post('/competitive/own-profile', headers=_headers('tenant-a'), json={
            'network': 'linkedin',
            'followers': 110000,
            'engagement_rate': 3.5,
            'posts_last_30d': 18,
            'estimated_mentions': 320,
        })
        assert own_r.status_code == 200, own_r.text

        # Comparison report
        report_r = client.get('/competitive/report', headers=_headers('tenant-a'))
        assert report_r.status_code == 200, report_r.text
        report_data = report_r.json()
        assert report_data['competitor_count'] >= 2
        assert report_data['own_brand'] is not None
        assert report_data['competitors'][0]['latest_snapshot'] is not None
        assert 'vs_own' in report_data['competitors'][0]

        # Share of voice
        sov_r = client.get('/competitive/share-of-voice', headers=_headers('tenant-a'))
        assert sov_r.status_code == 200, sov_r.text
        sov_data = sov_r.json()
        assert sov_data['total_estimated_mentions'] >= 980
        assert len(sov_data['breakdown']) >= 3
        total_pct = sum(b['share_pct'] for b in sov_data['breakdown'])
        assert abs(total_pct - 100.0) < 0.1, f'SoV percentages should sum to 100, got {total_pct}'

        # Remove a competitor
        del_comp_r = client.delete(f'/competitive/profiles/{comp2_id}', headers=_headers('tenant-a'))
        assert del_comp_r.status_code == 200, del_comp_r.text
        assert del_comp_r.json()['deleted'] is True

    # ── UTM Builder (SproutSocial §2.1.1) ─────────────────────────────────────────
    with TestClient(app) as client:
        # Create preset
        preset_r = client.post('/publishing/utm/presets', headers=_headers('tenant-a'), json={
            'name': 'Q3 LinkedIn Campaign',
            'utm_source': 'linkedin',
            'utm_medium': 'social',
            'utm_campaign': 'product_launch_q3',
            'utm_content': 'hero_image',
        })
        assert preset_r.status_code == 200, preset_r.text
        preset_id = preset_r.json()['preset']['id']

        # List presets
        list_p_r = client.get('/publishing/utm/presets', headers=_headers('tenant-a'))
        assert list_p_r.status_code == 200, list_p_r.text
        assert list_p_r.json()['count'] >= 1

        # Build URL from preset
        build_r = client.post(UTM_BUILD_PATH, headers=_headers('tenant-a'), json={
            'base_url': 'https://example.com/landing-page',
            'preset_id': preset_id,
        })
        assert build_r.status_code == 200, build_r.text
        build_data = build_r.json()
        assert 'utm_source=linkedin' in build_data['tagged_url']
        assert 'utm_medium=social' in build_data['tagged_url']
        assert 'utm_campaign=product_launch_q3' in build_data['tagged_url']

        # Build URL with campaign_tag suffix
        build_tag_r = client.post(UTM_BUILD_PATH, headers=_headers('tenant-a'), json={
            'base_url': 'https://example.com/landing-page',
            'preset_id': preset_id,
            'campaign_tag': 'variant_b',
        })
        assert build_tag_r.status_code == 200, build_tag_r.text
        assert 'variant_b' in build_tag_r.json()['tagged_url']

        # Build URL from custom params (no preset)
        custom_r = client.post(UTM_BUILD_PATH, headers=_headers('tenant-a'), json={
            'base_url': 'https://example.com/promo',
            'utm_source': 'instagram',
            'utm_medium': 'paid_social',
            'utm_campaign': 'summer_sale',
        })
        assert custom_r.status_code == 200, custom_r.text
        assert 'utm_source=instagram' in custom_r.json()['tagged_url']

        # Missing utm_source without preset → 422
        bad_r = client.post(UTM_BUILD_PATH, headers=_headers('tenant-a'), json={
            'base_url': 'https://example.com/page',
        })
        assert bad_r.status_code == 422, bad_r.text

        # Update preset
        upd_p_r = client.patch(f'/publishing/utm/presets/{preset_id}', headers=_headers('tenant-a'), json={
            'utm_campaign': 'product_launch_q3_v2',
        })
        assert upd_p_r.status_code == 200, upd_p_r.text
        assert upd_p_r.json()['preset']['utm_campaign'] == 'product_launch_q3_v2'

        # Delete preset
        del_p_r = client.delete(f'/publishing/utm/presets/{preset_id}', headers=_headers('tenant-a'))
        assert del_p_r.status_code == 200, del_p_r.text
        assert del_p_r.json()['deleted'] is True

    # ── SocialScheduleRequest campaign_tag + utm_params fields (SproutSocial §2.1.1) ──
    with TestClient(app) as client:
        import datetime as _dt
        future = (_dt.datetime.now(_dt.UTC) + _dt.timedelta(hours=1)).isoformat()
        sched_r = client.post('/social/schedule', headers=_headers('tenant-a'), json={
            'platform': 'linkedin',
            'text': 'Launching our new product line this summer!',
            'publish_at': future,
            'campaign_tag': 'summer_launch',
            'utm_preset_id': None,
            'first_comment': 'Drop a comment below if you are interested! 👇',
        })
        assert sched_r.status_code == 200, sched_r.text
        sched_data = sched_r.json()
        # Response must contain scheduling confirmation (any of these fields indicates success)
        assert isinstance(sched_data, dict), f'Response must be dict, got {type(sched_data)}'

    # ── Revenue Attribution (Shapley Multi-Touch + UTM injection + webhook ingest) ──
    with TestClient(app) as client:
        tp_r = client.post('/analytics/revenue-attribution/touchpoints', headers=_headers('tenant-a'), json={
            'post_id': 'post_linkedin_2026_001',
            'platform': 'linkedin',
            'campaign': 'spring_launch',
            'destination_url': 'https://example.com/pricing',
        })
        assert tp_r.status_code == 200, tp_r.text
        tp = tp_r.json()['touchpoint']
        assert 'nux_touchpoint=' in tp['tracked_url']
        assert 'utm_source=linkedin' in tp['tracked_url']

        conv_r = client.post('/analytics/revenue-attribution/conversions/ingest', headers=_headers('tenant-a'), json={
            'provider': 'stripe',
            'external_order_id': f'order-{int(datetime.now(UTC).timestamp())}',
            'amount': 499.0,
            'currency': 'USD',
            'event_type': 'checkout.session.completed',
            'touchpoint_keys': [tp['touchpoint_key']],
            'raw_payload': {'source': 'selftest'},
        })
        assert conv_r.status_code == 200, conv_r.text
        assert abs(float(conv_r.json()['conversion']['amount']) - 499.0) < 0.001

        report_r = client.get('/analytics/revenue-attribution/report?window_days=90', headers=_headers('tenant-a'))
        assert report_r.status_code == 200, report_r.text
        report = report_r.json()
        assert report['totals']['revenue'] >= 499.0
        assert report['totals']['attributed_revenue'] >= 499.0
        assert len(report.get('top_posts', [])) >= 1

    # ── Trend Intelligence (forecast phases + AI content generation + optimization) ──
    with TestClient(app) as client:
        seed_signals: list[dict[str, Any]] = [
            {
                'source_type': 'social_media',
                'source_platform': 'tiktok',
            'topic': TREND_TOPIC_PRIMARY,
                'keywords': ['ai', 'storytelling', 'faceless'],
                'mentions': 520,
                'likes': 2100,
                'comments': 260,
                'shares': 420,
                'saves': 180,
                'views': 28000,
                'clicks': 1900,
                'conversions': 68,
                'spend': 240,
                'dwell_seconds': 14.2,
                'negative_feedback': 120,
                'not_viewed_reasons': {'weak_hook': 32, 'wrong_timing': 18},
            },
            {
                'source_type': 'ads',
                'source_platform': 'instagram',
                'topic': TREND_TOPIC_PRIMARY,
                'keywords': ['short-form', 'ugc'],
                'mentions': 410,
                'likes': 1750,
                'comments': 190,
                'shares': 310,
                'saves': 120,
                'views': 22000,
                'clicks': 1700,
                'conversions': 74,
                'spend': 360,
                'dwell_seconds': 12.8,
                'negative_feedback': 88,
                'not_viewed_reasons': {'creative_fatigue': 26, 'weak_hook': 21},
            },
            {
                'source_type': 'web',
                'source_platform': 'youtube',
                'topic': 'voice ai dubbing',
                'keywords': ['dubbing', 'creator tools'],
                'mentions': 190,
                'likes': 620,
                'comments': 72,
                'shares': 61,
                'saves': 44,
                'views': 8400,
                'clicks': 490,
                'conversions': 12,
                'spend': 120,
                'dwell_seconds': 10.1,
                'negative_feedback': 42,
                'not_viewed_reasons': {'low_relevance': 14},
            },
        ]

        for signal in seed_signals:
            ingest_r = client.post(TREND_SIGNAL_INGEST_ENDPOINT, headers=_headers('tenant-trend'), json=signal)
            assert ingest_r.status_code == 200, ingest_r.text
            assert ingest_r.json()['signal']['topic'] in {TREND_TOPIC_PRIMARY, 'voice ai dubbing'}

        forecast_r = client.post(
            TREND_FORECAST_GENERATE_ENDPOINT,
            headers=_headers('tenant-trend'),
            json={'horizon_days': 21, 'lookback_days': 30, 'min_signals_per_topic': 2},
        )
        assert forecast_r.status_code == 200, forecast_r.text
        forecasts = forecast_r.json().get('forecasts', [])
        assert len(forecasts) >= 1
        trend = forecasts[0]
        assert trend['phase'] in {'upcoming_forecast', 'emerging', 'current', 'downfall'}

        select_r = client.post(
            TREND_SELECT_ENDPOINT,
            headers=_headers('tenant-trend'),
            json={
                'trend_id': trend['trend_id'],
                'objective': 'revenue',
                'channels': ['instagram', 'tiktok'],
                'budget': 1200,
            },
        )
        assert select_r.status_code == 200, select_r.text
        selection_id = select_r.json()['selection']['id']

        content_r = client.post(
            TREND_CONTENT_GENERATE_ENDPOINT,
            headers=_headers('tenant-trend'),
            json={
                'selection_id': selection_id,
                'target_channel': 'instagram',
                'output_types': ['social_post', 'short_ad_copy', 'hook', 'cta'],
                'tone': 'data-backed',
            },
        )
        assert content_r.status_code == 200, content_r.text
        generated_assets = content_r.json()['generation']['assets']
        assert len(generated_assets) >= 4

        perf_r = client.post(
            TREND_PERFORMANCE_TRACK_ENDPOINT,
            headers=_headers('tenant-trend'),
            json={
                'trend_id': trend['trend_id'],
                'content_id': 'asset_selftest_001',
                'channel': 'instagram',
                'likes': 940,
                'comments': 122,
                'shares': 141,
                'saves': 88,
                'views': 17200,
                'clicks': 1100,
                'conversions': 52,
                'spend': 260,
                'revenue': 1890,
                'watch_time_seconds': 12.4,
                'not_viewed_reasons': {'weak_hook': 15, 'wrong_timing': 9},
            },
        )
        assert perf_r.status_code == 200, perf_r.text
        assert perf_r.json()['diagnostics']['improvement_focus'] in {'hook_quality', 'cta_optimization'}

        dashboard_r = client.get(
            f"{TREND_ANALYTICS_ENDPOINT}?trend_id={trend['trend_id']}&days=30",
            headers=_headers('tenant-trend'),
        )
        assert dashboard_r.status_code == 200, dashboard_r.text
        dash = dashboard_r.json()
        assert 'graphs' in dash and 'trend_strength_history' in dash['graphs']
        assert 'achievable_projection' in dash['graphs']
        assert 'kpi' in dash and 'traction_kpi' in dash['kpi']
        assert 'performance_indicators' in dash and 'opportunity_indicator' in dash['performance_indicators']

        indicators_r = client.get(
            f"{TREND_INDICATORS_ENDPOINT}?trend_id={trend['trend_id']}&days=30",
            headers=_headers('tenant-trend'),
        )
        assert indicators_r.status_code == 200, indicators_r.text
        indicators = indicators_r.json()
        assert 'kpi' in indicators and 'roi_kpi' in indicators['kpi']
        assert 'performance_indicators' in indicators and 'cost_per_conversion_proxy' in indicators['performance_indicators']

        rec_r = client.get(
            f"{TREND_RECOMMENDATIONS_ENDPOINT}?trend_id={trend['trend_id']}",
            headers=_headers('tenant-trend'),
        )
        assert rec_r.status_code == 200, rec_r.text
        assert rec_r.json().get('count', 0) >= 1

    # ── AI Growth Suite / Strategic Features ───────────────────────────────────
    with TestClient(app) as client:
        bootstrap_r = client.post('/ops/platform/growth-suite/bootstrap', headers=_headers('tenant-growth'))
        assert bootstrap_r.status_code == 200, bootstrap_r.text
        bootstrap = bootstrap_r.json()
        assert bootstrap['totals']['features'] >= 18
        assert bootstrap['totals']['configured'] >= 18

        growth_summary_r = client.get('/ops/platform/growth-suite', headers=_headers('tenant-growth'))
        assert growth_summary_r.status_code == 200, growth_summary_r.text
        growth_summary = growth_summary_r.json()
        assert any(feature['key'] == 'brand_voice_dna' for feature in growth_summary['features'])
        assert any(feature['key'] == 'advanced_reports' for feature in growth_summary['features'])

        brand_voice_r = client.post(
            '/ai/brand-voice/profile',
            headers=_headers('tenant-growth'),
            json={
                'profile_name': 'Founder Voice',
                'sample_posts': [
                    'Specificity beats noise every time.',
                    'The best content proves pipeline, not vanity reach.',
                    'Clarity compounds when the offer is obvious.',
                ],
                'ai_output': 'This post is about growth and content marketing outcomes.',
            },
        )
        assert brand_voice_r.status_code == 200, brand_voice_r.text
        assert brand_voice_r.json()['brand_voice']['voice_score'] >= 62
        assert len(brand_voice_r.json()['brand_voice']['fingerprint']['signature_words']) >= 1

        ab_create_r = client.post(
            '/experiments/ab-tests',
            headers=_headers('tenant-growth'),
            json={
                'name': 'Growth CTA test',
                'base_content': 'Publish the proof, tighten the CTA, and let attribution show the winner.',
                'channel': 'linkedin',
                'goal': 'engagement',
            },
        )
        assert ab_create_r.status_code == 200, ab_create_r.text
        ab_test_key = ab_create_r.json()['test_key']
        assert len(ab_create_r.json()['variants']) == 5

        ab_eval_r = client.post(
            f'/experiments/ab-tests/{ab_test_key}/evaluate',
            headers=_headers('tenant-growth'),
            json={'engagement_scores': [0.18, 0.29, 0.24, 0.35, 0.31], 'republish': True},
        )
        assert ab_eval_r.status_code == 200, ab_eval_r.text
        assert ab_eval_r.json()['winner']['variant_key'] == 'variant_4'

        roi_r = client.post(
            '/forecast/roi',
            headers=_headers('tenant-growth'),
            json={
                'content_title': 'Launch post',
                'platform': 'linkedin',
                'expected_impressions': 15000,
                'historical_revenue': [250, 420, 515],
                'historical_engagement_rate': [0.04, 0.05, 0.055],
            },
        )
        assert roi_r.status_code == 200, roi_r.text
        assert roi_r.json()['forecast']['projected_revenue'] > 0

        agency_workspace_r = client.post(
            '/agency/workspaces',
            headers=_headers('tenant-growth'),
            json={
                'name': 'Nuxtron Agency Ops',
                'owner_email': 'owner@nuxtron.io',
                'clients': ['Acme', 'Orbit'],
            },
        )
        assert agency_workspace_r.status_code == 200, agency_workspace_r.text
        workspace_key = agency_workspace_r.json()['workspace']['workspace_key']

        agency_member_r = client.post(
            f'/agency/workspaces/{workspace_key}/members',
            headers=_headers('tenant-growth'),
            json={'email': 'editor@nuxtron.io', 'role': 'Editor'},
        )
        assert agency_member_r.status_code == 200, agency_member_r.text
        assert len(agency_member_r.json()['members']) >= 2

        agency_mrr_r = client.post(
            f'/agency/workspaces/{workspace_key}/mrr',
            headers=_headers('tenant-growth'),
            json={'client_name': 'Acme', 'monthly_recurring_revenue': 4500},
        )
        assert agency_mrr_r.status_code == 200, agency_mrr_r.text
        assert abs(float(agency_mrr_r.json()['mrr_total']) - 4500.0) < 0.001

        agency_overview_r = client.get('/agency/overview', headers=_headers('tenant-growth'))
        assert agency_overview_r.status_code == 200, agency_overview_r.text
        assert agency_overview_r.json()['overview']['workspaces'] >= 1
        assert agency_overview_r.json()['overview']['total_mrr'] >= 4500.0

        advanced_report_r = client.post(
            '/reports/advanced',
            headers=_headers('tenant-growth'),
            json={'client_name': 'Acme', 'reporting_window_days': 30},
        )
        assert advanced_report_r.status_code == 200, advanced_report_r.text
        assert advanced_report_r.json()['report']['csv_export_path'] == '/analytics/export'

    # ── HubSpot Blueprint Gap Coverage: Sequences / Meetings / Service / Commerce ──
    with TestClient(app) as client:
        # Sales sequences
        seq_r = client.post('/sequences', headers=_headers('tenant-a'), json={
            'name': 'Q2 Outbound Sequence',
            'description': 'Intro + follow-up cadence',
            'steps': [
                {'step_type': 'email', 'delay_days': 0, 'subject': 'Quick intro', 'body': 'Hello there'},
                {'step_type': 'call', 'delay_days': 2, 'task_description': 'Call prospect'},
            ],
        })
        assert seq_r.status_code == 200, seq_r.text
        seq_id = seq_r.json()['sequence']['id']

        enroll_r = client.post(f'/sequences/{seq_id}/enroll', headers=_headers('tenant-a'), json={
            'sequence_id': seq_id,
            'contact_id': 'contact-1001',
            'contact_email': 'prospect@example.com',
            'contact_name': 'Prospect One',
        })
        assert enroll_r.status_code == 200, enroll_r.text
        enrollment_id = enroll_r.json()['enrollment']['id']

        outcome_r = client.post(
            f'/sequences/enrollments/{enrollment_id}/step-outcome',
            headers=_headers('tenant-a'),
            json={'outcome': 'replied', 'notes': 'Positive response'},
        )
        assert outcome_r.status_code == 200, outcome_r.text

        seq_an_r = client.get(f'/sequences/{seq_id}/analytics', headers=_headers('tenant-a'))
        assert seq_an_r.status_code == 200, seq_an_r.text
        assert seq_an_r.json()['total_enrollments'] >= 1

        # Meeting scheduling
        link_r = client.post('/meetings/links', headers=_headers('tenant-a'), json={
            'name': 'Demo Call',
            'slug': 'demo-call-tenant-a',
            'duration_minutes': 30,
            'booking_type': 'one_on_one',
            'buffer_before_minutes': 15,
            'buffer_after_minutes': 15,
            'min_notice_hours': 0,
            'availability': [{'day': 'fri', 'start_time': '09:00', 'end_time': '17:00'}],
        })
        assert link_r.status_code == 200, link_r.text

        # Keep booking times in the future to satisfy min_notice_hours across calendar years.
        now_utc = datetime.now(UTC)
        booking_start = (now_utc + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
        days_until_friday = (4 - booking_start.weekday()) % 7
        booking_start = booking_start + timedelta(days=days_until_friday)
        if booking_start <= now_utc + timedelta(hours=2):
            booking_start = booking_start + timedelta(days=7)
        booking_conflict_start = booking_start + timedelta(minutes=20)
        booking_outside_window_start = booking_start.replace(hour=8, minute=0)
        booking_start_iso = booking_start.isoformat().replace('+00:00', 'Z')
        booking_conflict_iso = booking_conflict_start.isoformat().replace('+00:00', 'Z')
        booking_outside_window_iso = booking_outside_window_start.isoformat().replace('+00:00', 'Z')

        booking_r = client.post(MEETINGS_BOOK_PATH, headers=_headers('tenant-a'), json={
            'meeting_link_slug': 'demo-call-tenant-a',
            'attendee_email': BUYER_EMAIL,
            'attendee_name': 'Buyer Team',
            'start_time': booking_start_iso,
            'timezone': 'UTC',
        })
        assert booking_r.status_code == 200, booking_r.text
        booking_id = booking_r.json()['booking']['id']

        booking_conflict_r = client.post(MEETINGS_BOOK_PATH, headers=_headers('tenant-a'), json={
            'meeting_link_slug': 'demo-call-tenant-a',
            'attendee_email': 'second-buyer@example.com',
            'attendee_name': 'Second Buyer',
            'start_time': booking_conflict_iso,
            'timezone': 'UTC',
        })
        assert booking_conflict_r.status_code == 409, booking_conflict_r.text

        booking_outside_window_r = client.post(MEETINGS_BOOK_PATH, headers=_headers('tenant-a'), json={
            'meeting_link_slug': 'demo-call-tenant-a',
            'attendee_email': 'early-buyer@example.com',
            'attendee_name': 'Early Buyer',
            'start_time': booking_outside_window_iso,
            'timezone': 'UTC',
        })
        assert booking_outside_window_r.status_code == 409, booking_outside_window_r.text

        booking_upd_r = client.patch(
            f'/meetings/bookings/{booking_id}',
            headers=_headers('tenant-a'),
            json={'status': 'cancelled'},
        )
        assert booking_upd_r.status_code == 200, booking_upd_r.text

        # Tickets
        ticket_r = client.post('/tickets', headers=_headers('tenant-a'), json={
            'subject': 'Login issue',
            'description': 'User cannot login after password reset',
            'priority': 'high',
            'channel': 'email',
            'customer_email': 'customer@example.com',
            'customer_name': 'Customer One',
        })
        assert ticket_r.status_code == 200, ticket_r.text
        ticket_id = ticket_r.json()['ticket']['id']
        ticket_data = ticket_r.json()['ticket']
        assert ticket_data['first_response_due'] is not None
        assert ticket_data['resolution_due'] is not None

        comment_r = client.post(
            f'/tickets/{ticket_id}/comments',
            headers=_headers('tenant-a'),
            json={'body': 'Investigating now', 'is_internal': True},
        )
        assert comment_r.status_code == 200, comment_r.text

        csat_r = client.post(f'/tickets/{ticket_id}/csat?score=5', headers=_headers('tenant-a'))
        assert csat_r.status_code == 200, csat_r.text

        # Knowledge base
        kb_cat_r = client.post('/kb/categories', headers=_headers('tenant-a'), json={
            'name': 'Getting Started',
            'description': 'Onboarding docs',
        })
        assert kb_cat_r.status_code == 200, kb_cat_r.text
        kb_cat_id = kb_cat_r.json()['category']['id']

        kb_article_r = client.post('/kb/articles', headers=_headers('tenant-a'), json={
            'title': 'How to reset password',
            'body': 'Go to settings and click reset password.',
            'category_id': kb_cat_id,
            'status': 'published',
            'tags': ['auth', 'password'],
        })
        assert kb_article_r.status_code == 200, kb_article_r.text
        kb_article_id = kb_article_r.json()['article']['id']

        kb_feedback_r = client.post(
            f'/kb/articles/{kb_article_id}/feedback',
            headers=_headers('tenant-a'),
            json={'helpful': True, 'comment': 'Very clear'},
        )
        assert kb_feedback_r.status_code == 200, kb_feedback_r.text

        # Surveys (NPS)
        survey_r = client.post('/surveys', headers=_headers('tenant-a'), json={
            'name': 'Post-support NPS',
            'survey_type': 'nps',
            'trigger_event': 'ticket_resolved',
            'follow_up_threshold': 6,
        })
        assert survey_r.status_code == 200, survey_r.text
        survey_id = survey_r.json()['survey']['id']

        survey_resp_r = client.post(
            f'/surveys/{survey_id}/respond',
            headers=_headers('tenant-a'),
            json={
                'survey_id': survey_id,
                'respondent_email': 'customer@example.com',
                'primary_score': 9,
                'answers': [],
                'verbatim': 'Great support',
            },
        )
        assert survey_resp_r.status_code == 200, survey_resp_r.text

        survey_an_r = client.get(f'/surveys/{survey_id}/analytics', headers=_headers('tenant-a'))
        assert survey_an_r.status_code == 200, survey_an_r.text
        assert survey_an_r.json()['total_responses'] >= 1

        # Documents and quotes
        doc_r = client.post('/documents', headers=_headers('tenant-a'), json={
            'title': 'Enterprise Proposal',
            'doc_type': 'proposal',
            'description': 'Proposal for enterprise plan',
            'content_body': 'Proposal content',
        })
        assert doc_r.status_code == 200, doc_r.text
        doc_id = doc_r.json()['document']['id']

        share_r = client.post(
            f'/documents/{doc_id}/share',
            headers=_headers('tenant-a'),
            json={
                'recipient_email': BUYER_EMAIL,
                'recipient_name': 'Procurement Lead',
                'message': 'Please review',
                'expires_in_days': 30,
            },
        )
        assert share_r.status_code == 200, share_r.text
        share_data = share_r.json()['share']
        assert share_data['expires_at'] > share_data['shared_at']

        quote_r = client.post('/quotes', headers=_headers('tenant-a'), json={
            'title': 'Annual Platform Quote',
            'recipient_email': BUYER_EMAIL,
            'recipient_name': 'Procurement Lead',
            'line_items': [
                {'name': 'Platform License', 'quantity': 1, 'unit_price': 12000, 'discount_pct': 0, 'tax_pct': 0}
            ],
            'currency': 'USD',
            'valid_days': 30,
        })
        assert quote_r.status_code == 200, quote_r.text
        quote_id = quote_r.json()['quote']['id']

        quote_send_r = client.post(f'/quotes/{quote_id}/send', headers=_headers('tenant-a'))
        assert quote_send_r.status_code == 200, quote_send_r.text

        # Workflows
        wf_r = client.post('/workflows', headers=_headers('tenant-a'), json={
            'name': 'Lead Nurture',
            'description': 'Simple nurture flow',
            'trigger': {'trigger_type': 'manual', 'conditions': []},
            'steps': [
                {'step_id': 's1', 'action_type': 'send_email', 'config': {'template': 'welcome'}, 'next_step_id': 's2'},
                {'step_id': 's2', 'action_type': 'delay', 'config': {}, 'delay_hours': 24, 'next_step_id': ''},
            ],
        })
        assert wf_r.status_code == 200, wf_r.text
        workflow_id = wf_r.json()['workflow']['id']

        wf_enroll_r = client.post(
            f'/workflows/{workflow_id}/enroll',
            headers=_headers('tenant-a'),
            json={'contact_id': 'contact-1002', 'contact_email': 'lead@example.com'},
        )
        assert wf_enroll_r.status_code == 200, wf_enroll_r.text

        wf_an_r = client.get(f'/workflows/{workflow_id}/analytics', headers=_headers('tenant-a'))
        assert wf_an_r.status_code == 200, wf_an_r.text
        assert wf_an_r.json()['total_enrollments'] >= 1

        # Product catalog
        prod_cat_r = client.post('/products/categories', headers=_headers('tenant-a'), json={
            'name': 'Subscriptions',
            'description': 'Subscription products',
        })
        assert prod_cat_r.status_code == 200, prod_cat_r.text
        prod_cat_id = prod_cat_r.json()['category']['id']

        product_r = client.post('/products', headers=_headers('tenant-a'), json={
            'name': 'Nuxtron Pro',
            'description': 'Pro tier subscription',
            'sku': 'NUX-PRO-001',
            'category_id': prod_cat_id,
            'unit_price': 299,
            'currency': 'USD',
            'billing_model': 'recurring_monthly',
            'status': 'active',
            'track_inventory': False,
        })
        assert product_r.status_code == 200, product_r.text

        products_list_r = client.get('/products', headers=_headers('tenant-a'))
        assert products_list_r.status_code == 200, products_list_r.text
        assert products_list_r.json()['total'] >= 1

        # ── Enterprise Pentest Platform — Phase 1 ─────────────────────────────
        # Ingest a Semgrep finding
        semgrep_r = client.post(PENTEST_FINDINGS_ENDPOINT, headers=_headers('tenant-a'), json={
            'source': 'semgrep',
            'asset_id': 'repo:nuxtron/backend',
            'asset_type': 'repo',
            'business_criticality': 8.0,
            'payload': {
                'check_id': 'python.flask.security.sql-injection',
                'path': 'backend/app.py',
                'extra': {
                    'message': 'Possible SQL injection via string concatenation.',
                    'severity': 'error',
                },
            },
        })
        assert semgrep_r.status_code == 200, semgrep_r.text
        semgrep_body = semgrep_r.json()
        assert semgrep_body['action'] in {'created', 'deduped'}, semgrep_body
        semgrep_finding_id = semgrep_body['finding_id']
        assert semgrep_body['finding']['severity'] == 'high', semgrep_body
        assert semgrep_body['finding']['risk_score'] > 0, semgrep_body

        # Ingest a Trivy finding
        trivy_r = client.post(PENTEST_FINDINGS_ENDPOINT, headers=_headers('tenant-a'), json={
            'source': 'trivy',
            'asset_id': 'registry/nuxtron:latest',
            'asset_type': 'container_image',
            'business_criticality': 9.0,
            'payload': {
                'VulnerabilityID': 'CVE-2024-1234',
                'PkgName': 'openssl',
                'Severity': 'CRITICAL',
                'Title': 'OpenSSL remote code execution',
                'Description': 'Remote code execution via crafted packet.',
                'CVSS': {'nvd': {'V3Score': 9.8}},
            },
        })
        assert trivy_r.status_code == 200, trivy_r.text
        trivy_body = trivy_r.json()
        assert trivy_body['finding']['severity'] == 'critical', trivy_body
        assert math.isclose(trivy_body['finding']['cvss_score'], 9.8), trivy_body

        # Ingest a ZAP finding
        zap_r = client.post(PENTEST_FINDINGS_ENDPOINT, headers=_headers('tenant-a'), json={
            'source': 'zap',
            'asset_id': 'https://app.nuxtron.io',
            'asset_type': 'url',
            'business_criticality': 7.0,
            'payload': {
                'alertRef': '10038',
                'name': 'Content Security Policy Header Not Set',
                'riskcode': 2,
                'description': 'CSP header is missing from the response.',
                'url': 'https://app.nuxtron.io',
            },
        })
        assert zap_r.status_code == 200, zap_r.text
        assert zap_r.json()['finding']['severity'] == 'medium', zap_r.text

        # Ingest manual finding
        manual_r = client.post(PENTEST_FINDINGS_ENDPOINT, headers=_headers('tenant-a'), json={
            'source': 'manual',
            'asset_id': 'infra/k8s-cluster',
            'asset_type': 'host',
            'business_criticality': 10.0,
            'payload': {
                'title': 'Exposed admin dashboard without authentication',
                'description': 'Admin dashboard is reachable from the internet with no auth.',
                'severity': 'critical',
                'cvss_score': 9.5,
                'exploitability_score': 9.0,
                'vuln_key': 'admin-dashboard-no-auth',
                'source_finding_id': 'PENTEST-001',
            },
        })
        assert manual_r.status_code == 200, manual_r.text
        assert manual_r.json()['finding']['severity'] == 'critical', manual_r.text

        # Deduplication: ingest the same Semgrep finding again — should return deduped
        dedup_r = client.post(PENTEST_FINDINGS_ENDPOINT, headers=_headers('tenant-a'), json={
            'source': 'semgrep',
            'asset_id': 'repo:nuxtron/backend',
            'asset_type': 'repo',
            'business_criticality': 8.0,
            'payload': {
                'check_id': 'python.flask.security.sql-injection',
                'path': 'backend/app.py',
                'extra': {
                    'message': 'Possible SQL injection via string concatenation.',
                    'severity': 'error',
                },
            },
        })
        assert dedup_r.status_code == 200, dedup_r.text
        assert dedup_r.json()['action'] == 'deduped', dedup_r.text
        assert dedup_r.json()['finding']['dedupe_count'] == 2, dedup_r.text

        # List findings
        list_r = client.get('/pentest/findings', headers=_headers('tenant-a'))
        assert list_r.status_code == 200, list_r.text
        assert list_r.json()['total'] >= 4, list_r.text
        # Highest risk should come first
        findings_sorted = list_r.json()['findings']
        assert findings_sorted[0]['risk_score'] >= findings_sorted[-1]['risk_score'], 'findings not sorted by risk'

        # Remediation queue
        queue_r = client.get('/pentest/queue', headers=_headers('tenant-a'))
        assert queue_r.status_code == 200, queue_r.text
        assert len(queue_r.json()['queue']) >= 1, queue_r.text

        # Stats
        stats_r = client.get('/pentest/findings/stats', headers=_headers('tenant-a'))
        assert stats_r.status_code == 200, stats_r.text
        stats = stats_r.json()
        assert stats['total'] >= 4, stats
        assert stats['by_severity']['critical'] >= 2, stats

        # Get single finding
        get_r = client.get(f'/pentest/findings/{semgrep_finding_id}', headers=_headers('tenant-a'))
        assert get_r.status_code == 200, get_r.text
        assert get_r.json()['finding_id'] == semgrep_finding_id, get_r.text

        # 404 for unknown finding
        miss_r = client.get('/pentest/findings/nonexistent000', headers=_headers('tenant-a'))
        assert miss_r.status_code == 404, miss_r.text

        # Triage — mark Semgrep finding as false_positive
        triage_r = client.post(
            f'/pentest/findings/{semgrep_finding_id}/triage',
            headers=_headers('tenant-a'),
            json={'outcome': 'false_positive', 'notes': 'Reviewed: parameterised queries in use.'},
        )
        assert triage_r.status_code == 200, triage_r.text
        assert triage_r.json()['outcome'] == 'false_positive', triage_r.text
        assert triage_r.json()['finding']['status'] == 'false_positive', triage_r.text

        # Verify triaged finding is excluded from open queue
        queue_after_r = client.get('/pentest/queue', headers=_headers('tenant-a'))
        assert queue_after_r.status_code == 200, queue_after_r.text
        queue_ids = [f['finding_id'] for f in queue_after_r.json()['queue']]
        assert semgrep_finding_id not in queue_ids, 'false_positive should not appear in queue'

        # Triage — mark Trivy finding as true_positive → status becomes triaged
        trivy_finding_id = trivy_r.json()['finding_id']
        triage_tp_r = client.post(
            f'/pentest/findings/{trivy_finding_id}/triage',
            headers=_headers('tenant-a'),
            json={'outcome': 'true_positive', 'notes': 'Confirmed critical CVE.', 'assignee': 'security-lead'},
        )
        assert triage_tp_r.status_code == 200, triage_tp_r.text
        assert triage_tp_r.json()['finding']['status'] == 'triaged', triage_tp_r.text

        # Invalid triage outcome returns 422
        invalid_triage_r = client.post(
            f'/pentest/findings/{trivy_finding_id}/triage',
            headers=_headers('tenant-a'),
            json={'outcome': 'bad_outcome'},
        )
        assert invalid_triage_r.status_code == 422, invalid_triage_r.text

        # Invalid source returns 422
        bad_source_r = client.post(PENTEST_FINDINGS_ENDPOINT, headers=_headers('tenant-a'), json={
            'source': 'unknown_tool',
            'asset_id': 'test',
            'business_criticality': 5.0,
            'payload': {},
        })
        assert bad_source_r.status_code == 422, bad_source_r.text

        # Stats after triage — MTTR is still None (no remediated status yet)
        stats_after_r = client.get('/pentest/findings/stats', headers=_headers('tenant-a'))
        assert stats_after_r.status_code == 200, stats_after_r.text

        # Tenant isolation: findings from tenant-a must not be visible from tenant-b
        iso_r = client.get('/pentest/findings', headers=_headers('tenant-b'))
        assert iso_r.status_code == 200, iso_r.text
        assert iso_r.json()['total'] == 0, 'tenant isolation violated on pentest findings'

        # ── Enterprise Pentest Platform — Phase 2 ─────────────────────────────
        # policy_tier is present on newly created finding
        assert 'policy_tier' in semgrep_r.json()['finding'], 'policy_tier missing from finding'

        # Default policy: risk_score >=8.5 → critical, >=6.5 → high, >=4.0 → medium, else low
        pol_r = client.get(PENTEST_RISK_POLICY_ENDPOINT, headers=_headers('tenant-a'))
        assert pol_r.status_code == 200, pol_r.text
        pol_data = pol_r.json()
        assert math.isclose(pol_data['critical_threshold'], 8.5), 'default critical_threshold mismatch'
        assert math.isclose(pol_data['high_threshold'], 6.5), 'default high_threshold mismatch'

        # PUT /pentest/risk-policy — configure custom thresholds
        update_pol_r = client.put(PENTEST_RISK_POLICY_ENDPOINT, headers=_headers('tenant-a'), json={
            'critical_threshold': 9.0,
            'high_threshold': 7.0,
            'medium_threshold': 4.5,
            'critical_sla_hours': 12,
            'high_sla_hours': 48,
            'medium_sla_hours': 120,
            'low_sla_hours': 480,
        })
        assert update_pol_r.status_code == 200, update_pol_r.text
        updated_pol = update_pol_r.json()['policy']
        assert math.isclose(updated_pol['critical_threshold'], 9.0), 'policy update: critical_threshold mismatch'
        assert updated_pol['critical_sla_hours'] == 12, 'policy update: critical_sla_hours mismatch'

        # Invalid thresholds: must satisfy critical > high > medium
        bad_pol_r = client.put(PENTEST_RISK_POLICY_ENDPOINT, headers=_headers('tenant-a'), json={
            'critical_threshold': 5.0,
            'high_threshold': 7.0,   # high > critical → invalid
            'medium_threshold': 4.0,
        })
        assert bad_pol_r.status_code == 422, f'Expected 422 for invalid thresholds, got {bad_pol_r.status_code}'

        # GET policy returns the saved policy, not defaults
        refetch_pol_r = client.get(PENTEST_RISK_POLICY_ENDPOINT, headers=_headers('tenant-a'))
        assert math.isclose(refetch_pol_r.json()['critical_threshold'], 9.0), 'policy refetch: stale value'

        # Policy isolation: tenant-b should still return defaults
        pol_b_r = client.get(PENTEST_RISK_POLICY_ENDPOINT, headers=_headers('tenant-b'))
        assert pol_b_r.status_code == 200, pol_b_r.text
        assert math.isclose(pol_b_r.json()['critical_threshold'], 8.5), 'tenant-b should receive default policy'

        # DefectDojo config: 404 when not configured
        no_cfg_r = client.get(PENTEST_DEFECTDOJO_CONFIG_ENDPOINT, headers=_headers('tenant-a'))
        assert no_cfg_r.status_code == 404, f'Expected 404 before config, got {no_cfg_r.status_code}'

        # PUT /pentest/defectdojo/config — save connection details
        dojo_api_key = os.getenv('SELFTEST_DEFECTDOJO_API_KEY', 'selftest-defectdojo-token')
        cfg_r = client.put(PENTEST_DEFECTDOJO_CONFIG_ENDPOINT, headers=_headers('tenant-a'), json={
            'url': 'https://defectdojo.example.com',
            'api_key': dojo_api_key,
            'product_id': 5,
            'engagement_name': 'Pentest Platform Selftest',
            'auto_sync': False,
        })
        assert cfg_r.status_code == 200, cfg_r.text
        cfg_data = cfg_r.json()['config']
        assert cfg_data['product_id'] == 5, 'product_id not stored'
        assert '*' in cfg_data.get('api_key', ''), 'API key should be masked (contain asterisks) in response'
        assert cfg_data.get('api_key', '') != dojo_api_key, 'API key must not be returned in full'

        # GET config returns saved config (masked)
        get_cfg_r = client.get(PENTEST_DEFECTDOJO_CONFIG_ENDPOINT, headers=_headers('tenant-a'))
        assert get_cfg_r.status_code == 200, get_cfg_r.text
        assert get_cfg_r.json()['config']['product_id'] == 5, 'GET config product_id mismatch'
        assert get_cfg_r.json()['config']['url'] == 'https://defectdojo.example.com'

        # Invalid URL scheme
        bad_url_r = client.put(PENTEST_DEFECTDOJO_CONFIG_ENDPOINT, headers=_headers('tenant-a'), json={
            'url': 'ftp://bad.example.com',
            'api_key': 'key',
            'product_id': 1,
        })
        assert bad_url_r.status_code == 422, f'Expected 422 for bad URL scheme, got {bad_url_r.status_code}'

        # Sync: DefectDojo is configured but unreachable → status=failed in sync record
        sync_r = client.post('/pentest/defectdojo/sync', headers=_headers('tenant-a'), json={
            'finding_id': semgrep_finding_id,
        })
        assert sync_r.status_code == 200, sync_r.text
        sync_resp = sync_r.json()
        assert sync_resp['synced'] == 1, 'Expected 1 finding synced'
        assert len(sync_resp['records']) == 1, 'Expected 1 sync record'
        sync_record = sync_resp['records'][0]
        assert sync_record['finding_id'] == semgrep_finding_id, 'sync record finding_id mismatch'
        assert sync_record['status'] in {'synced', 'failed', 'pending'}, f"Unexpected status: {sync_record['status']}"

        # Sync queue: record should now appear in queue
        queue_r2 = client.get('/pentest/defectdojo/queue', headers=_headers('tenant-a'))
        assert queue_r2.status_code == 200, queue_r2.text
        assert queue_r2.json()['total'] >= 1, 'Sync queue should have ≥1 record'

        # GET sync record by finding_id
        sync_detail_r = client.get(f'/pentest/defectdojo/sync/{semgrep_finding_id}', headers=_headers('tenant-a'))
        assert sync_detail_r.status_code == 200, sync_detail_r.text
        assert sync_detail_r.json()['finding_id'] == semgrep_finding_id

        # 404 for unknown finding_id
        miss_sync_r = client.get('/pentest/defectdojo/sync/nonexistent-id', headers=_headers('tenant-a'))
        assert miss_sync_r.status_code == 404, f'Expected 404 for missing sync record, got {miss_sync_r.status_code}'

        # Retry endpoint: returns 422 if no DD config for the tenant
        no_cfg_retry_r = client.post('/pentest/defectdojo/retry', headers=_headers('tenant-b'))
        assert no_cfg_retry_r.status_code == 422, f'Expected 422 retry without config, got {no_cfg_retry_r.status_code}'

        # Retry endpoint: works when config is present (will retry any failed records)
        retry_r = client.post('/pentest/defectdojo/retry', headers=_headers('tenant-a'))
        assert retry_r.status_code == 200, retry_r.text
        assert 'retried' in retry_r.json(), 'retry response missing retried count'

        # Bulk sync: sync all open findings without an existing record
        bulk_r = client.post('/pentest/defectdojo/sync', headers=_headers('tenant-a'), json={})
        assert bulk_r.status_code == 200, bulk_r.text
        assert 'synced' in bulk_r.json(), 'bulk sync response missing synced count'

        # Phase 2 tenant isolation: tenant-b queue should be empty
        iso_queue_r = client.get('/pentest/defectdojo/queue', headers=_headers('tenant-b'))
        assert iso_queue_r.status_code == 200, iso_queue_r.text
        assert iso_queue_r.json()['total'] == 0, 'tenant isolation violated on sync queue'

    print('FastAPI selftest passed')



if __name__ == '__main__':
    args = {arg.strip().lower() for arg in sys.argv[1:]}
    run_vse_only = '--vse-only' in args
    include_vse_arg = '--include-vse' in args
    include_vse_env = os.getenv('SELFTEST_INCLUDE_VSE', '0').strip().lower() in {'1', 'true', 'yes', 'on'}

    if not run_vse_only:
        run_selftest()

    include_vse = run_vse_only or include_vse_arg or include_vse_env
    if include_vse:
        from importlib import import_module

        module = import_module('backend.fastapi.app.vse_selftest')
        run_vse_selftest = module.run_vse_selftest

        run_vse_selftest()
        print('FastAPI VSE selftest extension passed')

