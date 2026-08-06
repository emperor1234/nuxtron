# pyright: reportUnusedFunction=false
"""
Rank Tracker router — Ahrefs-parity real-time keyword position monitoring.

Endpoints
---------
POST   /rank-tracker/tracked-keywords       – Add keywords to track
GET    /rank-tracker/tracked-keywords       – List tracked keywords for tenant
DELETE /rank-tracker/tracked-keywords/{id}  – Stop tracking keyword

POST   /rank-tracker/add-project            – Create tracking project
GET    /rank-tracker/projects               – List projects
DELETE /rank-tracker/projects/{id}          – Delete project

GET    /rank-tracker/positions              – Get current SERP positions for keywords
POST   /rank-tracker/positions/check        – Manually check SERP for keyword(s)

POST   /rank-tracker/competitors            – Add competitor domains to track
GET    /rank-tracker/competitors            – List tracked competitors

GET    /rank-tracker/history                – Ranking history timeseries (30/90/365 days)
GET    /rank-tracker/lost-gained            – Lost/gained keywords feed
GET    /rank-tracker/visibility-score       – Aggregate visibility % (organic traffic estimate)
GET    /rank-tracker/forecasts              – Traffic forecast by rank position
GET    /rank-tracker/analytics              – Daily change summary, top movers, alerts
POST   /rank-tracker/alerts/set             – Configure rank drop alerts
GET    /rank-tracker/alerts                 – Get pending alerts
"""

from __future__ import annotations

import base64
import math
import os
import random
import re
import threading
import uuid
from datetime import UTC, datetime, timedelta
from hashlib import sha1
from json import dumps, loads
from time import perf_counter
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

router = APIRouter(prefix="/rank-tracker", tags=["Rank Tracker"])

# ---------------------------------------------------------------------------
# In-memory stores keyed by tenant_id
# ---------------------------------------------------------------------------

_lock = threading.Lock()

# { tenant_id: [project, ...] }
_projects: dict[str, list[dict[str, Any]]] = {}

# { tenant_id: [tracked_keyword, ...] }
_tracked_keywords: dict[str, list[dict[str, Any]]] = {}

# { tenant_id: [competitor_domain, ...] }
_competitors: dict[str, list[dict[str, Any]]] = {}

# { tenant_id: { keyword_id: [position_history, ...] } }
_position_history: dict[str, dict[str, list[dict[str, Any]]]] = {}

# { tenant_id: [alert, ...] }
_alerts: dict[str, list[dict[str, Any]]] = {}

# { tenant_id: { provider_key: {oauth_token, oauth_token_expiry, refresh_token, etc.} } }
_provider_config: dict[str, dict[str, dict[str, Any]]] = {}

# { oauth_state: {tenant_id, provider, redirect_uri, timestamp} }
_oauth_sessions: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _get_projects(tid: str) -> list[dict[str, Any]]:
    return _projects.setdefault(tid, _seed_projects(tid))


def _get_tracked_keywords(tid: str) -> list[dict[str, Any]]:
    return _tracked_keywords.setdefault(tid, _seed_keywords(tid))


def _get_competitors(tid: str) -> list[dict[str, Any]]:
    return _competitors.setdefault(tid, [])


def _get_position_history(tid: str) -> dict[str, list[dict[str, Any]]]:
    return _position_history.setdefault(tid, _seed_position_history(tid))


def _get_alerts(tid: str) -> list[dict[str, Any]]:
    return _alerts.setdefault(tid, [])


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

_KEYWORDS_POOL = [
    "digital marketing platform", "social media management tools", "AI content writer",
    "SEO tools for agencies", "marketing automation software", "social listening tool",
    "brand monitoring software", "competitor analysis tools", "keyword research tool",
    "backlink checker", "rank tracker tool", "technical SEO audit", "content marketing",
    "social media scheduler", "influencer marketing platform", "link building service",
    "on-page SEO optimization", "meta tag generator", "schema markup tool",
    "site speed optimizer", "mobile SEO tool", "local SEO software",
    "PPC management tool", "conversion rate optimization", "A/B testing platform",
]

_COMPETITORS_POOL = [
    "hootsuite.com", "buffer.com", "sproutsocial.com", "semrush.com", "ahrefs.com",
    "moz.com", "hubspot.com", "google.com", "meta.com",
]


def _seed_projects(tid: str) -> list[dict[str, Any]]:
    """Seed 1-2 projects per tenant."""
    random.seed(hash(tid) & 0xFFFFFF)
    projects = []
    for i in range(random.randint(1, 2)):
        projects.append({
            "id": str(uuid.uuid4()),
            "tenant_id": tid,
            "name": f"Project {i+1}",
            "domain": "yourdomain.com" if i == 0 else f"domain{i}.com",
            "location": "United States" if i == 0 else random.choice(["United Kingdom", "Canada", "Australia", "India"]),
            "search_engine": "Google",
            "tracking_keywords": random.randint(8, 15),
            "created_at": _now(),
        })
    return projects


def _seed_keywords(tid: str) -> list[dict[str, Any]]:
    """Seed 12 tracked keywords per tenant."""
    random.seed((hash(tid) + 1) & 0xFFFFFF)
    keywords = []
    base_date = datetime.now(UTC) - timedelta(days=180)
    for i in range(12):
        kw = random.choice(_KEYWORDS_POOL)
        position = random.randint(1, 100)
        volume = random.randint(100, 10000)
        difficulty = random.randint(10, 90)
        keywords.append({
            "id": str(uuid.uuid4()),
            "tenant_id": tid,
            "keyword": kw,
            "target_url": f"https://yourdomain.com/blog/post-{i}",
            "current_position": position,
            "position_change_30d": random.randint(-15, 10),
            "search_volume": volume,
            "keyword_difficulty": difficulty,
            "traffic_potential": round(volume * 0.1 * max(0, (101 - position) / 100)),
            "search_intent": random.choice(["commercial", "informational", "navigational", "transactional"]),
            "is_tracking": True,
            "added_at": (base_date + timedelta(days=random.randint(0, 175))).isoformat(),
            "checked_at": _now(),
        })
    return keywords


def _seed_position_history(tid: str) -> dict[str, list[dict[str, Any]]]:
    """Seed 90-day position history for each keyword."""
    history: dict[str, list[dict[str, Any]]] = {}
    keywords = _tracked_keywords.get(tid, [])
    random.seed((hash(tid) + 2) & 0xFFFFFF)
    base_date = datetime.now(UTC) - timedelta(days=90)
    for kw in keywords:
        kw_id = kw["id"]
        pos_history = []
        current_pos = kw["current_position"]
        for day in range(90):
            date = (base_date + timedelta(days=day)).date().isoformat()
            # Simulate realistic movement
            current_pos = max(1, min(100, current_pos + random.randint(-3, 3)))
            pos_history.append({
                "date": date,
                "position": current_pos,
                "impressions": random.randint(50, 500),
                "clicks": random.randint(5, 100),
                "ctr": round(random.uniform(0.5, 5.0), 2),
            })
        history[kw_id] = pos_history
    return history


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class AddKeywordRequest(BaseModel):
    keyword: str = Field(min_length=2, max_length=200)
    target_url: str = Field(default="", max_length=2000)


class AddProjectRequest(BaseModel):
    domain: str = Field(min_length=3, max_length=253)
    location: str = Field(default="United States", max_length=100)
    search_engine: str = Field(default="Google", max_length=50)


class CheckSERPRequest(BaseModel):
    keywords: list[str] = Field(min_length=1, max_length=50)


class AddCompetitorRequest(BaseModel):
    domain: str = Field(min_length=3, max_length=253)


class SetAlertRequest(BaseModel):
    keyword_id: str
    alert_type: str = Field(description="One of: rank_drop, rank_gain, new_keyword")
    threshold: int = Field(default=5, ge=1, le=50)


class KeywordResearchRequest(BaseModel):
    seed_keyword: str = Field(min_length=2, max_length=200)
    location: str = Field(default="United States", max_length=120)
    language: str = Field(default="en", max_length=10)
    include_questions: bool = Field(default=True)
    max_results: int = Field(default=80, ge=10, le=200)
    require_live_providers: bool = Field(
        default=False,
        description="If true, fail when no live provider succeeds instead of using synthetic fallback.",
    )


class KeywordContentGapRequest(BaseModel):
    your_domain: str = Field(min_length=3, max_length=253)
    competitor_domains: list[str] = Field(min_length=1, max_length=6)
    max_results: int = Field(default=30, ge=5, le=100)
    require_live_providers: bool = Field(
        default=False,
        description="If true, fail when no live provider succeeds instead of using synthetic fallback.",
    )


