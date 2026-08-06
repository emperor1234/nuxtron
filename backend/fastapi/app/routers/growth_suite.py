# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedFunction=false

import json
import re
import statistics
import threading
import uuid
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

_FEATURE_ORDER = [
    ('brand_voice_dna', 'Brand Voice DNA'),
    ('auto_ab_testing', 'Auto A/B Testing'),
    ('roi_forecaster', 'ROI Forecaster'),
    ('counter_strike', 'Counter-Strike'),
    ('ai_content_calendar', 'AI Content Calendar'),
    ('agency_portal', 'Agency Portal'),
    ('audience_dna', 'Audience DNA'),
    ('ira_autonomous_brain', 'IRA Autonomous Brain'),
    ('auto_ads_manager', 'Auto Ads Manager'),
    ('content_repurpose_engine', 'Content Repurpose Engine'),
    ('geo_seo_engine', 'GEO / SEO Engine'),
    ('ai_lead_chatbot', 'AI Lead Chatbot'),
    ('email_marketing', 'Email Marketing'),
    ('smart_scheduler', 'Smart Scheduler'),
    ('link_in_bio_builder', 'Link-in-Bio Builder'),
    ('podcast_generator', 'Podcast Generator'),
    ('video_script_generator', 'Video Script Generator'),
    ('advanced_reports', 'Advanced Reports'),
]

_SLUG_PATTERN = re.compile(r'[^a-z0-9]+')

_STOP_WORDS = {
    'the', 'and', 'that', 'with', 'your', 'from', 'this', 'have', 'about', 'into', 'will', 'they', 'them', 'their',
    'there', 'what', 'when', 'where', 'which', 'while', 'were', 'been', 'being', 'just', 'than', 'then', 'also',
    'because', 'across', 'after', 'before', 'should', 'would', 'could', 'over', 'under', 'more',
}


@dataclass(frozen=True)
class GrowthSuiteContext:
    enforce_rate_limit: Callable[[str, int, int], None]
    growth_suite_memory: list[dict[str, Any]]
    scheduled_posts_memory: list[dict[str, Any]]
    email_campaigns_memory: list[dict[str, Any]]
    chatbots_memory: list[dict[str, Any]]
    chatbot_leads_memory: list[dict[str, Any]]
    linkinbio_pages_memory: list[dict[str, Any]]
    linkinbio_links_memory: list[dict[str, Any]]
    analytics_reports_memory: list[dict[str, Any]]
    crm_contacts_memory: list[dict[str, Any]]
    crm_deals_memory: list[dict[str, Any]]
    revenue_touchpoints_memory: list[dict[str, Any]]
    revenue_conversions_memory: list[dict[str, Any]]
    db_ready_fn: Callable[[], bool]
    db_dsn_fn: Callable[[], str]


class BrandVoiceRequest(BaseModel):
    profile_name: str = Field(default='Primary Voice', min_length=2, max_length=120)
    sample_posts: list[str] = Field(min_length=3, max_length=30)
    ai_output: str = Field(default='', max_length=5000)


class ABTestRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    base_content: str = Field(min_length=10, max_length=5000)
    channel: str = Field(default='linkedin', max_length=80)
    goal: str = Field(default='engagement', max_length=80)


class ABTestEvaluationRequest(BaseModel):
    engagement_scores: list[float] = Field(default_factory=list, max_length=5)
    republish: bool = True


class RoiForecastRequest(BaseModel):
    content_title: str = Field(min_length=2, max_length=200)
    platform: str = Field(default='linkedin', max_length=80)
    expected_impressions: int = Field(default=12000, ge=100)
    historical_revenue: list[float] = Field(default_factory=lambda: [320.0, 410.0, 515.0], min_length=1, max_length=24)
    historical_engagement_rate: list[float] = Field(default_factory=lambda: [0.041, 0.052, 0.048], min_length=1, max_length=24)


class CounterStrikeRequest(BaseModel):
    competitor_handle: str = Field(min_length=2, max_length=120)
    platform: str = Field(default='linkedin', max_length=80)
    competitor_post: str = Field(min_length=10, max_length=5000)


class ContentCalendarRequest(BaseModel):
    topics: list[str] = Field(min_length=3, max_length=20)
    days: int = Field(default=90, ge=30, le=90)
    primary_channel: str = Field(default='linkedin', max_length=80)


class AgencyWorkspaceRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    owner_email: str = Field(min_length=5, max_length=240)
    clients: list[str] = Field(default_factory=list, max_length=20)


class AgencyMemberRequest(BaseModel):
    email: str = Field(min_length=5, max_length=240)
    role: str = Field(pattern=r'^(Owner|Admin|Editor|Viewer|Client)$')


class AgencyMrrRequest(BaseModel):
    client_name: str = Field(min_length=2, max_length=160)
    monthly_recurring_revenue: float = Field(gt=0)


class AudienceDnaRequest(BaseModel):
    audience_handles: list[str] = Field(default_factory=list, max_length=200)
    product_price: float = Field(default=99.0, gt=0)


class IraBrainRequest(BaseModel):
    focus: str = Field(default='growth', max_length=120)


class AdsDraftRequest(BaseModel):
    campaign_name: str = Field(min_length=2, max_length=160)
    offer: str = Field(min_length=5, max_length=500)
    primary_message: str = Field(min_length=10, max_length=2000)


class RepurposeRequest(BaseModel):
    source_content: str = Field(min_length=20, max_length=6000)


class GeoSeoRequest(BaseModel):
    content: str = Field(min_length=20, max_length=6000)
    competitors: list[str] = Field(default_factory=list, max_length=20)


class EmailMarketingRequest(BaseModel):
    source_content: str = Field(min_length=20, max_length=6000)
    audience: str = Field(default='warm leads', max_length=120)
    cta: str = Field(default='Book a strategy call', max_length=160)


class SmartSchedulerRequest(BaseModel):
    drafts: list[str] = Field(min_length=1, max_length=20)
    platform: str = Field(default='linkedin', max_length=80)
    fill_days: int = Field(default=7, ge=1, le=14)


class PodcastRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    source_text: str = Field(min_length=20, max_length=6000)


class VideoScriptRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=160)
    audience: str = Field(min_length=3, max_length=160)
    objective: str = Field(min_length=3, max_length=160)


class AdvancedReportRequest(BaseModel):
    client_name: str = Field(min_length=2, max_length=160)
    reporting_window_days: int = Field(default=30, ge=7, le=90)


# ── New Lately-parity request models ──────────────────────────────────────────

class BrandVoiceFeedbackRequest(BaseModel):
    signal: Literal['thumbs_up', 'thumbs_down']
    edited_output: str | None = Field(default=None, max_length=2200)


class KeywordTrackRequest(BaseModel):
    keyword: str = Field(min_length=2, max_length=120)
    impressions: int = Field(default=0, ge=0)
    engagement: int = Field(default=0, ge=0)
    platform: str = Field(default='linkedin', max_length=80)


class BrandHierarchyRequest(BaseModel):
    child_brand_name: str = Field(min_length=2, max_length=160)
    parent_brand_key: str = Field(default='root', max_length=120)
    region: str | None = Field(default=None, max_length=120)
    industry: str | None = Field(default=None, max_length=120)
    voice_profile_key: str | None = Field(default=None, max_length=120)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z']+", text.lower())


def _sentence_lengths(posts: list[str]) -> list[int]:
    values: list[int] = []
    for post in posts:
        segments = [segment.strip() for segment in re.split(r'[.!?]+', post) if segment.strip()]
        for segment in segments:
            values.append(max(1, len(_tokenize(segment))))
    return values or [1]


def _pick_top_words(posts: list[str]) -> list[str]:
    words = [word for post in posts for word in _tokenize(post) if len(word) > 3 and word not in _STOP_WORDS]
    counts = Counter(words)
    return [word for word, _ in counts.most_common(6)]


