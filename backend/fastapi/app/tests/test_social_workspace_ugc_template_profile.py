"""Tests for UGC template profile persistence in social workspace routes."""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

import os

from backend.fastapi.app import main as app_main
from backend.fastapi.app import memory_stores
from backend.fastapi.app.main import app
from fastapi.testclient import TestClient

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')
os.environ.setdefault('ALLOWED_HOSTS', 'testserver,localhost,127.0.0.1')


def _headers(tenant: str = 'tenant-ugc-tests') -> dict[str, str]:
    return {
        'X-API-Key': 'test-api-key',
        'X-Tenant-Id': tenant,
    }


def _reset_social_stores() -> None:
    memory_stores.social_brand_profiles.clear()
    memory_stores.audit_log.clear()
    app_main.reset_rate_limits_for_tests()


def test_social_brand_profile_contains_ugc_template_defaults() -> None:
    _reset_social_stores()
    client = TestClient(app)

    response = client.get('/social/brand-profile', headers=_headers())

    assert response.status_code == 200
    data = response.json()
    profile = data['brand_profile']
    ugc = profile['ugc_template_profile']

    assert ugc['style_category_id'] == 'no-discount-promo'
    assert ugc['preview_template_id'] == 'tpl-value-story'
    assert ugc['caption_pack_id'] == 'ugc-main-launch'
    assert ugc['platform'] == 'Instagram'
    assert ugc['objective'] == 'Sales'
    assert ugc['hook_style'] == 'Announcement'
    assert ugc['script_style'] == 'Storytelling'
    assert ugc['aspect_ratio'] == '9:16'
    assert ugc['auto_adjust_platforms'] is True
    assert ugc['background_media'] == 'AI Videos'
    assert ugc['subtitles_auto'] is True
    assert ugc['subtitles_language'] == 'Auto (detect)'


def test_update_ugc_template_profile_persists_across_reads() -> None:
    _reset_social_stores()
    client = TestClient(app)

    payload = {
        'style_category_id': 'travel',
        'preview_template_id': 'tpl-destination-hook',
        'caption_pack_id': 'ugc-social-short',
        'platform': 'TikTok',
        'objective': 'Engagement',
        'hook_style': 'Question',
        'script_style': 'Exploratory',
        'aspect_ratio': '9:16',
        'auto_adjust_platforms': False,
        'background_media': 'AI Images',
        'subtitles_auto': True,
        'subtitles_language': 'Spanish',
    }

    save_response = client.put('/social/brand-profile/ugc-template', json=payload, headers=_headers())
    assert save_response.status_code == 200
    saved = save_response.json()['ugc_template_profile']
    assert saved == payload

    read_response = client.get('/social/brand-profile', headers=_headers())
    assert read_response.status_code == 200
    read_back = read_response.json()['brand_profile']['ugc_template_profile']
    assert read_back == payload


def test_update_ugc_template_profile_normalizes_blank_values() -> None:
    _reset_social_stores()
    client = TestClient(app)

    payload = {
        'style_category_id': '  ',
        'preview_template_id': '',
        'caption_pack_id': '',
        'platform': '',
        'objective': '',
        'hook_style': '',
        'script_style': '',
        'aspect_ratio': '',
        'auto_adjust_platforms': False,
        'background_media': '',
        'subtitles_auto': False,
        'subtitles_language': '   ',
    }

    response = client.put('/social/brand-profile/ugc-template', json=payload, headers=_headers())
    assert response.status_code == 200

    normalized = response.json()['ugc_template_profile']
    assert normalized['style_category_id'] == 'no-discount-promo'
    assert normalized['preview_template_id'] == 'tpl-value-story'
    assert normalized['caption_pack_id'] == 'ugc-main-launch'
    assert normalized['platform'] == 'Instagram'
    assert normalized['objective'] == 'Sales'
    assert normalized['hook_style'] == 'Announcement'
    assert normalized['script_style'] == 'Storytelling'
    assert normalized['aspect_ratio'] == '9:16'
    assert normalized['auto_adjust_platforms'] is False
    assert normalized['background_media'] == 'AI Videos'
    assert normalized['subtitles_auto'] is False
    assert normalized['subtitles_language'] == 'Auto (detect)'