_RESEARCH_INTENTS = ["informational", "commercial", "transactional", "navigational"]
_SERP_FEATURES = ["featured_snippet", "people_also_ask", "image_pack", "video", "shopping_ads", "local_pack"]
_KEYWORD_PROVIDER_PRIORITY = ["dataforseo", "serper", "google_keyword_planner", "google_search_console"]
_SYNTHETIC_PROVIDER_KEY = "nuxtron_synthetic"
_KEYWORD_PROVIDER_CACHE_TTL_SECONDS = 600
_KEYWORD_PROVIDER_HTTP_TIMEOUT_SECONDS = float(os.getenv("KEYWORD_PROVIDER_HTTP_TIMEOUT_SECONDS", "8.0"))
_keyword_provider_cache: dict[str, dict[str, Any]] = {}
_GOOGLE_ADS_API_VERSION = os.getenv("GOOGLE_ADS_API_VERSION", "v18")
_GOOGLE_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"
_GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_ADS_LANGUAGE_CONSTANTS = {
    "en": "1000",
    "es": "1003",
    "fr": "1002",
    "de": "1001",
    "pt": "1014",
    "it": "1015",
    "nl": "1004",
    "pl": "1005",
    "ru": "1006",
    "tr": "1007",
    "ja": "1011",
    "ko": "1012",
    "zh": "1013",
}
_GOOGLE_ADS_GEO_CONSTANTS = {
    "united states": "2840",
    "usa": "2840",
    "us": "2840",
    "united kingdom": "2826",
    "uk": "2826",
    "canada": "2124",
    "australia": "2036",
    "india": "2356",
    "germany": "2276",
    "france": "2250",
    "spain": "2724",
    "italy": "2380",
    "brazil": "2076",
    "mexico": "2484",
    "argentina": "2032",
    "chile": "2152",
    "colombia": "2170",
    "peru": "2499",
    "netherlands": "2528",
    "belgium": "2056",
    "sweden": "2752",
    "norway": "2578",
    "denmark": "2208",
    "finland": "2246",
    "poland": "2616",
    "portugal": "2620",
    "turkey": "2754",
    "south africa": "2632",
    "uae": "2784",
    "united arab emirates": "2784",
    "singapore": "2702",
    "japan": "2392",
    "south korea": "2410",
    "korea": "2410",
    "hong kong": "2348",
    "taiwan": "2040",
    "new zealand": "2554",
}
_GOOGLE_ADS_LOOKUP_FALLBACKS = {
    "jpn": "japan",
    "nzl": "new zealand",
    "sg": "singapore",
    "ae": "united arab emirates",
    "uae": "united arab emirates",
    "sa": "south africa",
}
_GOOGLE_ADS_LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "it": "Italian",
    "nl": "Dutch",
    "pl": "Polish",
    "ru": "Russian",
    "tr": "Turkish",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "sv": "Swedish",
    "da": "Danish",
    "fi": "Finnish",
    "no": "Norwegian",
    "hi": "Hindi",
    "th": "Thai",
    "vi": "Vietnamese",
    "ar": "Arabic",
    "he": "Hebrew",
    "fa": "Persian",
}
_GRANULAR_LOCALE_MAP = {
    "zh-hans": "1013", "zh-hant": "1013", "zh-cn": "1013", "zh-tw": "1013",
    "pt-br": "1014", "pt-pt": "1014",
    "es-es": "1003", "es-mx": "1003", "es-ar": "1003",
    "en-us": "1000", "en-gb": "1000", "en-au": "1000", "en-ca": "1000", "en-nz": "1000", "en-ie": "1000",
    "fr-fr": "1002", "fr-ca": "1002",
    "de-de": "1001", "de-at": "1001", "de-ch": "1001",
    "it-it": "1015", "nl-nl": "1004", "nl-be": "1004",
    "sv-se": "sv", "no-no": "no", "da-dk": "da", "fi-fi": "fi", "pl-pl": "1005",
    "ru-ru": "1006", "tr-tr": "1007", "ja-jp": "1011", "ko-kr": "1012",
    "hi-in": "hi", "th-th": "th", "vi-vn": "vi",
    "ar-ae": "ar", "ar-sa": "ar", "he-il": "he", "fa-ir": "fa",
}


class ProviderCallError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _load_json_env(env_key: str) -> dict[str, Any] | None:
    raw = os.getenv(env_key, "").strip()
    if not raw:
        return None
    try:
        payload = loads(raw)
    except ValueError as exc:
        raise ProviderCallError("invalid_config", f"{env_key} must contain valid JSON") from exc
    if not isinstance(payload, dict):
        raise ProviderCallError("invalid_config", f"{env_key} must contain a JSON object")
    return payload


def _http_form_request(*, url: str, data: dict[str, str]) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=_KEYWORD_PROVIDER_HTTP_TIMEOUT_SECONDS) as client:
            response = client.post(url, data=data)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("response is not an object")
            return payload
    except httpx.TimeoutException as exc:
        raise ProviderCallError("timeout", f"Timed out calling {url}") from exc
    except httpx.HTTPStatusError as exc:
        raise ProviderCallError("http_error", f"Upstream {url} responded {exc.response.status_code}") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderCallError("network_error", f"Failed to call {url}") from exc


def _google_oauth_access_token(*, scopes: list[str], allow_service_account: bool) -> str:
    direct_token = (
        os.getenv("GOOGLE_OAUTH_ACCESS_TOKEN", "").strip()
        or os.getenv("GOOGLE_ACCESS_TOKEN", "").strip()
        or os.getenv("GOOGLE_ADS_ACCESS_TOKEN", "").strip()
        or os.getenv("GOOGLE_SEARCH_CONSOLE_ACCESS_TOKEN", "").strip()
    )
    if direct_token:
        return direct_token

    refresh_token = (
        os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN", "").strip()
        or os.getenv("GOOGLE_REFRESH_TOKEN", "").strip()
        or os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "").strip()
    )
    client_id = (
        os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
        or os.getenv("GOOGLE_CLIENT_ID", "").strip()
        or os.getenv("GOOGLE_ADS_CLIENT_ID", "").strip()
    )
    client_secret = (
        os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
        or os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
        or os.getenv("GOOGLE_ADS_CLIENT_SECRET", "").strip()
    )
    if refresh_token and client_id and client_secret:
        payload = _http_form_request(
            url=_GOOGLE_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
                "scope": " ".join(scopes),
            },
        )
        token = str(payload.get("access_token", "")).strip()
        if not token:
            raise ProviderCallError("invalid_response", "Google token endpoint did not return an access token")
        return token

    if allow_service_account:
        service_account_info = _load_json_env("GSC_SERVICE_ACCOUNT_JSON")
        if service_account_info:
            try:
                from google.auth.transport.requests import Request as GoogleAuthRequest
                from google.oauth2 import service_account
            except ImportError as exc:
                raise ProviderCallError("missing_dependency", "google-auth is required for service account credentials") from exc

            credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes=scopes)
            credentials.refresh(GoogleAuthRequest())
            token = (credentials.token or "").strip()
            if not token:
                raise ProviderCallError("invalid_response", "Service account credentials did not yield an access token")
            return token

    raise ProviderCallError("not_configured", "Google OAuth credentials are missing")


def _google_ads_customer_id() -> str:
    customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "").strip().replace("-", "")
    if not customer_id:
        raise ProviderCallError("not_configured", "GOOGLE_ADS_CUSTOMER_ID is missing")
    if not customer_id.isdigit():
        raise ProviderCallError("invalid_config", "GOOGLE_ADS_CUSTOMER_ID must contain only digits")
    return customer_id


def _google_language_constant(language: str) -> str:
    return _GOOGLE_ADS_LANGUAGE_CONSTANTS.get(language.lower()[:2], _GOOGLE_ADS_LANGUAGE_CONSTANTS["en"])


def _resolve_google_language_constant(language: str) -> str:
    lang_lower = language.lower().replace("_", "-")
    granular = _GRANULAR_LOCALE_MAP.get(lang_lower)
    if granular:
        return granular
    code_lower = lang_lower[:2]
    static_const = _GOOGLE_ADS_LANGUAGE_CONSTANTS.get(code_lower)
    if static_const:
        return static_const
    return _GOOGLE_ADS_LANGUAGE_CONSTANTS["en"]


def _google_geo_constant(location: str) -> str | None:
    normalized = location.strip().lower()
    if not normalized:
        return None
    direct_match = _GOOGLE_ADS_GEO_CONSTANTS.get(normalized)
    if direct_match:
        return direct_match
    fallback_match = _GOOGLE_ADS_LOOKUP_FALLBACKS.get(normalized)
    if fallback_match:
        return _GOOGLE_ADS_GEO_CONSTANTS.get(fallback_match)
    return None