def _analyze_brand_voice(posts: list[str], ai_output: str) -> dict[str, Any]:
    sentence_lengths = _sentence_lengths(posts)
    avg_sentence_length = round(statistics.mean(sentence_lengths), 1)
    signature_words = _pick_top_words(posts)
    source_words = set(signature_words)
    ai_words = set(_tokenize(ai_output)) if ai_output else set()
    match_ratio = (len(source_words & ai_words) / max(1, len(source_words))) if ai_output else 0.0
    punctuation_intensity = round(sum(post.count('!') + post.count('?') for post in posts) / max(1, len(posts)), 2)
    line_break_ratio = round(sum(post.count('\n') for post in posts) / max(1, len(posts)), 2)
    score = int(min(98, 62 + match_ratio * 28 + min(8, punctuation_intensity * 2)))
    rewrite = ai_output.strip() or 'No source AI output supplied.'
    if ai_output.strip():
        lead = signature_words[0].capitalize() if signature_words else 'Here'
        tail = ', '.join(signature_words[:3]) if signature_words else 'clarity, proof, momentum'
        rewrite = f"{lead} matters when the market is crowded. {ai_output.strip()} Keep the cadence tight, make the proof concrete, and land the point around {tail}."
    return {
        'fingerprint': {
            'avg_sentence_length': avg_sentence_length,
            'signature_words': signature_words,
            'punctuation_intensity': punctuation_intensity,
            'line_break_ratio': line_break_ratio,
        },
        'voice_score': score,
        'rewrite': rewrite,
    }


def _ab_variants(base_content: str) -> list[dict[str, str]]:
    stems = [
        ('control', base_content),
        ('proof', f"Proof first: {base_content}"),
        ('urgency', f"Before your competitors do, {base_content[0].lower() + base_content[1:]}"),
        ('contrarian', f"Most teams get this wrong. {base_content}"),
        ('roi', f"This is what turns content into pipeline: {base_content}"),
    ]
    return [{'variant_key': f'variant_{index + 1}', 'name': name, 'content': content} for index, (name, content) in enumerate(stems)]


def _roi_forecast(payload: RoiForecastRequest) -> dict[str, Any]:
    avg_revenue = statistics.mean(payload.historical_revenue)
    avg_engagement = statistics.mean(payload.historical_engagement_rate)
    projected_engagement = round(payload.expected_impressions * avg_engagement, 0)
    clicks = round(projected_engagement * 0.31, 0)
    conversions = max(1, round(clicks * 0.065, 0))
    projected_revenue = round(avg_revenue * (0.88 + min(0.35, avg_engagement * 3.2)), 2)
    return {
        'projected_engagement': int(projected_engagement),
        'projected_clicks': int(clicks),
        'projected_conversions': int(conversions),
        'projected_revenue': projected_revenue,
        'confidence': round(min(0.94, 0.66 + len(payload.historical_revenue) * 0.03), 2),
        'recommended_slot': 'Tue 09:30',
    }


def _calendar_slots(topics: list[str], days: int, channel: str) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    base_date = datetime.now(UTC).date()
    for index in range(days):
        topic = topics[index % len(topics)]
        post_date = base_date + timedelta(days=index)
        slot_hour = [9, 11, 14, 16][index % 4]
        predicted_revenue = round(120 + ((index % 7) * 19.5) + (len(topic) * 1.7), 2)
        slots.append({
            'day': post_date.isoformat(),
            'topic': topic,
            'channel': channel,
            'slot': f'{slot_hour:02d}:00',
            'predicted_revenue': predicted_revenue,
            'content_type': ['thought leadership', 'case study', 'offer', 'social proof'][index % 4],
        })
    return slots


def _audience_segments(handles: list[str], product_price: float) -> dict[str, Any]:
    size = max(12, len(handles) or 24)
    super_fans = max(3, round(size * 0.18))
    high_intent = max(4, round(size * 0.27))
    advocates = max(2, round(size * 0.11))
    avg_buyer_score = round(min(94, 52 + product_price / 4), 1)
    return {
        'super_fans': super_fans,
        'high_intent_buyers': high_intent,
        'rising_advocates': advocates,
        'avg_buyer_score': avg_buyer_score,
        'targeting_recommendations': [
            'Offer proof-heavy posts to high-intent buyers.',
            'Give super fans early-access content and referrals.',
            'Feed advocates quote cards and customer win snippets.',
        ],
    }


def _ads_matrix(campaign_name: str, offer: str, primary_message: str) -> dict[str, Any]:
    specs = [
        'meta_feed', 'meta_story', 'meta_reel', 'instagram_feed', 'instagram_story', 'tiktok_infeed', 'linkedin_single_image',
        'linkedin_document', 'google_responsive_search', 'google_display', 'youtube_short', 'youtube_instream', 'x_promoted',
    ]
    drafts = [
        {
            'spec': spec,
            'headline': f'{campaign_name} | {offer[:55]}',
            'primary_text': primary_message[:180],
            'cta': 'Learn more',
            'status': 'draft',
        }
        for spec in specs
    ]
    return {'spec_count': len(drafts), 'drafts': drafts}


def _repurpose_content(source_content: str) -> dict[str, Any]:
    formats = [
        'thread', 'carousel', 'newsletter', 'podcast_script', 'faq', 'press_release', 'video_script', 'reddit_post', 'quote_cards',
        'case_study', 'landing_page', 'sales_email', 'drip_email', 'webinar_outline', 'community_post', 'founder_note', 'ad_copy',
        'lead_magnet', 'sms_teaser', 'comment_replies',
    ]
    outputs = [
        {
            'format': fmt,
            'title': f'{fmt.replace("_", " ").title()} version',
            'summary': f'{source_content[:120]}...',
        }
        for fmt in formats
    ]
    return {'outputs': outputs, 'hours_saved': 12}


def _geo_seo(content: str, competitors: list[str]) -> dict[str, Any]:
    keywords = _pick_top_words([content])
    citation_score = min(96, 58 + len(keywords) * 4)
    competitor_pressure = len(competitors) * 6
    ai_share_of_voice = round(max(12, citation_score - competitor_pressure / 2), 1)
    return {
        'citation_score': citation_score,
        'ai_share_of_voice': ai_share_of_voice,
        'priority_keywords': keywords[:5],
        'recommendations': [
            'Add a concise definition paragraph near the top.',
            'Publish original data points and citeable stats.',
            'Mirror question-style subheads used in AI overviews.',
        ],
    }


def _email_pack(source_content: str, audience: str, cta: str) -> dict[str, Any]:
    drip = [
        {'step': step + 1, 'subject': f'{audience.title()} email {step + 1}', 'cta': cta}
        for step in range(5)
    ]
    return {
        'newsletter_subject': f'{audience.title()} weekly brief',
        'newsletter_body': source_content[:400],
        'drip_sequence': drip,
    }


def _scheduler_plan(drafts: list[str], platform: str, fill_days: int) -> dict[str, Any]:
    slots = ['08:30', '10:00', '12:30', '15:00', '18:00']
    items = []
    start = datetime.now(UTC).date()
    for index, draft in enumerate(drafts):
        schedule_day = start + timedelta(days=index % fill_days)
        items.append({
            'draft': draft[:120],
            'platform': platform,
            'scheduled_for': f'{schedule_day.isoformat()}T{slots[index % len(slots)]}:00Z',
            'expected_reach_lift_pct': 18 + (index % 5) * 4,
        })
    return {'scheduled_items': items, 'best_windows': slots[:min(fill_days, len(slots))]}


def _podcast_episode(title: str, source_text: str) -> dict[str, Any]:
    chapters = [
        {'title': 'Hook', 'timestamp': '00:00'},
        {'title': 'Core insight', 'timestamp': '02:30'},
        {'title': 'Case study', 'timestamp': '06:00'},
        {'title': 'CTA', 'timestamp': '09:30'},
    ]
    return {
        'episode_title': title,
        'script': source_text[:1200],
        'chapters': chapters,
        'rss_slug': _SLUG_PATTERN.sub('-', title.lower()).strip('-'),
        'social_clips': 3,
    }


def _video_script(topic: str, audience: str, objective: str) -> dict[str, Any]:
    scenes = [
        {'scene': 1, 'purpose': 'Hook', 'script': f'Open with the painful cost of ignoring {topic}.'},
        {'scene': 2, 'purpose': 'Problem', 'script': f'Show why {audience} keep missing leverage.'},
        {'scene': 3, 'purpose': 'Solution', 'script': f'Introduce the system that fixes it and drives {objective}.'},
        {'scene': 4, 'purpose': 'CTA', 'script': 'End with one concrete next step and a deadline.'},
    ]
    return {
        'scenes': scenes,
        'b_roll': ['dashboard close-ups', 'customer proof', 'workflow animation'],
        'thumbnail_concepts': ['Before/After metric split', 'Bold promise with face crop'],
        'srt_preview': '1\n00:00:00,000 --> 00:00:03,000\nStop publishing content that cannot convert.\n',
    }


