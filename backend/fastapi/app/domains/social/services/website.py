"""Social Workspace website service."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.persistence import _sw_audit
from ....domains.social.persistence import _sw_save_profile_to_db
from ..constants import DEFAULT_FONT_FAMILY
from ..constants import _DEFAULT_KEYWORDS
from ..constants import _INDUSTRY_RULES
from ..constants import _STOP_WORDS
from .brand import _normalize_avatar_profile
from .brand import _normalize_ugc_template_profile
from .brand import _normalize_voiceover_engine
from .workspace import _sw_http_error
from ...identity.secure_egress import resolve_outbound_target
from ...identity.secure_egress import safe_outbound_get
from datetime import UTC
from datetime import datetime
from html import unescape
from typing import Any
from urllib.parse import urljoin
from urllib.parse import urlparse
import httpx
import re


def _clean_text(value: str) -> str:
    without_tags = re.sub("<[^>]+>", " ", value)
    decoded = unescape(without_tags)
    compact = re.sub("\\s+", " ", decoded).strip()
    return compact


def _extract_title(html: str) -> str:
    match = re.search("<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return _clean_text(match.group(1))


def _extract_meta(html: str, keys: list[str]) -> str:
    for key in keys:
        patterns = [
            f"""<meta[^>]+(?:name|property)\\s*=\\s*["\\']{re.escape(key)}["\\'][^>]*content\\s*=\\s*["\\']([^"\\']+)["\\'][^>]*>""",
            f"""<meta[^>]+content\\s*=\\s*["\\']([^"\\']+)["\\'][^>]*(?:name|property)\\s*=\\s*["\\']{re.escape(key)}["\\'][^>]*>""",
        ]
        for pattern in patterns:
            match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
            if match:
                return _clean_text(match.group(1))
    return ""


def _extract_first_tag(html: str, tag: str) -> str:
    match = re.search(f"<{tag}[^>]*>(.*?)</{tag}>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return _clean_text(match.group(1))


def _extract_link_href(html: str, rel_values: list[str]) -> str:
    for rel_value in rel_values:
        patterns = [
            f"""<link[^>]+rel\\s*=\\s*["\\'][^"\\']*{re.escape(rel_value)}[^"\\']*["\\'][^>]*href\\s*=\\s*["\\']([^"\\']+)["\\'][^>]*>""",
            f"""<link[^>]+href\\s*=\\s*["\\']([^"\\']+)["\\'][^>]*rel\\s*=\\s*["\\'][^"\\']*{re.escape(rel_value)}[^"\\']*["\\'][^>]*>""",
        ]
        for pattern in patterns:
            match = re.search(pattern, html, flags=re.IGNORECASE)
            if match:
                return _clean_text(match.group(1))
    return ""


def _fetch_html(normalized_url: str) -> str:
    if not normalized_url.startswith(("https://", "http://")):
        return ""
    try:
        target = resolve_outbound_target(normalized_url, allow_http=True)
        response = safe_outbound_get(
            target,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; NuxtronBrandFetcher/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            },
            timeout=8.0,
            allow_http=True,
            allowed_host_suffix=target.host,
            max_response_bytes=300_000,
        )
        content_type = str(response.headers.get("Content-Type", "")).lower()
        if "text/html" in content_type or not content_type:
            return response.text
    except (httpx.HTTPError, ValueError):
        pass
    return ""


def _extract_keywords_from_html(html: str, brand_name: str, clean_host: str) -> list[str]:
    extracted_title = _extract_meta(html, ["og:title", "twitter:title"]) or _extract_title(html)
    extracted_h1 = _extract_first_tag(html, "h1")
    extracted_description = _extract_meta(
        html, ["description", "og:description", "twitter:description"]
    ) or _extract_first_tag(html, "p")
    meta_keywords = _extract_meta(html, ["keywords"])
    candidates: list[str] = []
    if meta_keywords:
        candidates.extend([item.strip().lower() for item in re.split("[,|;]", meta_keywords) if item.strip()])
    text_blob = " ".join([extracted_title, extracted_h1, extracted_description, brand_name, clean_host])
    word_candidates = re.findall("[A-Za-z][A-Za-z0-9+-]{2,}", text_blob.lower())
    candidates.extend([word for word in word_candidates if word not in _STOP_WORDS])
    dedup: list[str] = []
    for item in candidates:
        if item and item not in dedup:
            dedup.append(item)
    return dedup[:8] or [brand_name.lower()] + _DEFAULT_KEYWORDS


def _detect_industry(keywords: list[str]) -> str:
    for industry_name, tokens in _INDUSTRY_RULES.items():
        if any((token in keywords for token in tokens)):
            return industry_name
    return "marketing"


def _parse_website_host(website_url: str) -> tuple[str, str, str, str]:
    raw_url = website_url.strip()
    candidate = raw_url if raw_url.startswith(("http://", "https://")) else f"https://{raw_url}"
    parsed = urlparse(candidate)
    hostname = (parsed.netloc or parsed.path).strip().lower()
    if not hostname:
        raise _sw_http_error(status_code=422, detail="Website URL is required.")
    clean_host = hostname.removeprefix("www.").split("/")[0]
    if "." not in clean_host:
        raise _sw_http_error(status_code=422, detail="Enter a valid website domain.")
    brand_slug = clean_host.split(".")[0].replace("-", " ").replace("_", " ").strip()
    brand_name = " ".join((part.capitalize() for part in brand_slug.split())) or "Brand"
    handle = clean_host.split(".")[0].replace("-", "").replace("_", "")
    normalized_url = f"{parsed.scheme or 'https'}://{clean_host}"
    return (clean_host, brand_name, handle, normalized_url)


def _extract_page_content(html: str) -> dict[str, str]:
    title = _extract_meta(html, ["og:title", "twitter:title"]) or _extract_title(html)
    h1 = _extract_first_tag(html, "h1")
    description = _extract_meta(html, ["description", "og:description", "twitter:description"]) or _extract_first_tag(
        html, "p"
    )
    logo = _extract_meta(html, ["og:image", "twitter:image"]) or _extract_link_href(
        html, ["apple-touch-icon", "icon", "shortcut icon"]
    )
    return {"title": title, "h1": h1, "description": description, "logo": logo}


def _build_profile_from_website(website_url: str) -> dict[str, Any]:
    clean_host, brand_name, handle, normalized_url = _parse_website_host(website_url)
    html = _fetch_html(normalized_url)
    content = _extract_page_content(html) if html else {"title": "", "h1": "", "description": "", "logo": ""}
    extracted_title = content["title"]
    extracted_h1 = content["h1"]
    extracted_description = content["description"]
    raw_logo_url = content["logo"]
    keywords = (
        _extract_keywords_from_html(html, brand_name, clean_host) if html else [brand_name.lower()] + _DEFAULT_KEYWORDS
    )
    detected_industry = _detect_industry(keywords)
    headline = extracted_title or extracted_h1 or f"{brand_name} Official Website"
    summary = (
        extracted_description
        or f"{brand_name} builds a strong digital presence across social media and content channels."
    )
    description = f"Overview: {headline}.\n\nDescription: {summary}\n\nWebsite: {normalized_url}"[:780]
    hashtags = [f"#{item.replace(' ', '')}" for item in keywords[:4] if item]
    if f"#{handle}" not in hashtags:
        hashtags.insert(0, f"#{handle}")
    hashtags = hashtags[:6]
    logo_url = urljoin(normalized_url, raw_logo_url) if raw_logo_url else None
    return {
        "business_name": brand_name,
        "website": normalized_url,
        "logo_url": logo_url,
        "description": description,
        "industry": detected_industry,
        "tone": "professional",
        "keywords": keywords,
        "hashtags": hashtags,
        "fetched": bool(html),
    }


def _sw_strip_html(value: str) -> str:
    return unescape(re.sub("<[^>]*?>", " ", value)).strip()


def _sw_fetch_brand_from_website(st: _SocialWorkspaceState, website_url: str, tenant_id: str) -> dict[str, Any]:
    generated = _build_profile_from_website(website_url)
    with st.lock:
        profile = next((item for item in st.brand_profiles if item.get("tenant_id") == tenant_id), None)
        if profile is None:
            profile = {"id": len(st.brand_profiles) + 1, "tenant_id": tenant_id}
            st.brand_profiles.append(profile)
        profile.update(
            {
                "business_name": generated["business_name"],
                "industry": generated["industry"],
                "website": generated["website"],
                "logo_url": generated.get("logo_url"),
                "logo_dark_url": profile.get("logo_dark_url"),
                "description": generated["description"],
                "tone": generated["tone"],
                "keywords": generated["keywords"],
                "hashtags": generated["hashtags"],
                "timezone": profile.get("timezone", "UTC"),
                "ethnicity": profile.get("ethnicity"),
                "voiceover": profile.get("voiceover"),
                "avatar_profile": _normalize_avatar_profile(profile.get("avatar_profile")),
                "voiceover_engine": _normalize_voiceover_engine(profile.get("voiceover_engine")),
                "ugc_template_profile": _normalize_ugc_template_profile(profile.get("ugc_template_profile")),
                "brand_colors": profile.get("brand_colors", ["#f8fafc", "#84cc16", "#93c5fd"]),
                "title_font_family": profile.get("title_font_family", DEFAULT_FONT_FAMILY),
                "subtitle_font_family": profile.get("subtitle_font_family", DEFAULT_FONT_FAMILY),
                "title_font_weight": profile.get("title_font_weight", "Regular"),
                "subtitle_font_weight": profile.get("subtitle_font_weight", "Regular"),
                "title_case_type": profile.get("title_case_type", "Auto"),
                "subtitle_case_type": profile.get("subtitle_case_type", "Auto"),
                "use_custom_font_title": bool(profile.get("use_custom_font_title", False)),
                "use_custom_font_subtitle": bool(profile.get("use_custom_font_subtitle", False)),
                "custom_font_title": profile.get("custom_font_title"),
                "custom_font_subtitle": profile.get("custom_font_subtitle"),
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
        updated = profile.copy()
    _sw_save_profile_to_db(st, updated)
    _sw_audit(st, tenant_id, "social_brand_profile_fetched_from_website", updated["id"])
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "fetched": bool(generated.get("fetched")),
        "source": "public-web-profile",
        "brand_profile": updated,
    }