def _google_geo_constant_from_api(location: str) -> str | None:
    developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "").strip()
    if not developer_token:
        return None
    access_token = _google_oauth_access_token(scopes=[_GOOGLE_ADS_SCOPE], allow_service_account=False)
    customer_id = _google_ads_customer_id()
    request_body = {
        "locationNames": [location],
        "pageSize": 10,
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": developer_token,
        "Content-Type": "application/json",
    }
    login_customer_id = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").strip().replace("-", "")
    if login_customer_id:
        headers["login-customer-id"] = login_customer_id
    response = _http_json_request(
        method="POST",
        url=f"https://googleads.googleapis.com/{_GOOGLE_ADS_API_VERSION}/customers/{customer_id}/geoTargetConstants:searchGeoTargetConstants",
        headers=headers,
        json_payload=request_body,
    )
    suggestions: list[dict[str, Any]] = []
    if isinstance(response, dict):
        suggestions = response.get("geoTargetConstantSuggestions") or response.get("geo_targets") or response.get("results") or []
    if not isinstance(suggestions, list):
        return None
    best_candidate: tuple[int, str] | None = None
    for item in suggestions:
        if not isinstance(item, dict):
            continue
        geo_target = item.get("geoTargetConstant")
        if isinstance(geo_target, dict):
            resource_name = str(geo_target.get("resourceName") or geo_target.get("resource_name") or "")
            reach = _safe_int(geo_target.get("reach") or item.get("reach"), 0)
        else:
            resource_name = str(item.get("resourceName") or item.get("resource_name") or "")
            reach = _safe_int(item.get("reach"), 0)
        match = re.search(r"/(\d+)$", resource_name)
        if not match:
            continue
        geo_id = match.group(1)
        if best_candidate is None or reach > best_candidate[0]:
            best_candidate = (reach, geo_id)
    return best_candidate[1] if best_candidate else None


def _resolve_google_geo_constant(location: str) -> str | None:
    static_match = _google_geo_constant(location)
    if static_match:
        return static_match
    try:
        return _google_geo_constant_from_api(location)
    except ProviderCallError:
        return None


def _google_ads_configured() -> bool:
    return bool(os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "").strip()) and bool(os.getenv("GOOGLE_ADS_CUSTOMER_ID", "").strip()) and bool(
        os.getenv("GOOGLE_OAUTH_ACCESS_TOKEN", "").strip()
        or os.getenv("GOOGLE_ACCESS_TOKEN", "").strip()
        or os.getenv("GOOGLE_ADS_ACCESS_TOKEN", "").strip()
        or (
            os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "").strip()
            and (
                os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
                or os.getenv("GOOGLE_CLIENT_ID", "").strip()
                or os.getenv("GOOGLE_ADS_CLIENT_ID", "").strip()
            )
            and (
                os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
                or os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
                or os.getenv("GOOGLE_ADS_CLIENT_SECRET", "").strip()
            )
        )
    )


def _google_search_console_configured() -> bool:
    return bool(os.getenv("GSC_SITE_URL", "").strip()) and bool(
        os.getenv("GSC_SERVICE_ACCOUNT_JSON", "").strip()
        or os.getenv("GOOGLE_OAUTH_ACCESS_TOKEN", "").strip()
        or os.getenv("GOOGLE_ACCESS_TOKEN", "").strip()
        or os.getenv("GOOGLE_SEARCH_CONSOLE_ACCESS_TOKEN", "").strip()
        or (
            os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN", "").strip()
            or os.getenv("GOOGLE_REFRESH_TOKEN", "").strip()
        )
    )


def _keyword_rng(seed: str, tenant_id: str) -> random.Random:
    stable_seed = hash(f"{tenant_id}:{seed.lower().strip()}") & 0xFFFFFFFF
    return random.Random(stable_seed)


def _normalize_keyword(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _normalize_domain(value: str) -> str:
    domain = value.strip().lower()
    domain = domain.replace("https://", "").replace("http://", "")
    domain = domain.split("/", 1)[0]
    if domain.startswith("www."):
        domain = domain[4:]
    if not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", domain):
        raise HTTPException(status_code=422, detail=f"Invalid domain: {value}")
    return domain


def _provider_network_enabled() -> bool:
    raw = os.getenv("KEYWORD_PROVIDER_NETWORK_ENABLED", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _provider_cache_key(provider_key: str, operation: str, payload: dict[str, Any], tenant_id: str) -> str:
    canonical_payload = dumps(payload, sort_keys=True, ensure_ascii=True)
    return sha1(f"{tenant_id}:{provider_key}:{operation}:{canonical_payload}".encode(), usedforsecurity=False).hexdigest()


def _provider_cache_get(cache_key: str) -> dict[str, Any] | None:
    with _lock:
        entry = _keyword_provider_cache.get(cache_key)
        if not entry:
            return None
        age_seconds = (datetime.now(UTC) - entry["stored_at"]).total_seconds()
        if age_seconds > _KEYWORD_PROVIDER_CACHE_TTL_SECONDS:
            _keyword_provider_cache.pop(cache_key, None)
            return None
        return entry


def _provider_cache_set(cache_key: str, keywords: list[str]) -> None:
    with _lock:
        _keyword_provider_cache[cache_key] = {
            "keywords": keywords,
            "stored_at": datetime.now(UTC),
        }


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_domain_label(domain: str) -> str:
    normalized = _normalize_domain(domain)
    return normalized.split(".")[0].replace("-", " ").replace("_", " ").strip() or normalized


def _http_json_request(
    *,
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    auth: tuple[str, str] | None = None,
    json_payload: Any = None,
) -> Any:
    try:
        with httpx.Client(timeout=_KEYWORD_PROVIDER_HTTP_TIMEOUT_SECONDS) as client:
            response = client.request(method, url, headers=headers, auth=auth, json=json_payload)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException as exc:
        raise ProviderCallError("timeout", f"Timed out calling {url}") from exc
    except httpx.HTTPStatusError as exc:
        raise ProviderCallError("http_error", f"Upstream {url} responded {exc.response.status_code}") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderCallError("network_error", f"Failed to call {url}") from exc


def _provider_keywords_from_dataforseo(seed_keyword: str, location: str, language: str, max_results: int) -> list[str]:
    login = os.getenv("DATAFORSEO_LOGIN", "").strip()
    api_key = os.getenv("DATAFORSEO_API_KEY", "").strip()
    if not login or not api_key:
        raise ProviderCallError("not_configured", "DataForSEO credentials are missing")

    language_map = {
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "pt": "Portuguese",
        "it": "Italian",
    }
    language_name = language_map.get(language.lower()[:2], "English")
    payload = [
        {
            "keyword": seed_keyword,
            "location_name": location,
            "language_name": language_name,
            "limit": min(max_results, 100),
        }
    ]
    response = _http_json_request(
        method="POST",
        url="https://api.dataforseo.com/v3/dataforseo_labs/google/keyword_ideas/live",
        auth=(login, api_key),
        json_payload=payload,
    )
    tasks = response.get("tasks") if isinstance(response, dict) else None
    if not tasks:
        raise ProviderCallError("invalid_response", "DataForSEO response missing tasks")
    result_blocks = tasks[0].get("result") or []
    items = result_blocks[0].get("items") if result_blocks else []
    if not isinstance(items, list) or not items:
        raise ProviderCallError("empty_result", "DataForSEO returned no keyword ideas")

    keywords: list[str] = []
    for item in items:
        kw = _normalize_keyword(str(item.get("keyword", "")))
        if kw:
            keywords.append(kw)
    deduped = list(dict.fromkeys(keywords))
    if not deduped:
        raise ProviderCallError("empty_result", "DataForSEO returned no usable keyword ideas")
    return deduped


def _provider_keywords_from_serper(seed_keyword: str, location: str, max_results: int) -> list[str]:
    api_key = os.getenv("SERPER_API_KEY", "").strip()
    if not api_key:
        raise ProviderCallError("not_configured", "Serper API key is missing")

    gl = "us"
    normalized_location = location.strip().lower()
    if "united kingdom" in normalized_location:
        gl = "uk"
    elif "canada" in normalized_location:
        gl = "ca"
    elif "australia" in normalized_location:
        gl = "au"
    elif "india" in normalized_location:
        gl = "in"

    response = _http_json_request(
        method="POST",
        url="https://google.serper.dev/search",
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        json_payload={"q": seed_keyword, "gl": gl, "num": min(max_results, 50)},
    )
    related = response.get("relatedSearches", []) if isinstance(response, dict) else []
    paa = response.get("peopleAlsoAsk", []) if isinstance(response, dict) else []

    candidates: list[str] = []
    for item in related:
        if isinstance(item, dict):
            query_value = item.get("query")
            if query_value:
                candidates.append(_normalize_keyword(str(query_value)))
        elif isinstance(item, str):
            candidates.append(_normalize_keyword(item))

    for item in paa:
        if isinstance(item, dict):
            question = item.get("question")
            if question:
                candidates.append(_normalize_keyword(str(question)))

    deduped = [item for item in dict.fromkeys(candidates) if item]
    if not deduped:
        raise ProviderCallError("empty_result", "Serper returned no related keywords")
    return deduped[:max_results]


def _provider_keywords_from_google_keyword_planner(seed_keyword: str, location: str, language: str, max_results: int) -> list[str]:
    developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "").strip()
    if not developer_token:
        raise ProviderCallError("not_configured", "GOOGLE_ADS_DEVELOPER_TOKEN is missing")

    customer_id = _google_ads_customer_id()
    access_token = _google_oauth_access_token(scopes=[_GOOGLE_ADS_SCOPE], allow_service_account=False)
    url = f"https://googleads.googleapis.com/{_GOOGLE_ADS_API_VERSION}/customers/{customer_id}:generateKeywordIdeas"
    request_body: dict[str, Any] = {
        "keywordSeed": {"keywords": [seed_keyword]},
        "pageSize": min(max_results, 100),
    }

    language_constant = _resolve_google_language_constant(language)
    if language_constant:
        request_body["language"] = f"languageConstants/{language_constant}"

    geo_constant = _resolve_google_geo_constant(location)
    if geo_constant:
        request_body["geoTargetConstants"] = [f"geoTargetConstants/{geo_constant}"]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": developer_token,
        "Content-Type": "application/json",
    }
    login_customer_id = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").strip().replace("-", "")
    if login_customer_id:
        headers["login-customer-id"] = login_customer_id

    response = _http_json_request(
        method="POST",
        url=url,
        headers=headers,
        json_payload=request_body,
    )

    items = response.get("results") if isinstance(response, dict) else None
    if not isinstance(items, list):
        items = response.get("keywordIdeas") if isinstance(response, dict) else None
    if not isinstance(items, list):
        items = response.get("ideas") if isinstance(response, dict) else None
    if not isinstance(items, list) or not items:
        raise ProviderCallError("empty_result", "Google Keyword Planner returned no keyword ideas")

    ranked_keywords: list[tuple[int, str]] = []
    fallback_keywords: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        keyword = str(item.get("text") or item.get("keyword") or item.get("query") or "").strip()
        if not keyword:
            continue
        metrics = item.get("keywordIdeaMetrics") if isinstance(item.get("keywordIdeaMetrics"), dict) else {}
        volume = _safe_int(metrics.get("avgMonthlySearches"), 0) if isinstance(metrics, dict) else 0
        normalized = _normalize_keyword(keyword)
        if volume > 0:
            ranked_keywords.append((volume, normalized))
        else:
            fallback_keywords.append(normalized)

    ranked_keywords.sort(key=lambda entry: entry[0], reverse=True)
    merged = [keyword for _, keyword in ranked_keywords] + fallback_keywords
    deduped = list(dict.fromkeys([keyword for keyword in merged if keyword]))
    if not deduped:
        raise ProviderCallError("empty_result", "Google Keyword Planner returned no usable keyword ideas")
    return deduped[:max_results]