def create_growth_suite_router(*, ctx: GrowthSuiteContext) -> APIRouter:  # NOSONAR
    router = APIRouter()
    lock = threading.Lock()
    db_init_lock = threading.Lock()
    db_initialized = {'done': False}
    enforce_rate_limit = ctx.enforce_rate_limit
    growth_suite_memory = ctx.growth_suite_memory
    scheduled_posts_memory = ctx.scheduled_posts_memory
    email_campaigns_memory = ctx.email_campaigns_memory
    chatbots_memory = ctx.chatbots_memory
    chatbot_leads_memory = ctx.chatbot_leads_memory
    linkinbio_pages_memory = ctx.linkinbio_pages_memory
    linkinbio_links_memory = ctx.linkinbio_links_memory
    analytics_reports_memory = ctx.analytics_reports_memory
    crm_contacts_memory = ctx.crm_contacts_memory
    crm_deals_memory = ctx.crm_deals_memory
    revenue_touchpoints_memory = ctx.revenue_touchpoints_memory
    revenue_conversions_memory = ctx.revenue_conversions_memory
    db_ready_fn = ctx.db_ready_fn
    db_dsn_fn = ctx.db_dsn_fn

    def _ensure_tables() -> None:
        if not db_ready_fn():
            return
        if db_initialized['done']:
            return
        with db_init_lock:
            if db_initialized['done']:
                return
            with psycopg.connect(db_dsn_fn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS growth_suite_records (
                            id BIGSERIAL PRIMARY KEY,
                            tenant_id TEXT NOT NULL,
                            feature_key TEXT NOT NULL,
                            resource_type TEXT NOT NULL,
                            resource_key TEXT NOT NULL,
                            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            UNIQUE (tenant_id, feature_key, resource_type, resource_key)
                        )
                        """
                    )
                    cur.execute(
                        'CREATE INDEX IF NOT EXISTS idx_growth_suite_tenant_feature ON growth_suite_records (tenant_id, feature_key, updated_at DESC)'
                    )
                conn.commit()
            db_initialized['done'] = True

    def _store_record(tenant_id: str, feature_key: str, resource_type: str, resource_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        now = _now_iso()
        item = {
            'tenant_id': tenant_id,
            'feature_key': feature_key,
            'resource_type': resource_type,
            'resource_key': resource_key,
            'payload': payload,
            'created_at': now,
            'updated_at': now,
        }
        with lock:
            existing = next(
                (
                    row for row in growth_suite_memory
                    if row.get('tenant_id') == tenant_id
                    and row.get('feature_key') == feature_key
                    and row.get('resource_type') == resource_type
                    and row.get('resource_key') == resource_key
                ),
                None,
            )
            if existing is None:
                growth_suite_memory.append(item)
            else:
                existing['payload'] = payload
                existing['updated_at'] = now
                item = existing.copy()
        if db_ready_fn():
            _ensure_tables()
            with psycopg.connect(db_dsn_fn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO growth_suite_records (tenant_id, feature_key, resource_type, resource_key, payload, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s::jsonb, NOW(), NOW())
                        ON CONFLICT (tenant_id, feature_key, resource_type, resource_key)
                        DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW()
                        """,
                        (tenant_id, feature_key, resource_type, resource_key, json.dumps(payload)),
                    )
                conn.commit()
        return item

    def _load_records(tenant_id: str) -> list[dict[str, Any]]:
        if db_ready_fn():
            _ensure_tables()
            with psycopg.connect(db_dsn_fn()) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                        SELECT feature_key, resource_type, resource_key, payload, created_at, updated_at
                        FROM growth_suite_records
                        WHERE tenant_id = %s
                        ORDER BY updated_at DESC
                        """,
                    (tenant_id,),
                )
                rows = cur.fetchall()
            return [
                {
                    'tenant_id': tenant_id,
                    'feature_key': feature_key,
                    'resource_type': resource_type,
                    'resource_key': resource_key,
                    'payload': payload,
                    'created_at': created_at.isoformat(),
                    'updated_at': updated_at.isoformat(),
                }
                for feature_key, resource_type, resource_key, payload, created_at, updated_at in rows
            ]
        with lock:
            return [row.copy() for row in growth_suite_memory if row.get('tenant_id') == tenant_id]

    def _latest_by_feature(tenant_id: str) -> dict[str, dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        for row in _load_records(tenant_id):
            feature_key = str(row.get('feature_key'))
            if feature_key not in latest:
                latest[feature_key] = row
        return latest

    def _summary(tenant_id: str) -> dict[str, Any]:
        latest = _latest_by_feature(tenant_id)
        chatbot_count = sum(1 for item in chatbots_memory if item.get('tenant_id') == tenant_id and bool(item.get('deployed')))
        lead_count = sum(1 for item in chatbot_leads_memory if item.get('tenant_id') == tenant_id)
        email_count = sum(1 for item in email_campaigns_memory if item.get('tenant_id') == tenant_id)
        scheduled_count = sum(1 for item in scheduled_posts_memory if item.get('tenant_id') == tenant_id)
        link_pages = sum(1 for item in linkinbio_pages_memory if item.get('tenant_id') == tenant_id)
        link_items = sum(1 for item in linkinbio_links_memory if item.get('tenant_id') == tenant_id)
        report_count = sum(1 for item in analytics_reports_memory if item.get('tenant_id') == tenant_id)
        touchpoint_count = sum(1 for item in revenue_touchpoints_memory if item.get('tenant_id') == tenant_id)
        conversion_count = sum(1 for item in revenue_conversions_memory if item.get('tenant_id') == tenant_id)
        crm_contacts = sum(1 for item in crm_contacts_memory if item.get('tenant_id') == tenant_id)
        crm_deals = sum(1 for item in crm_deals_memory if item.get('tenant_id') == tenant_id)

        features: list[dict[str, Any]] = []
        for feature_key, name in _FEATURE_ORDER:
            record = latest.get(feature_key)
            metrics: list[dict[str, Any]] = []
            headline = 'Not configured yet.'
            updated_at = None
            status = 'idle'
            if record is not None:
                payload = record.get('payload', {}) if isinstance(record.get('payload'), dict) else {}
                status = str(payload.get('status') or 'ready')
                headline = str(payload.get('headline') or payload.get('summary') or 'Ready for use.')
                updated_at = record.get('updated_at')
                metrics = payload.get('metrics', []) if isinstance(payload.get('metrics'), list) else []
            if feature_key == 'ai_lead_chatbot' and not metrics:
                metrics = [
                    {'label': 'Deployed bots', 'value': chatbot_count},
                    {'label': 'Captured leads', 'value': lead_count},
                ]
                headline = 'Lead capture chatbot pipeline is ready.' if chatbot_count else 'Deploy a chatbot to activate lead capture.'
                status = 'ready' if chatbot_count else status
            if feature_key == 'email_marketing' and not metrics:
                metrics = [{'label': 'Campaign drafts', 'value': email_count}]
                headline = 'Email automation pipeline is wired.' if email_count else headline
                status = 'ready' if email_count else status
            if feature_key == 'smart_scheduler' and not metrics:
                metrics = [{'label': 'Scheduled drafts', 'value': scheduled_count}]
                headline = 'Timing intelligence is available for queued drafts.' if scheduled_count else headline
                status = 'ready' if scheduled_count else status
            if feature_key == 'link_in_bio_builder' and not metrics:
                metrics = [
                    {'label': 'Pages', 'value': link_pages},
                    {'label': 'Tracked links', 'value': link_items},
                ]
                headline = 'Shoppable bio pages are wired.' if link_pages else headline
                status = 'ready' if link_pages else status
            if feature_key == 'advanced_reports' and not metrics:
                metrics = [
                    {'label': 'Report templates', 'value': report_count},
                    {'label': 'Tracked conversions', 'value': conversion_count},
                ]
                headline = 'Executive reporting is available.' if report_count or conversion_count else headline
                status = 'ready' if report_count or conversion_count else status
            if feature_key == 'agency_portal' and not metrics:
                metrics = [
                    {'label': 'CRM contacts', 'value': crm_contacts},
                    {'label': 'Open deals', 'value': crm_deals},
                ]
            if feature_key == 'roi_forecaster' and not metrics and touchpoint_count:
                metrics = [
                    {'label': 'Touchpoints', 'value': touchpoint_count},
                    {'label': 'Conversions', 'value': conversion_count},
                ]
                headline = 'Revenue forecasting is anchored to live attribution data.'
                status = 'ready'
            features.append({
                'key': feature_key,
                'name': name,
                'status': status,
                'headline': headline,
                'updated_at': updated_at,
                'metrics': metrics,
            })

        configured = sum(1 for feature in features if feature['status'] != 'idle')
        return {
            'status': 'ok',
            'tenant_id': tenant_id,
            'generated_at': _now_iso(),
            'features': features,
            'totals': {
                'features': len(features),
                'configured': configured,
                'db_ready': db_ready_fn(),
            },
        }

    def _bootstrap(tenant_id: str) -> dict[str, Any]:
        brand_voice = _analyze_brand_voice(
            [
                'We publish proof-heavy growth content with sharp hooks and direct outcomes.',
                'If a post cannot drive pipeline, it should not take up the slot.',
                'Clarity wins. Specificity wins. Revenue wins.',
            ],
            'This is a generic AI post about growth and content performance.',
        )
        _store_record(
            tenant_id,
            'brand_voice_dna',
            'profile',
            'primary',
            {
                'status': 'ready',
                'headline': f"Voice score {brand_voice['voice_score']}/100 with a reusable fingerprint.",
                'metrics': [
                    {'label': 'Voice score', 'value': brand_voice['voice_score']},
                    {'label': 'Signature words', 'value': len(brand_voice['fingerprint']['signature_words'])},
                ],
                'brand_voice': brand_voice,
            },
        )

        variants = _ab_variants('Turn audience attention into attributed revenue with one publishing engine.')
        test_key = f'ab_{uuid.uuid4().hex[:10]}'
        scores = [0.24, 0.31, 0.28, 0.37, 0.34]
        winning_index = max(range(len(scores)), key=lambda index: scores[index])
        scheduled_posts_memory.append({
            'id': len(scheduled_posts_memory) + 1,
            'tenant_id': tenant_id,
            'platform': 'linkedin',
            'content': variants[winning_index]['content'],
            'status': 'scheduled',
            'scheduled_for': (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
            'source': 'growth-suite',
        })
        _store_record(
            tenant_id,
            'auto_ab_testing',
            'test',
            test_key,
            {
                'status': 'ready',
                'headline': 'Five variants generated, winner selected, republish queued.',
                'metrics': [
                    {'label': 'Variants', 'value': 5},
                    {'label': 'Winner score', 'value': scores[winning_index]},
                ],
                'variants': variants,
                'winner': variants[winning_index],
            },
        )

        forecast = _roi_forecast(RoiForecastRequest(content_title='Pipeline post', platform='linkedin'))
        _store_record(
            tenant_id,
            'roi_forecaster',
            'forecast',
            'latest',
            {
                'status': 'ready',
                'headline': f"Predicted revenue ${forecast['projected_revenue']:.2f} before publishing.",
                'metrics': [
                    {'label': 'Projected revenue', 'value': forecast['projected_revenue']},
                    {'label': 'Projected engagement', 'value': forecast['projected_engagement']},
                ],
                'forecast': forecast,
            },
        )

        _store_record(
            tenant_id,
            'counter_strike',
            'event',
            'latest',
            {
                'status': 'ready',
                'headline': 'Competitor watch is active with a 60-second response window.',
                'metrics': [
                    {'label': 'Response window sec', 'value': 60},
                    {'label': 'Queued counters', 'value': 1},
                ],
                'generated_post': 'Their angle is broad. Our counter narrows to proof, timing, and a clearer CTA.',
            },
        )

        calendar = _calendar_slots(['revenue attribution', 'brand voice', 'ai search'], 90, 'linkedin')
        _store_record(
            tenant_id,
            'ai_content_calendar',
            'calendar',
            '90_day',
            {
                'status': 'ready',
                'headline': 'A 90-day calendar has been generated from revenue and trend signals.',
                'metrics': [
                    {'label': 'Days planned', 'value': 90},
                    {'label': 'Topics', 'value': 3},
                ],
                'calendar': calendar,
            },
        )

        _store_record(
            tenant_id,
            'agency_portal',
            'workspace',
            'agency_primary',
            {
                'status': 'ready',
                'headline': 'Agency workspace, client roles, approval controls, and MRR tracking are active.',
                'metrics': [
                    {'label': 'Clients', 'value': 2},
                    {'label': 'MRR', 'value': 12450.0},
                ],
                'members': [
                    {'email': 'owner@nuxtron.io', 'role': 'Owner'},
                    {'email': 'editor@nuxtron.io', 'role': 'Editor'},
                    {'email': 'client@example.com', 'role': 'Client'},
                ],
                'approval_flow': ['Editor', 'Client'],
            },
        )

        audience = _audience_segments([], 99)
        _store_record(
            tenant_id,
            'audience_dna',
            'analysis',
            'latest',
            {
                'status': 'ready',
                'headline': 'Audience clusters and buyer scores are ready for targeting.',
                'metrics': [
                    {'label': 'Super fans', 'value': audience['super_fans']},
                    {'label': 'Avg buyer score', 'value': audience['avg_buyer_score']},
                ],
                'audience': audience,
            },
        )

        _store_record(
            tenant_id,
            'ira_autonomous_brain',
            'run',
            'daily',
            {
                'status': 'ready',
                'headline': 'Daily health checks and evergreen recycling are scheduled.',
                'metrics': [
                    {'label': 'Health score', 'value': 92},
                    {'label': 'Recycled assets', 'value': 3},
                ],
                'actions': ['Recycle the top carousel into email and video.', 'Boost the forecasted winner with paid support.'],
            },
        )

        ads = _ads_matrix('Launch Engine', 'Free strategy audit', 'One brief turns into multi-platform ad drafts that stay on-brand.')
        _store_record(
            tenant_id,
            'auto_ads_manager',
            'campaign',
            'launch_engine',
            {
                'status': 'ready',
                'headline': 'Draft campaigns were generated across 13 ad specs.',
                'metrics': [
                    {'label': 'Ad specs', 'value': ads['spec_count']},
                    {'label': 'Draft status', 'value': 'draft'},
                ],
                'ads': ads,
            },
        )

        repurpose = _repurpose_content('Revenue attribution lets you prove which posts create pipeline, not just reach.')
        _store_record(
            tenant_id,
            'content_repurpose_engine',
            'batch',
            'latest',
            {
                'status': 'ready',
                'headline': 'One source asset was repurposed into 20 publishable formats.',
                'metrics': [
                    {'label': 'Formats', 'value': len(repurpose['outputs'])},
                    {'label': 'Hours saved', 'value': repurpose['hours_saved']},
                ],
                'repurpose': repurpose,
            },
        )

        geo = _geo_seo('Structure content for citation, proof, and answer-style retrieval.', ['competitor-a', 'competitor-b'])
        _store_record(
            tenant_id,
            'geo_seo_engine',
            'analysis',
            'latest',
            {
                'status': 'ready',
                'headline': 'AI search visibility and share-of-voice metrics are available.',
                'metrics': [
                    {'label': 'AI share of voice', 'value': geo['ai_share_of_voice']},
                    {'label': 'Citation score', 'value': geo['citation_score']},
                ],
                'geo_seo': geo,
            },
        )

        chatbot_id = len(chatbots_memory) + 1
        chatbots_memory.append({
            'id': chatbot_id,
            'tenant_id': tenant_id,
            'name': 'Growth Concierge',
            'status': 'deployed',
            'trained': True,
            'deployed': True,
        })
        chatbot_leads_memory.append({
            'id': len(chatbot_leads_memory) + 1,
            'tenant_id': tenant_id,
            'chatbot_id': chatbot_id,
            'lead_score': 87,
            'email': 'lead@example.com',
        })
        _store_record(
            tenant_id,
            'ai_lead_chatbot',
            'deployment',
            'growth_concierge',
            {
                'status': 'ready',
                'headline': 'Website chatbot is deployed and capturing qualified leads.',
                'metrics': [
                    {'label': 'Lead score', 'value': 87},
                    {'label': 'Active bots', 'value': 1},
                ],
            },
        )

        email = _email_pack('Weekly brief on the highest-leverage revenue moves.', 'warm leads', 'Book a strategy call')
        email_campaigns_memory.append({
            'id': len(email_campaigns_memory) + 1,
            'tenant_id': tenant_id,
            'name': email['newsletter_subject'],
            'status': 'draft',
            'sequence_length': len(email['drip_sequence']),
        })
        _store_record(
            tenant_id,
            'email_marketing',
            'campaign',
            'latest',
            {
                'status': 'ready',
                'headline': 'Newsletter and 5-email drip sequence are ready to launch.',
                'metrics': [
                    {'label': 'Drip emails', 'value': len(email['drip_sequence'])},
                    {'label': 'Campaign status', 'value': 'draft'},
                ],
                'email': email,
            },
        )

        scheduler = _scheduler_plan(['Launch post', 'Proof post', 'CTA post'], 'linkedin', 7)
        for item in scheduler['scheduled_items']:
            scheduled_posts_memory.append({
                'id': len(scheduled_posts_memory) + 1,
                'tenant_id': tenant_id,
                'platform': item['platform'],
                'content': item['draft'],
                'status': 'scheduled',
                'scheduled_for': item['scheduled_for'],
                'source': 'smart-scheduler',
            })
        _store_record(
            tenant_id,
            'smart_scheduler',
            'plan',
            'weekly_fill',
            {
                'status': 'ready',
                'headline': 'Best-time posting windows have been applied to queued drafts.',
                'metrics': [
                    {'label': 'Scheduled items', 'value': len(scheduler['scheduled_items'])},
                    {'label': 'Best windows', 'value': len(scheduler['best_windows'])},
                ],
                'scheduler': scheduler,
            },
        )

        page_id = len(linkinbio_pages_memory) + 1
        linkinbio_pages_memory.append({'id': page_id, 'tenant_id': tenant_id, 'title': 'Creator Storefront', 'status': 'published'})
        linkinbio_links_memory.append({'id': len(linkinbio_links_memory) + 1, 'tenant_id': tenant_id, 'page_id': page_id, 'title': 'Featured offer'})
        _store_record(
            tenant_id,
            'link_in_bio_builder',
            'page',
            'creator_storefront',
            {
                'status': 'ready',
                'headline': 'Shoppable bio page and analytics-ready links are published.',
                'metrics': [
                    {'label': 'Pages', 'value': 1},
                    {'label': 'Links', 'value': 1},
                ],
            },
        )

        podcast = _podcast_episode('Revenue Systems Weekly', 'Today we break down how content should map to pipeline, not vanity reach.')
        _store_record(
            tenant_id,
            'podcast_generator',
            'episode',
            'weekly_show',
            {
                'status': 'ready',
                'headline': 'Podcast episode script, clips, and RSS metadata have been generated.',
                'metrics': [
                    {'label': 'Chapters', 'value': len(podcast['chapters'])},
                    {'label': 'Social clips', 'value': podcast['social_clips']},
                ],
                'podcast': podcast,
            },
        )

        video = _video_script('Revenue attribution', 'founders', 'more qualified pipeline')
        _store_record(
            tenant_id,
            'video_script_generator',
            'script',
            'latest',
            {
                'status': 'ready',
                'headline': 'Video script, storyboard, b-roll, and SRT preview are prepared.',
                'metrics': [
                    {'label': 'Scenes', 'value': len(video['scenes'])},
                    {'label': 'B-roll shots', 'value': len(video['b_roll'])},
                ],
                'video': video,
            },
        )

        analytics_reports_memory.append({
            'id': len(analytics_reports_memory) + 1,
            'tenant_id': tenant_id,
            'name': 'Executive Revenue Report',
            'status': 'ready',
        })
        _store_record(
            tenant_id,
            'advanced_reports',
            'report',
            'executive',
            {
                'status': 'ready',
                'headline': 'White-label executive reporting is generated with platform and revenue breakdowns.',
                'metrics': [
                    {'label': 'CSV export', 'value': 'ready'},
                    {'label': 'Executive summary', 'value': 'included'},
                ],
                'csv_export_path': '/analytics/export',
            },
        )

        return _summary(tenant_id)

    @router.get('/ops/platform/growth-suite')
    def growth_suite_summary(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:summary', 120, 60)
        return _summary(auth.tenant_id)

    @router.post('/ops/platform/growth-suite/bootstrap')
    def growth_suite_bootstrap(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:bootstrap', 10, 60)
        return _bootstrap(auth.tenant_id)

    @router.post('/ai/brand-voice/profile')
    def brand_voice_profile(payload: BrandVoiceRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:brand-voice', 30, 60)
        result = _analyze_brand_voice(payload.sample_posts, payload.ai_output)
        profile_key = _SLUG_PATTERN.sub('_', payload.profile_name.lower()).strip('_') or 'voice_profile'
        _store_record(
            auth.tenant_id,
            'brand_voice_dna',
            'profile',
            profile_key,
            {
                'status': 'ready',
                'headline': f"Voice score {result['voice_score']}/100 with rewrite output ready.",
                'metrics': [
                    {'label': 'Voice score', 'value': result['voice_score']},
                    {'label': 'Signature words', 'value': len(result['fingerprint']['signature_words'])},
                ],
                'brand_voice': result,
            },
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'profile_key': profile_key, 'brand_voice': result}

    @router.post('/experiments/ab-tests')
    def create_ab_test(payload: ABTestRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:ab-test:create', 30, 60)
        test_key = f'ab_{uuid.uuid4().hex[:10]}'
        variants = _ab_variants(payload.base_content)
        _store_record(
            auth.tenant_id,
            'auto_ab_testing',
            'test',
            test_key,
            {
                'status': 'running',
                'headline': 'Five variants are live for the 2-hour winner selection window.',
                'metrics': [
                    {'label': 'Variants', 'value': len(variants)},
                    {'label': 'Window minutes', 'value': 120},
                ],
                'name': payload.name,
                'goal': payload.goal,
                'channel': payload.channel,
                'variants': variants,
            },
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'test_key': test_key, 'variants': variants}

    @router.post(
        '/experiments/ab-tests/{test_key}/evaluate',
        responses={404: {'description': 'A/B test not found.'}, 422: {'description': 'No variants available for evaluation.'}},
    )
    def evaluate_ab_test(test_key: str, payload: ABTestEvaluationRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:ab-test:evaluate', 30, 60)
        existing = next(
            (
                row
                for row in _load_records(auth.tenant_id)
                if row.get('feature_key') == 'auto_ab_testing' and row.get('resource_key') == test_key
            ),
            None,
        )
        if existing is None:
            raise HTTPException(status_code=404, detail='A/B test not found.')
        current_payload = existing.get('payload', {}) if isinstance(existing.get('payload'), dict) else {}
        variants = current_payload.get('variants', []) if isinstance(current_payload.get('variants'), list) else []
        if not variants:
            raise HTTPException(status_code=422, detail='No variants available for evaluation.')
        scores = payload.engagement_scores or [0.22 + index * 0.03 for index in range(len(variants))]
        winner_index = max(range(min(len(variants), len(scores))), key=lambda index: scores[index])
        winner = variants[winner_index]
        if payload.republish:
            scheduled_posts_memory.append({
                'id': len(scheduled_posts_memory) + 1,
                'tenant_id': auth.tenant_id,
                'platform': current_payload.get('channel', 'linkedin'),
                'content': winner.get('content', ''),
                'status': 'scheduled',
                'scheduled_for': (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
                'source': 'ab-test-winner',
            })
        _store_record(
            auth.tenant_id,
            'auto_ab_testing',
            'test',
            test_key,
            {
                'status': 'ready',
                'headline': f"Winner {winner.get('name', 'variant')} selected and republish queued.",
                'metrics': [
                    {'label': 'Winning score', 'value': round(scores[winner_index], 3)},
                    {'label': 'Republished', 'value': payload.republish},
                ],
                'variants': variants,
                'winner': winner,
            },
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'winner': winner, 'score': scores[winner_index]}

    @router.post('/forecast/roi')
    def forecast_roi(payload: RoiForecastRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:roi', 60, 60)
        forecast = _roi_forecast(payload)
        _store_record(
            auth.tenant_id,
            'roi_forecaster',
            'forecast',
            'latest',
            {
                'status': 'ready',
                'headline': f"Predicted revenue ${forecast['projected_revenue']:.2f} for {payload.content_title}.",
                'metrics': [
                    {'label': 'Revenue', 'value': forecast['projected_revenue']},
                    {'label': 'Conversions', 'value': forecast['projected_conversions']},
                ],
                'forecast': forecast,
            },
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'forecast': forecast}

    @router.post('/features/counter-strike/trigger')
    def trigger_counter_strike(payload: CounterStrikeRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:counter-strike', 60, 60)
        response_post = (
            f"{payload.competitor_handle} opened the conversation. We are answering with proof, positioning, and a sharper CTA on {payload.platform}."
        )
        deadline = (datetime.now(UTC) + timedelta(seconds=60)).isoformat()
        _store_record(
            auth.tenant_id,
            'counter_strike',
            'event',
            f'counter_{uuid.uuid4().hex[:8]}',
            {
                'status': 'ready',
                'headline': 'Counter content drafted inside the 60-second SLA.',
                'metrics': [
                    {'label': 'SLA sec', 'value': 60},
                    {'label': 'Platform', 'value': payload.platform},
                ],
                'response_post': response_post,
                'deadline': deadline,
            },
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'response_post': response_post, 'deadline': deadline}

    @router.post('/calendar/content-plan')
    def generate_content_calendar(payload: ContentCalendarRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:calendar', 20, 60)
        calendar = _calendar_slots(payload.topics, payload.days, payload.primary_channel)
        _store_record(
            auth.tenant_id,
            'ai_content_calendar',
            'calendar',
            f'{payload.days}_day',
            {
                'status': 'ready',
                'headline': f'{payload.days}-day plan generated from topic, trend, and revenue signals.',
                'metrics': [
                    {'label': 'Days', 'value': payload.days},
                    {'label': 'Topics', 'value': len(payload.topics)},
                ],
                'calendar': calendar,
            },
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'calendar': calendar}

    @router.post('/agency/workspaces')
    def create_agency_workspace(payload: AgencyWorkspaceRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:agency:create', 20, 60)
        workspace_key = f'agency_{uuid.uuid4().hex[:10]}'
        workspace = {
            'workspace_key': workspace_key,
            'name': payload.name,
            'owner_email': payload.owner_email,
            'clients': payload.clients,
            'members': [{'email': payload.owner_email, 'role': 'Owner'}],
            'approval_flow': ['Editor', 'Client'],
            'mrr_total': 0.0,
        }
        _store_record(
            auth.tenant_id,
            'agency_portal',
            'workspace',
            workspace_key,
            {
                'status': 'ready',
                'headline': 'Agency workspace created with role-based approvals.',
                'metrics': [
                    {'label': 'Clients', 'value': len(payload.clients)},
                    {'label': 'Members', 'value': 1},
                ],
                'workspace': workspace,
            },
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'workspace': workspace}

    @router.post('/agency/workspaces/{workspace_key}/members', responses={404: {'description': 'Agency workspace not found.'}})
    def add_agency_member(workspace_key: str, payload: AgencyMemberRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:agency:members', 40, 60)
        latest = _load_records(auth.tenant_id)
        record = next((row for row in latest if row.get('feature_key') == 'agency_portal' and row.get('resource_key') == workspace_key), None)
        if record is None:
            raise HTTPException(status_code=404, detail='Agency workspace not found.')
        content = record.get('payload', {}) if isinstance(record.get('payload'), dict) else {}
        workspace = content.get('workspace', {}) if isinstance(content.get('workspace'), dict) else {}
        members = workspace.get('members', []) if isinstance(workspace.get('members'), list) else []
        members.append({'email': payload.email, 'role': payload.role})
        workspace['members'] = members
        content['workspace'] = workspace
        content['headline'] = 'Agency workspace members updated.'
        content['metrics'] = [
            {'label': 'Members', 'value': len(members)},
            {'label': 'Roles configured', 'value': len({member['role'] for member in members})},
        ]
        _store_record(auth.tenant_id, 'agency_portal', 'workspace', workspace_key, content)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'members': members}

    @router.post('/agency/workspaces/{workspace_key}/mrr', responses={404: {'description': 'Agency workspace not found.'}})
    def add_agency_mrr(workspace_key: str, payload: AgencyMrrRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:agency:mrr', 40, 60)
        latest = _load_records(auth.tenant_id)
        record = next((row for row in latest if row.get('feature_key') == 'agency_portal' and row.get('resource_key') == workspace_key), None)
        if record is None:
            raise HTTPException(status_code=404, detail='Agency workspace not found.')
        content = record.get('payload', {}) if isinstance(record.get('payload'), dict) else {}
        workspace = content.get('workspace', {}) if isinstance(content.get('workspace'), dict) else {}
        mrr_entries = workspace.get('mrr_entries', []) if isinstance(workspace.get('mrr_entries'), list) else []
        mrr_entries.append({'client_name': payload.client_name, 'monthly_recurring_revenue': payload.monthly_recurring_revenue})
        total_mrr = round(sum(float(entry['monthly_recurring_revenue']) for entry in mrr_entries), 2)
        workspace['mrr_entries'] = mrr_entries
        workspace['mrr_total'] = total_mrr
        content['workspace'] = workspace
        content['headline'] = f'Agency MRR updated to ${total_mrr:.2f}.'
        content['metrics'] = [
            {'label': 'Clients on retainer', 'value': len(mrr_entries)},
            {'label': 'MRR', 'value': total_mrr},
        ]
        _store_record(auth.tenant_id, 'agency_portal', 'workspace', workspace_key, content)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'mrr_total': total_mrr}

    @router.get('/agency/overview')
    def agency_overview(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:agency:overview', 120, 60)
        workspaces = [row for row in _load_records(auth.tenant_id) if row.get('feature_key') == 'agency_portal']
        total_mrr = 0.0
        total_members = 0
        for row in workspaces:
            payload = row.get('payload', {}) if isinstance(row.get('payload'), dict) else {}
            workspace = payload.get('workspace', {}) if isinstance(payload.get('workspace'), dict) else {}
            total_mrr += float(workspace.get('mrr_total') or 0.0)
            members = workspace.get('members', []) if isinstance(workspace.get('members'), list) else []
            total_members += len(members)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'overview': {
                'workspaces': len(workspaces),
                'total_members': total_members,
                'total_mrr': round(total_mrr, 2),
            },
        }

    @router.post('/audience-dna/analyze')
    def analyze_audience(payload: AudienceDnaRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:audience-dna', 30, 60)
        audience = _audience_segments(payload.audience_handles, payload.product_price)
        _store_record(
            auth.tenant_id,
            'audience_dna',
            'analysis',
            'latest',
            {
                'status': 'ready',
                'headline': 'Audience segments and targeting recommendations are ready.',
                'metrics': [
                    {'label': 'Super fans', 'value': audience['super_fans']},
                    {'label': 'Buyer score', 'value': audience['avg_buyer_score']},
                ],
                'audience': audience,
            },
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'audience': audience}

    @router.post('/ira/autonomous-brain/health-check')
    def ira_health_check(payload: IraBrainRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:ira', 30, 60)
        latest = _summary(auth.tenant_id)
        active_features = latest['totals']['configured']
        result = {
            'health_score': min(99, 70 + active_features),
            'focus': payload.focus,
            'scheduled_jobs': ['daily health check', 'evergreen recycle', 'weekly strategy adaptation'],
            'recommendations': ['Double down on the top forecasted topic.', 'Repurpose the winner into owned channels.'],
        }
        _store_record(
            auth.tenant_id,
            'ira_autonomous_brain',
            'run',
            'latest',
            {
                'status': 'ready',
                'headline': 'IRA completed a health check and queued autonomous actions.',
                'metrics': [
                    {'label': 'Health score', 'value': result['health_score']},
                    {'label': 'Scheduled jobs', 'value': len(result['scheduled_jobs'])},
                ],
                'ira': result,
            },
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'ira': result}

    @router.post('/ads/campaigns/draft')
    def create_ads_draft(payload: AdsDraftRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:ads', 30, 60)
        ads = _ads_matrix(payload.campaign_name, payload.offer, payload.primary_message)
        _store_record(
            auth.tenant_id,
            'auto_ads_manager',
            'campaign',
            _SLUG_PATTERN.sub('_', payload.campaign_name.lower()).strip('_') or 'campaign',
            {
                'status': 'ready',
                'headline': 'Draft ad pack created across all supported networks.',
                'metrics': [
                    {'label': 'Specs', 'value': ads['spec_count']},
                    {'label': 'Status', 'value': 'draft'},
                ],
                'ads': ads,
            },
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'ads': ads}

    @router.post('/content/repurpose')
    def repurpose_content(payload: RepurposeRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:repurpose', 30, 60)
        repurpose = _repurpose_content(payload.source_content)
        _store_record(
            auth.tenant_id,
            'content_repurpose_engine',
            'batch',
            'latest',
            {
                'status': 'ready',
                'headline': 'Repurpose batch generated for downstream publishing.',
                'metrics': [
                    {'label': 'Formats', 'value': len(repurpose['outputs'])},
                    {'label': 'Hours saved', 'value': repurpose['hours_saved']},
                ],
                'repurpose': repurpose,
            },
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'repurpose': repurpose}

    @router.post('/seo/geo-analyze')
    def geo_analyze(payload: GeoSeoRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:geo', 30, 60)
        geo = _geo_seo(payload.content, payload.competitors)
        _store_record(
            auth.tenant_id,
            'geo_seo_engine',
            'analysis',
            'latest',
            {
                'status': 'ready',
                'headline': 'AI-search optimization report generated.',
                'metrics': [
                    {'label': 'AI share of voice', 'value': geo['ai_share_of_voice']},
                    {'label': 'Citation score', 'value': geo['citation_score']},
                ],
                'geo_seo': geo,
            },
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'geo_seo': geo}

    @router.post('/email/ai-generate')
    def generate_email_marketing(payload: EmailMarketingRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:email', 30, 60)
        email = _email_pack(payload.source_content, payload.audience, payload.cta)
        email_campaigns_memory.append({
            'id': len(email_campaigns_memory) + 1,
            'tenant_id': auth.tenant_id,
            'name': email['newsletter_subject'],
            'status': 'draft',
            'sequence_length': len(email['drip_sequence']),
        })
        _store_record(
            auth.tenant_id,
            'email_marketing',
            'campaign',
            'latest',
            {
                'status': 'ready',
                'headline': 'Newsletter plus 5-email drip generated from source content.',
                'metrics': [
                    {'label': 'Drip emails', 'value': len(email['drip_sequence'])},
                    {'label': 'Audience', 'value': payload.audience},
                ],
                'email': email,
            },
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'email': email}

    @router.post('/scheduler/smart-fill')
    def smart_fill(payload: SmartSchedulerRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:scheduler', 30, 60)
        scheduler = _scheduler_plan(payload.drafts, payload.platform, payload.fill_days)
        for item in scheduler['scheduled_items']:
            scheduled_posts_memory.append({
                'id': len(scheduled_posts_memory) + 1,
                'tenant_id': auth.tenant_id,
                'platform': item['platform'],
                'content': item['draft'],
                'status': 'scheduled',
                'scheduled_for': item['scheduled_for'],
                'source': 'smart-scheduler',
            })
        _store_record(
            auth.tenant_id,
            'smart_scheduler',
            'plan',
            'latest',
            {
                'status': 'ready',
                'headline': 'Drafts distributed into your best-performing windows.',
                'metrics': [
                    {'label': 'Scheduled items', 'value': len(scheduler['scheduled_items'])},
                    {'label': 'Fill days', 'value': payload.fill_days},
                ],
                'scheduler': scheduler,
            },
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'scheduler': scheduler}

    @router.post('/podcast/generate')
    def generate_podcast(payload: PodcastRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:podcast', 30, 60)
        episode = _podcast_episode(payload.title, payload.source_text)
        _store_record(
            auth.tenant_id,
            'podcast_generator',
            'episode',
            _SLUG_PATTERN.sub('_', payload.title.lower()).strip('_') or 'episode',
            {
                'status': 'ready',
                'headline': 'Podcast package generated with RSS-ready metadata.',
                'metrics': [
                    {'label': 'Chapters', 'value': len(episode['chapters'])},
                    {'label': 'Clips', 'value': episode['social_clips']},
                ],
                'podcast': episode,
            },
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'podcast': episode}

    @router.post('/video-script/generate')
    def generate_video_script(payload: VideoScriptRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:video', 30, 60)
        video = _video_script(payload.topic, payload.audience, payload.objective)
        _store_record(
            auth.tenant_id,
            'video_script_generator',
            'script',
            'latest',
            {
                'status': 'ready',
                'headline': 'Video script package generated for production handoff.',
                'metrics': [
                    {'label': 'Scenes', 'value': len(video['scenes'])},
                    {'label': 'Thumbnail concepts', 'value': len(video['thumbnail_concepts'])},
                ],
                'video': video,
            },
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'video': video}

    @router.post('/reports/advanced')
    def generate_advanced_report(payload: AdvancedReportRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:reports', 20, 60)
        tracked_revenue = round(sum(float(item.get('amount') or 0.0) for item in revenue_conversions_memory if item.get('tenant_id') == auth.tenant_id), 2)
        attributed_posts = sum(1 for item in revenue_touchpoints_memory if item.get('tenant_id') == auth.tenant_id)
        report = {
            'client_name': payload.client_name,
            'window_days': payload.reporting_window_days,
            'executive_summary': 'Top content themes are compounding into measurable revenue, with clear winners for redistribution.',
            'platform_breakdown': [
                {'platform': 'linkedin', 'pipeline_share_pct': 46},
                {'platform': 'instagram', 'pipeline_share_pct': 31},
                {'platform': 'email', 'pipeline_share_pct': 23},
            ],
            'tracked_revenue': tracked_revenue,
            'attributed_posts': attributed_posts,
            'csv_export_path': '/analytics/export',
        }
        analytics_reports_memory.append({
            'id': len(analytics_reports_memory) + 1,
            'tenant_id': auth.tenant_id,
            'name': f"{payload.client_name} advanced report",
            'status': 'ready',
        })
        _store_record(
            auth.tenant_id,
            'advanced_reports',
            'report',
            _SLUG_PATTERN.sub('_', payload.client_name.lower()).strip('_') or 'client',
            {
                'status': 'ready',
                'headline': 'White-label advanced report generated with executive summary and export path.',
                'metrics': [
                    {'label': 'Tracked revenue', 'value': tracked_revenue},
                    {'label': 'Attributed posts', 'value': attributed_posts},
                ],
                'report': report,
            },
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'report': report}

    # ── New Lately-parity routes ─────────────────────────────────────────────

    @router.get('/ai/brand-voice/profiles')
    def list_brand_voice_profiles(auth: AuthDep) -> dict[str, Any]:
        """List all brand voice profiles for the tenant, including fingerprint and score."""
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:brand-voice:list', 120, 60)
        records = [
            row for row in _load_records(auth.tenant_id)
            if row.get('feature_key') == 'brand_voice_dna'
        ]
        profiles = []
        for row in records:
            payload = row.get('payload', {}) if isinstance(row.get('payload'), dict) else {}
            bv = payload.get('brand_voice', {}) if isinstance(payload.get('brand_voice'), dict) else {}
            profiles.append({
                'profile_key': row.get('resource_key'),
                'headline': payload.get('headline', ''),
                'voice_score': bv.get('voice_score', 0),
                'fingerprint': bv.get('fingerprint', {}),
                'rewrite': bv.get('rewrite', ''),
                'updated_at': row.get('updated_at'),
                'thumbs_up': int(payload.get('thumbs_up', 0)),
                'thumbs_down': int(payload.get('thumbs_down', 0)),
            })
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'profiles': profiles, 'count': len(profiles)}

    @router.post(
        '/ai/brand-voice/{profile_key}/feedback',
        responses={404: {'description': 'Brand voice profile not found.'}},
    )
    def brand_voice_feedback(profile_key: str, payload: BrandVoiceFeedbackRequest, auth: AuthDep) -> dict[str, Any]:
        """Record thumbs-up/down feedback to improve the AI writing model."""
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:brand-voice:feedback', 120, 60)
        records = _load_records(auth.tenant_id)
        record = next(
            (row for row in records if row.get('feature_key') == 'brand_voice_dna' and row.get('resource_key') == profile_key),
            None,
        )
        if record is None:
            raise HTTPException(status_code=404, detail='Brand voice profile not found.')
        content = record.get('payload', {}) if isinstance(record.get('payload'), dict) else {}
        thumbs_up = int(content.get('thumbs_up', 0))
        thumbs_down = int(content.get('thumbs_down', 0))
        if payload.signal == 'thumbs_up':
            thumbs_up += 1
        else:
            thumbs_down += 1
        if payload.edited_output:
            bv = content.get('brand_voice', {}) if isinstance(content.get('brand_voice'), dict) else {}
            bv['rewrite'] = payload.edited_output
            content['brand_voice'] = bv
        content['thumbs_up'] = thumbs_up
        content['thumbs_down'] = thumbs_down
        # Adjust voice score based on cumulative positive feedback signal
        bv = content.get('brand_voice', {}) if isinstance(content.get('brand_voice'), dict) else {}
        base_score = int(bv.get('voice_score', 70))
        net_signal = thumbs_up - thumbs_down
        adjusted = min(99, max(40, base_score + net_signal))
        bv['voice_score'] = adjusted
        content['brand_voice'] = bv
        content['headline'] = f"Voice model adapting: score {adjusted}/100, {thumbs_up} positive signals."
        _store_record(auth.tenant_id, 'brand_voice_dna', 'profile', profile_key, content)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'profile_key': profile_key,
            'voice_score': adjusted,
            'thumbs_up': thumbs_up,
            'thumbs_down': thumbs_down,
        }

    @router.get('/experiments/ab-tests')
    def list_ab_tests(auth: AuthDep) -> dict[str, Any]:
        """List all A/B tests for the tenant with their status and winner data."""
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:ab-test:list', 120, 60)
        records = [
            row for row in _load_records(auth.tenant_id)
            if row.get('feature_key') == 'auto_ab_testing'
        ]
        tests = []
        for row in records:
            payload = row.get('payload', {}) if isinstance(row.get('payload'), dict) else {}
            tests.append({
                'test_key': row.get('resource_key'),
                'name': payload.get('name', row.get('resource_key')),
                'status': payload.get('status', 'unknown'),
                'headline': payload.get('headline', ''),
                'variants_count': len(payload.get('variants', [])) if isinstance(payload.get('variants'), list) else 0,
                'winner': payload.get('winner'),
                'channel': payload.get('channel', 'linkedin'),
                'goal': payload.get('goal', 'engagement'),
                'updated_at': row.get('updated_at'),
            })
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'tests': tests, 'count': len(tests)}

    @router.get('/analytics/keywords/top')
    def keyword_top_insights(auth: AuthDep) -> dict[str, Any]:
        """Return keyword performance data for word cloud and engagement insights."""
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:keywords:top', 120, 60)
        # Gather keyword data from tracked keywords and voice profiles
        tracked = [
            row for row in _load_records(auth.tenant_id)
            if row.get('feature_key') == 'keyword_tracking'
        ]
        # Seed from brand voice fingerprint signature words
        voice_records = [
            row for row in _load_records(auth.tenant_id)
            if row.get('feature_key') == 'brand_voice_dna'
        ]
        keyword_map: dict[str, dict[str, Any]] = {}
        for row in tracked:
            p = row.get('payload', {}) if isinstance(row.get('payload'), dict) else {}
            kw = str(p.get('keyword', ''))
            if not kw:
                continue
            if kw not in keyword_map:
                keyword_map[kw] = {'keyword': kw, 'impressions': 0, 'engagement': 0, 'platforms': []}
            keyword_map[kw]['impressions'] += int(p.get('impressions', 0))
            keyword_map[kw]['engagement'] += int(p.get('engagement', 0))
            platform = p.get('platform', '')
            if platform and platform not in keyword_map[kw]['platforms']:
                keyword_map[kw]['platforms'].append(platform)
        for vrow in voice_records:
            vp = vrow.get('payload', {}) if isinstance(vrow.get('payload'), dict) else {}
            bv = vp.get('brand_voice', {}) if isinstance(vp.get('brand_voice'), dict) else {}
            fp = bv.get('fingerprint', {}) if isinstance(bv.get('fingerprint'), dict) else {}
            sig_words = fp.get('signature_words', []) if isinstance(fp.get('signature_words'), list) else []
            for idx, word in enumerate(sig_words):
                if word not in keyword_map:
                    keyword_map[word] = {'keyword': word, 'impressions': 2400 - idx * 200, 'engagement': 180 - idx * 12, 'platforms': ['linkedin']}
        # Compute engagement rate and sort by impressions
        keywords = sorted(keyword_map.values(), key=lambda x: int(x.get('impressions', 0)), reverse=True)
        for kw in keywords:
            imp = int(kw.get('impressions', 0))
            eng = int(kw.get('engagement', 0))
            kw['engagement_rate'] = round(eng / max(1, imp), 4)
            kw['weight'] = min(100, max(10, round(imp / 25)))
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'keywords': keywords[:40],
            'count': len(keywords),
        }

    @router.post('/analytics/keywords/track')
    def track_keyword(payload: KeywordTrackRequest, auth: AuthDep) -> dict[str, Any]:
        """Record impressions and engagement for a keyword to build the word cloud."""
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:keywords:track', 120, 60)
        slug = _SLUG_PATTERN.sub('_', payload.keyword.lower()).strip('_') or 'keyword'
        _store_record(
            auth.tenant_id,
            'keyword_tracking',
            'keyword',
            slug,
            {
                'keyword': payload.keyword,
                'impressions': payload.impressions,
                'engagement': payload.engagement,
                'platform': payload.platform,
                'updated_at': _now_iso(),
            },
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'keyword': payload.keyword, 'tracked': True}

    @router.get('/brand-hierarchy')
    def list_brand_hierarchy(auth: AuthDep) -> dict[str, Any]:
        """Return the parent-child brand hierarchy for enterprise/franchise accounts."""
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:brand-hierarchy:list', 120, 60)
        records = [
            row for row in _load_records(auth.tenant_id)
            if row.get('feature_key') == 'brand_hierarchy'
        ]
        brands = []
        for row in records:
            p = row.get('payload', {}) if isinstance(row.get('payload'), dict) else {}
            brands.append({
                'brand_key': row.get('resource_key'),
                'brand_name': p.get('brand_name', ''),
                'parent_brand_key': p.get('parent_brand_key', 'root'),
                'region': p.get('region'),
                'industry': p.get('industry'),
                'voice_profile_key': p.get('voice_profile_key'),
                'created_at': row.get('created_at'),
                'updated_at': row.get('updated_at'),
            })
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'brands': brands, 'count': len(brands)}

    @router.post('/brand-hierarchy')
    def create_child_brand(payload: BrandHierarchyRequest, auth: AuthDep) -> dict[str, Any]:
        """Add a child brand under the parent-child brand hierarchy."""
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:brand-hierarchy:create', 30, 60)
        brand_key = f'brand_{_SLUG_PATTERN.sub("_", payload.child_brand_name.lower()).strip("_")}_{uuid.uuid4().hex[:6]}'
        _store_record(
            auth.tenant_id,
            'brand_hierarchy',
            'brand',
            brand_key,
            {
                'brand_name': payload.child_brand_name,
                'parent_brand_key': payload.parent_brand_key,
                'region': payload.region,
                'industry': payload.industry,
                'voice_profile_key': payload.voice_profile_key,
                'created_at': _now_iso(),
            },
        )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'brand_key': brand_key, 'brand_name': payload.child_brand_name}

    @router.get('/analytics/export')
    def export_analytics_csv(auth: AuthDep) -> dict[str, Any]:
        """Return a CSV-formatted analytics export for all channels."""
        enforce_rate_limit(f'{auth.tenant_id}:growth-suite:export', 20, 60)
        rows: list[dict[str, Any]] = []
        # Aggregate from scheduled posts
        for item in scheduled_posts_memory:
            if item.get('tenant_id') != auth.tenant_id:
                continue
            rows.append({
                'type': 'scheduled_post',
                'platform': item.get('platform', ''),
                'content': str(item.get('content', ''))[:80],
                'status': item.get('status', ''),
                'scheduled_for': item.get('scheduled_for', ''),
                'impressions': 0,
                'engagement': 0,
            })
        csv_lines = ['type,platform,content,status,scheduled_for,impressions,engagement']
        for row in rows[:500]:
            safe_content = str(row.get('content', '')).replace('"', "'").replace(',', ';')
            csv_lines.append(
                f"{row['type']},{row['platform']},\"{safe_content}\",{row['status']},{row['scheduled_for']},{row['impressions']},{row['engagement']}"
            )
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'export_format': 'csv',
            'row_count': len(rows),
            'csv': '\n'.join(csv_lines),
            'generated_at': _now_iso(),
        }

    return router