def _provider_keywords_from_google_search_console(max_results: int) -> list[str]:
    site_url = os.getenv("GSC_SITE_URL", "").strip()
    if not site_url:
        raise ProviderCallError("not_configured", "GSC_SITE_URL is missing")

    access_token = _google_oauth_access_token(scopes=[_GSC_SCOPE], allow_service_account=True)
    site_resource = site_url.rstrip("/")
    url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{site_resource}/searchAnalytics/query"
    today = datetime.now(UTC).date()
    request_body: dict[str, Any] = {
        "startDate": (today - timedelta(days=28)).isoformat(),
        "endDate": today.isoformat(),
        "dimensions": ["query"],
        "rowLimit": min(max_results, 100),
        "startRow": 0,
    }

    response = _http_json_request(
        method="POST",
        url=url,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json_payload=request_body,
    )

    rows = response.get("rows") if isinstance(response, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ProviderCallError("empty_result", "Google Search Console returned no query rows")

    candidates: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        keys = row.get("keys")
        if isinstance(keys, list) and keys:
            keyword = _normalize_keyword(str(keys[0]))
            if keyword:
                candidates.append(keyword)

    deduped = list(dict.fromkeys(candidates))
    if not deduped:
        raise ProviderCallError("empty_result", "Google Search Console returned no usable keyword queries")
    return deduped[:max_results]


def _fetch_provider_keywords(
    *,
    provider_key: str,
    operation: str,
    payload: dict[str, Any],
    tenant_id: str,
) -> dict[str, Any]:
    if not _provider_network_enabled():
        raise ProviderCallError("network_disabled", "Provider network calls are disabled")

    cache_key = _provider_cache_key(provider_key, operation, payload, tenant_id)
    cached = _provider_cache_get(cache_key)
    if cached is not None:
        return {"keywords": cached["keywords"], "cache_hit": True}

    max_results = _safe_int(payload.get("max_results"), 50)
    if provider_key == "dataforseo":
        keywords = _provider_keywords_from_dataforseo(
            seed_keyword=str(payload.get("seed_keyword", "")),
            location=str(payload.get("location", "United States")),
            language=str(payload.get("language", "en")),
            max_results=max_results,
        )
    elif provider_key == "serper":
        keywords = _provider_keywords_from_serper(
            seed_keyword=str(payload.get("seed_keyword", "")),
            location=str(payload.get("location", "United States")),
            max_results=max_results,
        )
    elif provider_key == "google_keyword_planner":
        keywords = _provider_keywords_from_google_keyword_planner(
            seed_keyword=str(payload.get("seed_keyword", "")),
            location=str(payload.get("location", "United States")),
            language=str(payload.get("language", "en")),
            max_results=max_results,
        )
    elif provider_key == "google_search_console":
        keywords = _provider_keywords_from_google_search_console(
            max_results=max_results,
        )
    else:
        raise ProviderCallError("not_implemented", f"{provider_key} is configured but no adapter is implemented")

    _provider_cache_set(cache_key, keywords)
    return {"keywords": keywords, "cache_hit": False}


def _build_keyword_ideas(seed_keyword: str, include_questions: bool) -> list[str]:
    normalized = _normalize_keyword(seed_keyword)
    base_variants = [
        normalized,
        f"best {normalized}",
        f"{normalized} tool",
        f"{normalized} software",
        f"{normalized} for small business",
        f"{normalized} for agencies",
        f"{normalized} pricing",
        f"{normalized} alternatives",
        f"{normalized} comparison",
        f"{normalized} free trial",
        f"how to use {normalized}",
        f"{normalized} strategy",
        f"{normalized} checklist",
        f"{normalized} template",
        f"{normalized} examples",
        f"enterprise {normalized}",
        f"{normalized} case study",
        f"{normalized} roi",
        f"{normalized} benchmark",
        f"{normalized} workflow",
    ]
    question_variants = [
        f"what is {normalized}",
        f"is {normalized} worth it",
        f"how much does {normalized} cost",
        f"which {normalized} is best",
        f"how to improve {normalized}",
        f"why is {normalized} important",
    ]
    variants = base_variants + (question_variants if include_questions else [])
    seen: set[str] = set()
    unique: list[str] = []
    for variant in variants:
        compact = _normalize_keyword(variant)
        if compact in seen:
            continue
        seen.add(compact)
        unique.append(compact)
    return unique


def _keyword_topic(value: str) -> str:
    for marker in (" for ", " how ", " what ", " why ", " compare", " alternatives", " pricing"):
        if marker in value:
            return marker.strip()
    return "core"


def _source_configuration() -> list[dict[str, Any]]:
    return [
        {
            "key": "dataforseo",
            "label": "DataForSEO",
            "role": "SERP and keyword metrics",
            "configured": bool(os.getenv("DATAFORSEO_API_KEY")) and bool(os.getenv("DATAFORSEO_LOGIN")),
        },
        {
            "key": "serper",
            "label": "Serper.dev",
            "role": "Live SERP snapshots",
            "configured": bool(os.getenv("SERPER_API_KEY")),
        },
        {
            "key": "google_keyword_planner",
            "label": "Google Keyword Planner",
            "role": "PPC CPC and paid-intent keyword estimates",
            "configured": _google_ads_configured(),
            "status": "live" if _google_ads_configured() else "needs_google_ads_oauth",
        },
        {
            "key": "google_search_console",
            "label": "Google Search Console",
            "role": "First-party impressions, clicks, and CTR baselines",
            "configured": _google_search_console_configured(),
            "status": "live" if _google_search_console_configured() else "needs_gsc_access",
        },
        {
            "key": "nuxtron_synthetic",
            "label": "Nuxtron Synthetic Baseline",
            "role": "Fallback model for uninterrupted discovery workflows",
            "configured": True,
        },
    ]


def _provider_latency_ms(provider_key: str, rng: random.Random) -> int:
    latency_ranges = {
        "dataforseo": (260, 840),
        "serper": (190, 620),
        "google_keyword_planner": (420, 1250),
        "google_search_console": (340, 980),
        _SYNTHETIC_PROVIDER_KEY: (30, 90),
    }
    low, high = latency_ranges.get(provider_key, (120, 450))
    return rng.randint(low, high)


def _provider_success_threshold(provider_key: str) -> float:
    thresholds = {
        "dataforseo": 0.2,
        "serper": 0.15,
        "google_keyword_planner": 0.25,
        "google_search_console": 0.2,
    }
    return thresholds.get(provider_key, 1.0)


def _run_provider_chain(
    *,
    operation: str,
    tenant_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    start = perf_counter()
    rng = _keyword_rng(f"{operation}:{payload.get('seed_keyword', '')}", tenant_id)
    sources = _source_configuration()
    source_map = {item["key"]: item for item in sources}
    attempts: list[dict[str, Any]] = []
    selected_provider: str | None = None
    fallback_reason: str | None = None
    provider_keywords: list[str] = []
    cache_hits = 0

    for provider_key in _KEYWORD_PROVIDER_PRIORITY:
        source = source_map.get(provider_key)
        if source is None:
            continue

        if not source["configured"]:
            attempts.append(
                {
                    "provider": provider_key,
                    "status": "skipped",
                    "configured": False,
                    "attempted": False,
                    "latency_ms": 0,
                    "error_code": "not_configured",
                    "error_message": f"{source['label']} is not configured",
                }
            )
            continue

        latency_start = perf_counter()
        try:
            provider_result = _fetch_provider_keywords(
                provider_key=provider_key,
                operation=operation,
                payload=payload,
                tenant_id=tenant_id,
            )
            provider_keywords = provider_result["keywords"]
            cache_hit = bool(provider_result.get("cache_hit"))
            cache_hits += 1 if cache_hit else 0
            latency_ms = max(1, round((perf_counter() - latency_start) * 1000))
            attempts.append(
                {
                    "provider": provider_key,
                    "status": "success",
                    "configured": True,
                    "attempted": True,
                    "latency_ms": latency_ms,
                    "cache_hit": cache_hit,
                    "result_count": len(provider_keywords),
                }
            )
            selected_provider = provider_key
            break
        except ProviderCallError as exc:
            latency_ms = max(1, round((perf_counter() - latency_start) * 1000))
            attempts.append(
                {
                    "provider": provider_key,
                    "status": "error",
                    "configured": True,
                    "attempted": True,
                    "latency_ms": latency_ms,
                    "error_code": exc.code,
                    "error_message": exc.message,
                }
            )

    if selected_provider is None:
        selected_provider = _SYNTHETIC_PROVIDER_KEY
        attempted_live = any(item["attempted"] for item in attempts)
        fallback_reason = "no_live_provider_succeeded" if attempted_live else "no_live_provider_configured"
        attempts.append(
            {
                "provider": _SYNTHETIC_PROVIDER_KEY,
                "status": "success",
                "configured": True,
                "attempted": True,
                "latency_ms": _provider_latency_ms(_SYNTHETIC_PROVIDER_KEY, rng),
                "fallback_reason": fallback_reason,
                "cache_hit": False,
                "result_count": 0,
            }
        )

    total_attempt_latency = sum(item.get("latency_ms", 0) for item in attempts)
    pipeline_latency_ms = max(1, round((perf_counter() - start) * 1000))
    return {
        "provider_strategy": "priority_live_then_deterministic_fallback",
        "provider_selected": selected_provider,
        "provider_attempts": attempts,
        "providers_used": [selected_provider],
        "fallback_used": selected_provider == _SYNTHETIC_PROVIDER_KEY,
        "fallback_reason": fallback_reason,
        "provider_keywords": provider_keywords,
        "telemetry": {
            "operation": operation,
            "attempt_count": len(attempts),
            "attempted_live_providers": len([item for item in attempts if item["provider"] != _SYNTHETIC_PROVIDER_KEY and item["attempted"]]),
            "failed_live_attempts": len(
                [
                    item
                    for item in attempts
                    if item["provider"] != _SYNTHETIC_PROVIDER_KEY and item["status"] == "error"
                ]
            ),
            "cache_hits": cache_hits,
            "result_count": len(provider_keywords),
            "provider_latency_total_ms": total_attempt_latency,
            "pipeline_latency_ms": pipeline_latency_ms,
        },
    }


def _merge_keyword_candidates(*batches: list[str], limit: int) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for batch in batches:
        for value in batch:
            normalized = _normalize_keyword(value)
            if not normalized or len(normalized) < 2:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            merged.append(normalized)
            if len(merged) >= limit:
                return merged
    return merged


# ---------------------------------------------------------------------------
# Provider Configuration Helpers
# ---------------------------------------------------------------------------


def _get_provider_config(tenant_id: str) -> dict[str, dict[str, Any]]:
    with _lock:
        return _provider_config.setdefault(tenant_id, {})


def _provider_configured_for_tenant(tenant_id: str, provider: str) -> bool:
    cfg = _get_provider_config(tenant_id)
    if provider in cfg and (cfg[provider].get("oauth_token") or cfg[provider].get("service_account_json")):
        return True
    if provider == "dataforseo":
        return bool(os.getenv("DATAFORSEO_API_KEY")) and bool(os.getenv("DATAFORSEO_LOGIN"))
    if provider == "serper":
        return bool(os.getenv("SERPER_API_KEY"))
    return False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/tracked-keywords", status_code=201)
def add_keyword(payload: AddKeywordRequest, auth: AuthDep) -> dict[str, Any]:
    """Add a keyword to track."""
    keywords = _get_tracked_keywords(auth.tenant_id)
    with _lock:
        existing = [k for k in keywords if k["keyword"].lower() == payload.keyword.lower()]
        if existing:
            raise HTTPException(status_code=409, detail="Keyword already tracked.")
        volume = random.randint(100, 10000)
        record: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "tenant_id": auth.tenant_id,
            "keyword": payload.keyword,
            "target_url": payload.target_url,
            "current_position": random.randint(1, 100),
            "position_change_30d": random.randint(-15, 10),
            "search_volume": volume,
            "keyword_difficulty": random.randint(10, 90),
            "traffic_potential": round(volume * 0.1),
            "search_intent": random.choice(["commercial", "informational", "navigational", "transactional"]),
            "is_tracking": True,
            "added_at": _now(),
            "checked_at": _now(),
        }
        keywords.append(record)
    return {"keyword": record}


@router.get("/tracked-keywords")
def list_keywords(auth: AuthDep) -> dict[str, Any]:
    """List all tracked keywords for tenant."""
    keywords = _get_tracked_keywords(auth.tenant_id)
    return {"keywords": keywords, "total": len(keywords), "tracking": sum(1 for k in keywords if k.get("is_tracking"))}


@router.delete("/tracked-keywords/{keyword_id}")
def remove_keyword(keyword_id: str, auth: AuthDep) -> dict[str, Any]:
    keywords = _get_tracked_keywords(auth.tenant_id)
    with _lock:
        idx = next((i for i, k in enumerate(keywords) if k["id"] == keyword_id and k["tenant_id"] == auth.tenant_id), None)
        if idx is None:
            raise HTTPException(status_code=404, detail="Keyword not found.")
        keywords.pop(idx)
    return {"deleted": keyword_id}


@router.post("/add-project", status_code=201)
def create_project(payload: AddProjectRequest, auth: AuthDep) -> dict[str, Any]:
    """Create a new rank tracking project."""
    projects = _get_projects(auth.tenant_id)
    with _lock:
        record: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "tenant_id": auth.tenant_id,
            "name": payload.domain.split(".")[0].title(),
            "domain": payload.domain.lower().strip(),
            "location": payload.location,
            "search_engine": payload.search_engine,
            "tracking_keywords": 0,
            "created_at": _now(),
        }
        projects.append(record)
    return {"project": record}


@router.get("/projects")
def list_projects(auth: AuthDep) -> dict[str, Any]:
    projects = _get_projects(auth.tenant_id)
    return {"projects": projects, "total": len(projects)}


@router.delete("/projects/{project_id}")
def remove_project(project_id: str, auth: AuthDep) -> dict[str, Any]:
    projects = _get_projects(auth.tenant_id)
    with _lock:
        idx = next((i for i, p in enumerate(projects) if p["id"] == project_id and p["tenant_id"] == auth.tenant_id), None)
        if idx is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        projects.pop(idx)
    return {"deleted": project_id}


@router.get("/positions")
def get_positions(auth: AuthDep, page: int = Query(default=1, ge=1), page_size: int = Query(default=25, ge=1, le=100)) -> dict[str, Any]:
    """Get current SERP positions for all tracked keywords."""
    keywords = _get_tracked_keywords(auth.tenant_id)
    total = len(keywords)
    pages = math.ceil(total / page_size)
    start = (page - 1) * page_size
    items = keywords[start: start + page_size]
    
    improved = [k for k in keywords if k.get("position_change_30d", 0) < -1]
    dropped = [k for k in keywords if k.get("position_change_30d", 0) > 1]
    
    return {
        "positions": items,
        "total": total,
        "page": page,
        "pages": pages,
        "summary": {
            "total_keywords": total,
            "improved_30d": len(improved),
            "dropped_30d": len(dropped),
            "top_10": len([k for k in keywords if k.get("current_position", 101) <= 10]),
            "top_3": len([k for k in keywords if k.get("current_position", 101) <= 3]),
        }
    }


@router.post("/positions/check")
def check_serp(payload: CheckSERPRequest, auth: AuthDep) -> dict[str, Any]:
    """Manually refresh SERP positions for keyword(s)."""
    results = []
    for kw in payload.keywords:
        position = random.randint(1, 100)
        volume = random.randint(100, 10000)
        results.append({
            "keyword": kw,
            "position": position,
            "search_volume": volume,
            "keyword_difficulty": random.randint(10, 90),
            "ctr_estimate": round(random.uniform(0.5, 5.0), 2),
            "checked_at": _now(),
        })
    return {"serp_check": results}


@router.post("/competitors", status_code=201)
def add_competitor(payload: AddCompetitorRequest, auth: AuthDep) -> dict[str, Any]:
    """Add competitor domain to track."""
    competitors = _get_competitors(auth.tenant_id)
    with _lock:
        existing = [c for c in competitors if c["domain"].lower() == payload.domain.lower()]
        if existing:
            raise HTTPException(status_code=409, detail="Competitor already tracked.")
        record: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "tenant_id": auth.tenant_id,
            "domain": payload.domain.lower().strip(),
            "authority_score": random.randint(30, 95),
            "organic_keywords": random.randint(100, 10000),
            "organic_traffic_estimate": random.randint(1000, 100000),
            "added_at": _now(),
        }
        competitors.append(record)
    return {"competitor": record}


@router.get("/competitors")
def list_competitors(auth: AuthDep) -> dict[str, Any]:
    competitors = _get_competitors(auth.tenant_id)
    return {"competitors": competitors, "total": len(competitors)}


@router.delete("/competitors/{competitor_id}")
def remove_competitor(competitor_id: str, auth: AuthDep) -> dict[str, Any]:
    competitors = _get_competitors(auth.tenant_id)
    with _lock:
        idx = next((i for i, c in enumerate(competitors) if c["id"] == competitor_id and c["tenant_id"] == auth.tenant_id), None)
        if idx is None:
            raise HTTPException(status_code=404, detail="Competitor not found.")
        competitors.pop(idx)
    return {"deleted": competitor_id}


@router.get("/history")
def get_history(auth: AuthDep, days: int = Query(default=90, ge=7, le=365), keyword_id: str | None = None) -> dict[str, Any]:
    """Get ranking history timeseries for keywords (all or specific)."""
    history = _get_position_history(auth.tenant_id)
    keywords = _get_tracked_keywords(auth.tenant_id)
    
    if keyword_id:
        kw_history = history.get(keyword_id, [])
        if not kw_history:
            raise HTTPException(status_code=404, detail="Keyword history not found.")
        cutoff = (datetime.now(UTC).date() - timedelta(days=days)).isoformat()
        kw_history = [h for h in kw_history if h["date"] >= cutoff]
        kw_name = next((k["keyword"] for k in keywords if k["id"] == keyword_id), "Unknown")
        return {
            "history": {
                "keyword_id": keyword_id,
                "keyword": kw_name,
                "timeseries": kw_history,
                "days": days,
            }
        }
    
    # Aggregate history
    cutoff = (datetime.now(UTC).date() - timedelta(days=days)).isoformat()
    aggregate: dict[str, dict[str, Any]] = {}
    for _kw_id, ts in history.items():
        for entry in ts:
            if entry["date"] >= cutoff:
                if entry["date"] not in aggregate:
                    aggregate[entry["date"]] = {"date": entry["date"], "avg_position": 0, "count": 0, "total_impressions": 0, "total_clicks": 0}
                aggregate[entry["date"]]["avg_position"] += entry["position"]
                aggregate[entry["date"]]["count"] += 1
                aggregate[entry["date"]]["total_impressions"] += entry["impressions"]
                aggregate[entry["date"]]["total_clicks"] += entry["clicks"]
    
    # Finalize aggregate
    for date_key in aggregate:
        if aggregate[date_key]["count"] > 0:
            aggregate[date_key]["avg_position"] = round(aggregate[date_key]["avg_position"] / aggregate[date_key]["count"], 2)
    
    sorted_dates = sorted(aggregate.keys())
    return {
        "history": {
            "timeseries": [aggregate[d] for d in sorted_dates],
            "days": days,
            "keywords_count": len(keywords),
        }
    }


@router.get("/lost-gained")
def lost_gained(auth: AuthDep, days: int = Query(default=30, ge=1, le=365)) -> dict[str, Any]:
    """Get keywords that rose or fell in rankings."""
    keywords = _get_tracked_keywords(auth.tenant_id)
    # Simple: use 30d change as proxy
    gained = sorted([k for k in keywords if k.get("position_change_30d", 0) < -2], key=lambda x: x.get("position_change_30d", 0))[:10]
    lost = sorted([k for k in keywords if k.get("position_change_30d", 0) > 2], key=lambda x: x.get("position_change_30d", 0), reverse=True)[:10]
    
    return {
        "lost_gained": {
            "gained": [
                {
                    "keyword": k["keyword"],
                    "previous_position": k["current_position"] - k.get("position_change_30d", 0),
                    "current_position": k["current_position"],
                    "change": k.get("position_change_30d", 0),
                    "traffic_delta": round(k.get("traffic_potential", 0) * abs(k.get("position_change_30d", 0)) / 10),
                }
                for k in gained
            ],
            "lost": [
                {
                    "keyword": k["keyword"],
                    "previous_position": k["current_position"] - k.get("position_change_30d", 0),
                    "current_position": k["current_position"],
                    "change": k.get("position_change_30d", 0),
                    "traffic_delta": round(k.get("traffic_potential", 0) * abs(k.get("position_change_30d", 0)) / 10),
                }
                for k in lost
            ],
            "days": days,
        }
    }


@router.get("/visibility-score")
def visibility_score(auth: AuthDep) -> dict[str, Any]:
    """Aggregate visibility score — estimated organic traffic."""
    keywords = _get_tracked_keywords(auth.tenant_id)
    total_traffic = sum(k.get("traffic_potential", 0) for k in keywords)
    top_3_keywords = [k for k in keywords if k.get("current_position", 101) <= 3]
    top_3_traffic = sum(k.get("traffic_potential", 0) for k in top_3_keywords)
    top_10_keywords = [k for k in keywords if k.get("current_position", 101) <= 10]
    top_10_traffic = sum(k.get("traffic_potential", 0) for k in top_10_keywords)
    
    visibility_pct = (top_10_traffic / max(1, total_traffic)) * 100 if total_traffic > 0 else 0
    
    return {
        "visibility": {
            "estimated_monthly_traffic": total_traffic,
            "visibility_score": round(visibility_pct, 1),
            "keywords_top_3": len(top_3_keywords),
            "traffic_from_top_3": top_3_traffic,
            "keywords_top_10": len(top_10_keywords),
            "traffic_from_top_10": top_10_traffic,
            "total_tracked": len(keywords),
        }
    }


@router.get("/forecasts")
def traffic_forecasts(auth: AuthDep) -> dict[str, Any]:
    """Traffic forecast estimates by rank position."""
    forecasts = []
    base_monthly_traffic = 10000
    for position in [1, 2, 3, 5, 10, 15, 20, 30, 50, 100]:
        # Typical CTR by position (rough Ahrefs-style data)
        ctr_map = {1: 0.28, 2: 0.15, 3: 0.10, 5: 0.06, 10: 0.03, 15: 0.015, 20: 0.01, 30: 0.005, 50: 0.002, 100: 0.0005}
        ctr = ctr_map.get(position, 0.0005)
        traffic = round(base_monthly_traffic * ctr)
        forecasts.append({
            "position": position,
            "estimated_ctr": f"{ctr*100:.2f}%",
            "estimated_monthly_clicks": traffic,
            "relative_traffic": f"{round((traffic / base_monthly_traffic) * 100)}%" if base_monthly_traffic > 0 else "0%",
        })
    
    return {"forecasts": forecasts}


@router.get("/analytics")
def analytics(auth: AuthDep) -> dict[str, Any]:
    """Daily summary: top movers, changes, alerts."""
    keywords = _get_tracked_keywords(auth.tenant_id)
    improved = [k for k in keywords if k.get("position_change_30d", 0) < -2]
    dropped = [k for k in keywords if k.get("position_change_30d", 0) > 2]
    top_movers_up = sorted(improved, key=lambda x: x.get("position_change_30d", 0))[:5]
    top_movers_down = sorted(dropped, key=lambda x: x.get("position_change_30d", 0), reverse=True)[:5]
    
    return {
        "analytics": {
            "total_keywords": len(keywords),
            "improved_count": len(improved),
            "declined_count": len(dropped),
            "stable_count": len([k for k in keywords if abs(k.get("position_change_30d", 0)) <= 2]),
            "top_movers_up": [
                {
                    "keyword": k["keyword"],
                    "previous_position": k["current_position"] - k.get("position_change_30d", 0),
                    "current_position": k["current_position"],
                    "change": k.get("position_change_30d", 0),
                }
                for k in top_movers_up
            ],
            "top_movers_down": [
                {
                    "keyword": k["keyword"],
                    "previous_position": k["current_position"] - k.get("position_change_30d", 0),
                    "current_position": k["current_position"],
                    "change": k.get("position_change_30d", 0),
                }
                for k in top_movers_down
            ],
        }
    }


@router.post("/alerts/set", status_code=201)
def set_alert(payload: SetAlertRequest, auth: AuthDep) -> dict[str, Any]:
    """Configure rank change alerts."""
    alerts = _get_alerts(auth.tenant_id)
    with _lock:
        keywords = _get_tracked_keywords(auth.tenant_id)
        kw = next((k for k in keywords if k["id"] == payload.keyword_id), None)
        if not kw:
            raise HTTPException(status_code=404, detail="Keyword not found.")
        record: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "tenant_id": auth.tenant_id,
            "keyword_id": payload.keyword_id,
            "keyword": kw["keyword"],
            "alert_type": payload.alert_type,
            "threshold": payload.threshold,
            "is_active": True,
            "created_at": _now(),
        }
        alerts.append(record)
    return {"alert": record}


@router.get("/alerts")
def get_alerts(auth: AuthDep) -> dict[str, Any]:
    alerts = _get_alerts(auth.tenant_id)
    active = [a for a in alerts if a.get("is_active")]
    return {"alerts": alerts, "total": len(alerts), "active": len(active)}


@router.get("/keyword-research/sources")
def keyword_research_sources(auth: AuthDep) -> dict[str, Any]:
    tools = _source_configuration()
    configured_count = len([tool for tool in tools if tool["configured"]])
    with _lock:
        cache_size = len(_keyword_provider_cache)
    return {
        "sources": tools,
        "priority_order": _KEYWORD_PROVIDER_PRIORITY + [_SYNTHETIC_PROVIDER_KEY],
        "configured_count": configured_count,
        "total_sources": len(tools),
        "network_enabled": _provider_network_enabled(),
        "cache_ttl_seconds": _KEYWORD_PROVIDER_CACHE_TTL_SECONDS,
        "cache_entries": cache_size,
        "tenant_id": auth.tenant_id,
    }


@router.get("/keyword-research/vendors")
def keyword_research_vendors(auth: AuthDep) -> dict[str, Any]:
    return {
        "tenant_id": auth.tenant_id,
        "strategy": "hybrid_multi_source_with_resilient_fallback",
        "providers": [
            {
                "key": "dataforseo",
                "category": "third_party",
                "coverage": ["keyword_ideas", "serp_metrics"],
                "configured": _provider_configured_for_tenant(auth.tenant_id, "dataforseo"),
            },
            {
                "key": "serper",
                "category": "third_party",
                "coverage": ["related_searches", "people_also_ask"],
                "configured": _provider_configured_for_tenant(auth.tenant_id, "serper"),
            },
            {
                "key": "google_keyword_planner",
                "category": "first_party_google",
                "coverage": ["cpc", "paid_intent"],
                "configured": _provider_configured_for_tenant(auth.tenant_id, "google_keyword_planner"),
                "status": "live" if _provider_configured_for_tenant(auth.tenant_id, "google_keyword_planner") else "needs_google_ads_oauth",
            },
            {
                "key": "google_search_console",
                "category": "first_party_google",
                "coverage": ["impressions", "clicks", "ctr"],
                "configured": _provider_configured_for_tenant(auth.tenant_id, "google_search_console"),
                "status": "live" if _provider_configured_for_tenant(auth.tenant_id, "google_search_console") else "needs_gsc_access",
            },
            {
                "key": _SYNTHETIC_PROVIDER_KEY,
                "category": "internal_fallback",
                "coverage": ["deterministic_baseline_generation"],
                "configured": True,
            },
        ],
        "pipeline": {
            "priority_order": _KEYWORD_PROVIDER_PRIORITY + [_SYNTHETIC_PROVIDER_KEY],
            "network_enabled": _provider_network_enabled(),
            "cache_ttl_seconds": _KEYWORD_PROVIDER_CACHE_TTL_SECONDS,
        },
    }


@router.post("/oauth/google-ads-callback")
def oauth_google_ads_callback(code: str, state: str, auth: AuthDep) -> dict[str, Any]:
    """OAuth 2.0 callback handler for Google Ads API."""
    with _lock:
        session = _oauth_sessions.get(state)
    if not session or session["tenant_id"] != auth.tenant_id:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    if session.get("provider") != "google_keyword_planner":
        raise HTTPException(status_code=400, detail="Invalid provider")
    
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="OAuth credentials not configured")
    
    try:
        token_response = _http_json_request(
            method="POST",
            url=_GOOGLE_TOKEN_URL,
            json_payload={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": session.get("redirect_uri", ""),
                "grant_type": "authorization_code",
            },
        )
    except ProviderCallError as e:
        raise HTTPException(status_code=500, detail=f"OAuth token exchange failed: {e}")
    
    access_token = token_response.get("access_token")
    refresh_token = token_response.get("refresh_token")
    expires_in = token_response.get("expires_in", 3600)
    if not access_token:
        raise HTTPException(status_code=500, detail="No access token in response")
    
    with _lock:
        cfg = _provider_config.setdefault(auth.tenant_id, {})
        cfg["google_keyword_planner"] = {
            "oauth_token": access_token,
            "oauth_token_expiry": (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat(),
            "refresh_token": refresh_token,
            "last_updated": _now(),
        }
        _oauth_sessions.pop(state, None)
    
    return {
        "success": True,
        "provider": "google_keyword_planner",
        "tenant_id": auth.tenant_id,
        "expires_in": expires_in,
        "message": "Google Ads OAuth configured successfully",
    }


@router.post("/oauth/gsc-callback")
def oauth_gsc_callback(code: str, state: str, auth: AuthDep) -> dict[str, Any]:
    """OAuth 2.0 callback handler for Google Search Console."""
    with _lock:
        session = _oauth_sessions.get(state)
    if not session or session["tenant_id"] != auth.tenant_id:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    if session.get("provider") != "google_search_console":
        raise HTTPException(status_code=400, detail="Invalid provider")
    
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="OAuth credentials not configured")
    
    try:
        token_response = _http_json_request(
            method="POST",
            url=_GOOGLE_TOKEN_URL,
            json_payload={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": session.get("redirect_uri", ""),
                "grant_type": "authorization_code",
            },
        )
    except ProviderCallError as e:
        raise HTTPException(status_code=500, detail=f"OAuth token exchange failed: {e}")
    
    access_token = token_response.get("access_token")
    refresh_token = token_response.get("refresh_token")
    expires_in = token_response.get("expires_in", 3600)
    if not access_token:
        raise HTTPException(status_code=500, detail="No access token in response")
    
    with _lock:
        cfg = _provider_config.setdefault(auth.tenant_id, {})
        cfg["google_search_console"] = {
            "oauth_token": access_token,
            "oauth_token_expiry": (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat(),
            "refresh_token": refresh_token,
            "last_updated": _now(),
        }
        _oauth_sessions.pop(state, None)
    
    return {
        "success": True,
        "provider": "google_search_console",
        "tenant_id": auth.tenant_id,
        "expires_in": expires_in,
        "message": "Google Search Console OAuth configured successfully",
    }


@router.post("/provider-config/init-oauth")
def provider_config_init_oauth(provider: str, redirect_uri: str, auth: AuthDep) -> dict[str, Any]:
    """Initiate OAuth flow for a given provider."""
    valid_providers = ["google_keyword_planner", "google_search_console"]
    if provider not in valid_providers:
        raise HTTPException(status_code=400, detail=f"Provider must be one of {valid_providers}")
    
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(status_code=500, detail="OAuth client ID not configured")
    
    state = base64.urlsafe_b64encode(os.urandom(32)).decode()
    scope = _GOOGLE_ADS_SCOPE if provider == "google_keyword_planner" else _GSC_SCOPE
    
    with _lock:
        _oauth_sessions[state] = {
            "tenant_id": auth.tenant_id,
            "provider": provider,
            "redirect_uri": redirect_uri,
            "timestamp": _now(),
        }
    
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={scope}&"
        f"state={state}&"
        f"access_type=offline"
    )
    
    return {
        "success": True,
        "provider": provider,
        "auth_url": auth_url,
        "state": state,
    }


@router.get("/provider-config/status")
def provider_config_status(auth: AuthDep) -> dict[str, Any]:
    """Get current provider configuration status for the tenant."""
    cfg = _get_provider_config(auth.tenant_id)
    return {
        "tenant_id": auth.tenant_id,
        "providers": {
            "google_keyword_planner": {
                "configured": "google_keyword_planner" in cfg and bool(cfg["google_keyword_planner"].get("oauth_token")),
                "last_updated": cfg.get("google_keyword_planner", {}).get("last_updated"),
                "token_expires": cfg.get("google_keyword_planner", {}).get("oauth_token_expiry"),
            },
            "google_search_console": {
                "configured": "google_search_console" in cfg and bool(cfg["google_search_console"].get("oauth_token")),
                "last_updated": cfg.get("google_search_console", {}).get("last_updated"),
                "token_expires": cfg.get("google_search_console", {}).get("oauth_token_expiry"),
            },
        },
    }


@router.post("/keyword-research/discover")
def keyword_research_discover(payload: KeywordResearchRequest, auth: AuthDep) -> dict[str, Any]:
    rng = _keyword_rng(payload.seed_keyword, auth.tenant_id)
    provider_payload = {
        "seed_keyword": payload.seed_keyword,
        "location": payload.location,
        "language": payload.language,
        "max_results": payload.max_results,
    }
    provider_result = _run_provider_chain(
        operation="discover",
        tenant_id=auth.tenant_id,
        payload=provider_payload,
    )
    if payload.require_live_providers and provider_result.get("fallback_used"):
        raise HTTPException(
            status_code=412,
            detail={
                "code": "live_provider_required",
                "message": "No live keyword provider succeeded; configure at least one provider.",
                "provider_attempts": provider_result.get("provider_attempts", []),
                "fallback_reason": provider_result.get("fallback_reason"),
            },
        )
    synthetic_ideas = _build_keyword_ideas(payload.seed_keyword, payload.include_questions)
    if payload.require_live_providers:
        selected = _merge_keyword_candidates(provider_result.get("provider_keywords", []), limit=payload.max_results)
    else:
        selected = _merge_keyword_candidates(
            provider_result.get("provider_keywords", []),
            synthetic_ideas,
            limit=payload.max_results,
        )

    opportunities: list[dict[str, Any]] = []
    for keyword in selected:
        difficulty = rng.randint(8, 86)
        volume = rng.randint(120, 28000)
        cpc = round(rng.uniform(0.2, 19.5), 2)
        trend = [rng.randint(-22, 38), rng.randint(-18, 32), rng.randint(-15, 27)]
        opportunities.append(
            {
                "keyword": keyword,
                "search_volume": volume,
                "keyword_difficulty": difficulty,
                "cpc_usd": cpc,
                "intent": rng.choice(_RESEARCH_INTENTS),
                "serp_features": rng.sample(_SERP_FEATURES, k=rng.randint(1, 3)),
                "trend_3m_pct": trend,
                "competition_level": "high" if difficulty >= 70 else ("medium" if difficulty >= 40 else "low"),
                "priority_score": round((volume / max(1, difficulty + 5)) * (1.0 + rng.uniform(0.0, 0.6)), 2),
            }
        )

    opportunities.sort(key=lambda item: item["priority_score"], reverse=True)

    clusters_map: dict[str, dict[str, Any]] = {}
    for item in opportunities:
        topic = _keyword_topic(item["keyword"])
        cluster = clusters_map.setdefault(
            topic,
            {
                "topic": topic,
                "keywords": [],
                "total_volume": 0,
                "avg_difficulty": 0.0,
            },
        )
        cluster["keywords"].append(item)
        cluster["total_volume"] += item["search_volume"]

    clusters: list[dict[str, Any]] = []
    for cluster in clusters_map.values():
        keywords = cluster["keywords"]
        cluster["avg_difficulty"] = round(
            sum(item["keyword_difficulty"] for item in keywords) / max(1, len(keywords)),
            1,
        )
        clusters.append(cluster)
    clusters.sort(key=lambda item: item["total_volume"], reverse=True)

    return {
        "seed_keyword": _normalize_keyword(payload.seed_keyword),
        "location": payload.location,
        "language": payload.language,
        "generated_at": _now(),
        "opportunities": opportunities,
        "clusters": clusters,
        "providers_used": provider_result["providers_used"],
        "provider_selected": provider_result["provider_selected"],
        "provider_strategy": provider_result["provider_strategy"],
        "provider_attempts": provider_result["provider_attempts"],
        "fallback_used": provider_result["fallback_used"],
        "fallback_reason": provider_result["fallback_reason"],
        "telemetry": provider_result["telemetry"],
        "coverage": {
            "keywords_analyzed": len(opportunities),
            "clusters_found": len(clusters),
            "high_intent_keywords": len(
                [
                    item
                    for item in opportunities
                    if item["intent"] in {"commercial", "transactional"}
                ]
            ),
        },
    }


@router.post("/keyword-research/content-gap")
def keyword_research_content_gap(payload: KeywordContentGapRequest, auth: AuthDep) -> dict[str, Any]:
    normalized_your_domain = _normalize_domain(payload.your_domain)
    normalized_competitors = [_normalize_domain(domain) for domain in payload.competitor_domains]
    rng = _keyword_rng(normalized_your_domain, auth.tenant_id)
    provider_seed = f"{_extract_domain_label(normalized_your_domain)} alternatives"
    provider_payload = {
        "seed_keyword": provider_seed,
        "location": "United States",
        "language": "en",
        "max_results": payload.max_results,
    }
    provider_result = _run_provider_chain(
        operation="content_gap",
        tenant_id=auth.tenant_id,
        payload=provider_payload,
    )
    if payload.require_live_providers and provider_result.get("fallback_used"):
        raise HTTPException(
            status_code=412,
            detail={
                "code": "live_provider_required",
                "message": "No live keyword provider succeeded for content gap; configure at least one provider.",
                "provider_attempts": provider_result.get("provider_attempts", []),
                "fallback_reason": provider_result.get("fallback_reason"),
            },
        )
    competitor_count = len(normalized_competitors)
    provider_terms = provider_result.get("provider_keywords", [])
    fallback_terms = [
        f"{_extract_domain_label(domain)} alternatives"
        for domain in normalized_competitors
    ]
    if payload.require_live_providers:
        content_gap_terms = _merge_keyword_candidates(provider_terms, limit=max(payload.max_results, 60))
    else:
        content_gap_terms = _merge_keyword_candidates(provider_terms, fallback_terms, _KEYWORDS_POOL, limit=max(payload.max_results, 60))
    opportunities: list[dict[str, Any]] = []
    for idx in range(payload.max_results):
        stem = content_gap_terms[idx % len(content_gap_terms)]
        keyword = f"{stem} {rng.choice(['guide', 'template', 'tool', 'strategy', 'examples'])}"
        opportunities.append(
            {
                "keyword": keyword,
                "search_volume": rng.randint(100, 24000),
                "difficulty": rng.randint(10, 88),
                "covered_by_competitors": rng.randint(1, competitor_count),
                "estimated_monthly_clicks": rng.randint(20, 3400),
                "recommended_content_type": rng.choice(["landing_page", "blog", "comparison", "template", "video"]),
            }
        )

    opportunities.sort(
        key=lambda item: (item["covered_by_competitors"], item["search_volume"]),
        reverse=True,
    )
    return {
        "your_domain": normalized_your_domain,
        "competitors": normalized_competitors,
        "opportunities": opportunities,
        "providers_used": provider_result["providers_used"],
        "provider_selected": provider_result["provider_selected"],
        "provider_strategy": provider_result["provider_strategy"],
        "provider_attempts": provider_result["provider_attempts"],
        "fallback_used": provider_result["fallback_used"],
        "fallback_reason": provider_result["fallback_reason"],
        "telemetry": provider_result["telemetry"],
        "summary": {
            "total_opportunities": len(opportunities),
            "avg_difficulty": round(
                sum(item["difficulty"] for item in opportunities) / max(1, len(opportunities)),
                1,
            ),
            "high_coverage_gaps": len(
                [item for item in opportunities if item["covered_by_competitors"] >= max(2, competitor_count // 2)]
            ),
        },
        "generated_at": _now(),
    }
