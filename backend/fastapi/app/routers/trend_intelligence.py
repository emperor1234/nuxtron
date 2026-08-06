# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedFunction=false

import threading
import uuid
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]
TrendPhase = str


class TrendSignalRequest(BaseModel):
    source_type: str = Field(default='social_media', max_length=40)
    source_platform: str = Field(default='instagram', max_length=80)
    topic: str = Field(min_length=2, max_length=200)
    keywords: list[str] = Field(default_factory=list, max_length=40)
    captured_at: str | None = Field(default=None, max_length=40)
    mentions: int = Field(default=0, ge=0)
    likes: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    saves: int = Field(default=0, ge=0)
    views: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    conversions: int = Field(default=0, ge=0)
    spend: float = Field(default=0.0, ge=0)
    dwell_seconds: float = Field(default=0.0, ge=0)
    negative_feedback: int = Field(default=0, ge=0)
    audience_segments: list[str] = Field(default_factory=list, max_length=20)
    not_viewed_reasons: dict[str, int] = Field(default_factory=dict)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class ForecastRequest(BaseModel):
    horizon_days: int = Field(default=30, ge=7, le=120)
    lookback_days: int = Field(default=30, ge=7, le=180)
    min_signals_per_topic: int = Field(default=2, ge=1, le=100)


class TrendSelectionRequest(BaseModel):
    trend_id: str = Field(min_length=3, max_length=80)
    objective: str = Field(default='engagement', max_length=80)
    channels: list[str] = Field(default_factory=lambda: ['instagram', 'tiktok'], min_length=1, max_length=12)
    budget: float = Field(default=0.0, ge=0)


class ContentGenerateRequest(BaseModel):
    trend_id: str | None = Field(default=None, max_length=80)
    selection_id: int | None = Field(default=None, ge=1)
    target_channel: str = Field(default='instagram', max_length=80)
    output_types: list[str] = Field(default_factory=lambda: ['social_post', 'short_ad_copy', 'hook', 'cta'], min_length=1, max_length=12)
    tone: str = Field(default='high-energy', max_length=80)
    language: str = Field(default='en', max_length=16)


class PerformanceTrackRequest(BaseModel):
    trend_id: str = Field(min_length=3, max_length=80)
    content_id: str = Field(min_length=3, max_length=120)
    channel: str = Field(default='instagram', max_length=80)
    posted_at: str | None = Field(default=None, max_length=40)
    likes: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    saves: int = Field(default=0, ge=0)
    views: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    conversions: int = Field(default=0, ge=0)
    spend: float = Field(default=0.0, ge=0)
    revenue: float = Field(default=0.0, ge=0)
    watch_time_seconds: float = Field(default=0.0, ge=0)
    not_viewed_reasons: dict[str, int] = Field(default_factory=dict)


@dataclass
class _TrendCtx:
    enforce_rate_limit: Callable[[str, int, int], None]
    signals_memory: list[dict[str, Any]]
    forecasts_memory: list[dict[str, Any]]
    selections_memory: list[dict[str, Any]]
    content_memory: list[dict[str, Any]]
    performance_memory: list[dict[str, Any]]
    recommendations_memory: list[dict[str, Any]]
    lock: threading.Lock


def _to_dt(raw: str | None, fallback: datetime) -> datetime:
    if not raw:
        return fallback
    try:
        return datetime.fromisoformat(raw.replace('Z', '+00:00')).astimezone(UTC)
    except ValueError:
        return fallback


def _safe_rate(numerator: float, denominator: float) -> float:
    return 0.0 if denominator <= 0 else numerator / denominator


def _clip(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _classify_phase(strength: float, momentum: float, acceleration: float) -> TrendPhase:
    if strength >= 0.64 and momentum >= 0.08 and acceleration >= 0.01:
        return 'upcoming_forecast'
    if strength >= 0.52 and momentum >= 0.02:
        return 'emerging'
    if strength >= 0.4 and momentum > -0.02:
        return 'current'
    return 'downfall'


def _recommendation_lines(phase: TrendPhase, roi_score: float, best_hour: int | None) -> list[str]:
    lines: list[str] = []
    if phase == 'upcoming_forecast':
        lines.append('Move early: publish teaser and problem-framing content before competitor saturation.')
    elif phase == 'emerging':
        lines.append('Scale now: repurpose winners into short video and carousel variants this week.')
    elif phase == 'current':
        lines.append('Defend share: optimize hooks and CTAs while trend demand is active.')
    else:
        lines.append('Reposition quickly: pivot to adjacent narratives and reduce paid spend on this trend.')

    if roi_score < 0.45:
        lines.append('Improve offer clarity and intent targeting to lift conversion efficiency.')
    elif roi_score > 0.75:
        lines.append('Increase controlled spend on the top channel while trend ROI remains high.')

    if best_hour is not None:
        lines.append(f'Peak publishing window detected near {best_hour:02d}:00 local trend time.')
    return lines


def _best_hour_for_perf(trend_perf: list[dict[str, Any]], now: datetime) -> int | None:
    if not trend_perf:
        return None
    hour_counter: dict[int, float] = defaultdict(float)
    for row in trend_perf:
        dt = _to_dt(str(row.get('posted_at')), now)
        hour_counter[dt.hour] += float(row.get('engagement_rate') or 0.0)
    return max(hour_counter, key=lambda key, counter=hour_counter: counter.get(key, 0.0)) if hour_counter else None


def _recommendation_item(forecast: dict[str, Any], perf: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    trend_perf = [p for p in perf if p.get('trend_id') == forecast.get('trend_id')]
    best_hour = _best_hour_for_perf(trend_perf, now)
    phase = str(forecast.get('phase') or 'current')
    roi_score = float(forecast.get('roi_score') or 0.0)
    return {
        'trend_id': str(forecast.get('trend_id')),
        'topic': forecast.get('topic'),
        'phase': phase,
        'priority': 'high' if phase in {'upcoming_forecast', 'emerging'} else 'medium',
        'roi_score': round(roi_score, 6),
        'recommendations': _recommendation_lines(phase, roi_score, best_hour),
    }


def _tenant_signals_for_window(ctx: _TrendCtx, tenant_id: str, cutoff: datetime, now: datetime) -> list[dict[str, Any]]:
    with ctx.lock:
        return [
            s.copy()
            for s in ctx.signals_memory
            if s.get('tenant_id') == tenant_id and _to_dt(str(s.get('captured_at')), now) >= cutoff
        ]


def _topic_series(topic_signals: list[dict[str, Any]]) -> tuple[list[float], list[float], list[float], list[float]]:
    scores = [float(s.get('virality_score') or 0.0) for s in topic_signals]
    quality = [float(s.get('quality_index') or 0.0) for s in topic_signals]
    ctr_values = [float(s.get('ctr') or 0.0) for s in topic_signals]
    conv_values = [float(s.get('conversion_rate') or 0.0) for s in topic_signals]
    return scores, quality, ctr_values, conv_values


def _topic_strengths(scores: list[float], quality: list[float], ctr_values: list[float], conv_values: list[float]) -> tuple[float, float, float, float, TrendPhase]:
    strength = _clip((sum(scores) / max(1, len(scores))) * 0.7 + (sum(quality) / max(1, len(quality))) * 0.3)
    momentum = (scores[-1] - scores[0]) / max(1, len(scores) - 1)
    acceleration = 0.0 if len(scores) < 3 else (scores[-1] - scores[-2]) - (scores[-2] - scores[-3])
    roi_score = _clip((sum(conv_values) / max(1, len(conv_values))) * 0.6 + (sum(ctr_values) / max(1, len(ctr_values))) * 0.4)
    phase = _classify_phase(strength, momentum, acceleration)
    return strength, momentum, acceleration, roi_score, phase


def _topic_timing(topic_signals: list[dict[str, Any]], now: datetime) -> tuple[str, int]:
    platform_counter: dict[str, int] = defaultdict(int)
    hourly_counter: dict[int, int] = defaultdict(int)
    for signal in topic_signals:
        platform_counter[str(signal.get('source_platform') or 'unknown')] += 1
        dt = _to_dt(str(signal.get('captured_at')), now)
        hourly_counter[dt.hour] += int(signal.get('views') or 0)

    best_platform = max(platform_counter, key=lambda key, counter=platform_counter: counter.get(key, 0))
    best_hour = max(hourly_counter, key=lambda key, counter=hourly_counter: counter.get(key, 0)) if hourly_counter else 12
    return best_platform, best_hour


def _topic_projection(strength: float, momentum: float, acceleration: float, mean_ctr: float, horizon_days: int) -> list[dict[str, Any]]:
    projection: list[dict[str, Any]] = []
    for day in range(1, horizon_days + 1):
        day_factor = 1 + momentum * day + acceleration * (day * 0.2)
        projected_strength = _clip(strength * max(0.2, day_factor))
        projection.append(
            {
                'day': day,
                'projected_strength': round(projected_strength, 6),
                'projected_reach': int(1000 + projected_strength * 40000),
                'projected_ctr': round(_clip(mean_ctr * (0.95 + momentum * 2), 0.0, 0.25), 6),
            }
        )
    return projection


def _build_topic_forecast(
    *,
    topic: str,
    topic_signals: list[dict[str, Any]],
    tenant_id: str,
    now: datetime,
    horizon_days: int,
    next_id: int,
) -> dict[str, Any]:
    topic_signals.sort(key=lambda s: str(s.get('captured_at', '')))
    scores, quality, ctr_values, conv_values = _topic_series(topic_signals)
    strength, momentum, acceleration, roi_score, phase = _topic_strengths(scores, quality, ctr_values, conv_values)
    best_platform, best_hour = _topic_timing(topic_signals, now)
    projection = _topic_projection(strength, momentum, acceleration, sum(ctr_values) / max(1, len(ctr_values)), horizon_days)

    return {
        'id': next_id,
        'trend_id': f'trend_{uuid.uuid4().hex[:12]}',
        'tenant_id': tenant_id,
        'topic': topic,
        'phase': phase,
        'trend_strength': round(strength, 6),
        'momentum': round(momentum, 6),
        'acceleration': round(acceleration, 6),
        'roi_score': round(roi_score, 6),
        'best_platform': best_platform,
        'best_hour': best_hour,
        'signal_count': len(topic_signals),
        'horizon_days': horizon_days,
        'projection': projection,
        'created_at': now.isoformat(),
    }


def _compute_forecasts(ctx: _TrendCtx, tenant_id: str, payload: ForecastRequest, now: datetime) -> list[dict[str, Any]]:
    lookback_cutoff = now - timedelta(days=payload.lookback_days)
    tenant_signals = _tenant_signals_for_window(ctx, tenant_id, lookback_cutoff, now)

    by_topic: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for signal in tenant_signals:
        by_topic[str(signal.get('topic') or 'unknown')].append(signal)

    forecasts: list[dict[str, Any]] = []
    for topic, topic_signals in by_topic.items():
        if len(topic_signals) < payload.min_signals_per_topic:
            continue
        forecasts.append(
            _build_topic_forecast(
                topic=topic,
                topic_signals=topic_signals,
                tenant_id=tenant_id,
                now=now,
                horizon_days=payload.horizon_days,
                next_id=len(ctx.forecasts_memory) + len(forecasts) + 1,
            )
        )

    forecasts.sort(key=lambda item: (float(item.get('trend_strength') or 0.0), float(item.get('roi_score') or 0.0)), reverse=True)
    return forecasts


def _aggregate_analytics(forecasts: list[dict[str, Any]], perf: list[dict[str, Any]], days: int) -> dict[str, Any]:
    phase_counter: dict[str, int] = defaultdict(int)
    strength_points: list[dict[str, Any]] = []
    for item in sorted(forecasts, key=lambda row: str(row.get('created_at', ''))):
        phase_counter[str(item.get('phase') or 'unknown')] += 1
        strength_points.append(
            {
                'timestamp': item.get('created_at'),
                'topic': item.get('topic'),
                'strength': item.get('trend_strength', 0),
                'roi_score': item.get('roi_score', 0),
            }
        )

    totals: dict[str, float | int] = {
        'views': sum(int(p.get('views') or 0) for p in perf),
        'clicks': sum(int(p.get('clicks') or 0) for p in perf),
        'conversions': sum(int(p.get('conversions') or 0) for p in perf),
        'revenue': round(sum(float(p.get('revenue') or 0.0) for p in perf), 2),
        'spend': round(sum(float(p.get('spend') or 0.0) for p in perf), 2),
        'likes': sum(int(p.get('likes') or 0) for p in perf),
        'comments': sum(int(p.get('comments') or 0) for p in perf),
        'shares': sum(int(p.get('shares') or 0) for p in perf),
        'saves': sum(int(p.get('saves') or 0) for p in perf),
    }
    views = float(totals['views'])
    clicks = float(totals['clicks'])
    conversions = float(totals['conversions'])
    spend = float(totals['spend'])
    revenue = float(totals['revenue'])
    engagement_total = float(totals['likes']) + float(totals['comments']) + float(totals['shares']) + float(totals['saves'])

    totals['ctr'] = round(_safe_rate(clicks, max(views, 1.0)), 6)
    totals['conversion_rate'] = round(_safe_rate(conversions, max(clicks, 1.0)), 6)
    totals['roi'] = round(_safe_rate(revenue - spend, max(spend, 1.0)), 6)
    totals['engagement_rate'] = round(_safe_rate(engagement_total, max(views, 1.0)), 6)

    hour_heatmap: dict[str, float] = defaultdict(float)
    for row in perf:
        dt = _to_dt(str(row.get('posted_at')), datetime.now(UTC))
        bucket = f"{dt.strftime('%A')}:{dt.hour:02d}"
        hour_heatmap[bucket] += float(row.get('engagement_rate') or 0.0)

    heatmap_rows = [
        {'bucket': key, 'engagement_score': round(score, 6)}
        for key, score in sorted(hour_heatmap.items(), key=lambda item: item[1], reverse=True)[:24]
    ]

    achievable = {
        'conservative_revenue': round(revenue * 1.08, 2),
        'target_revenue': round(revenue * 1.22, 2),
        'aggressive_revenue': round(revenue * 1.4, 2),
    }

    kpi = {
        'trend_strength_kpi': round(sum(float(x.get('trend_strength') or 0.0) for x in forecasts) / max(1, len(forecasts)), 6),
        'traction_kpi': round(_safe_rate(engagement_total, max(views, 1.0)) * 1000, 3),
        'roi_kpi': round(_safe_rate(revenue - spend, max(spend, 1.0)), 6),
        'revenue_per_1k_views_kpi': round(_safe_rate(revenue, max(views, 1.0)) * 1000, 3),
        'conversion_efficiency_kpi': round(_safe_rate(conversions, max(views, 1.0)), 6),
    }

    performance_indicators = {
        'save_rate': round(_safe_rate(float(totals['saves']), max(views, 1.0)), 6),
        'share_rate': round(_safe_rate(float(totals['shares']), max(views, 1.0)), 6),
        'comment_rate': round(_safe_rate(float(totals['comments']), max(views, 1.0)), 6),
        'like_rate': round(_safe_rate(float(totals['likes']), max(views, 1.0)), 6),
        'click_to_conversion_ratio': round(_safe_rate(conversions, max(clicks, 1.0)), 6),
        'cost_per_click_proxy': round(_safe_rate(spend, max(clicks, 1.0)), 6),
        'cost_per_conversion_proxy': round(_safe_rate(spend, max(conversions, 1.0)), 6),
        'momentum_indicator': round(sum(float(x.get('momentum') or 0.0) for x in forecasts) / max(1, len(forecasts)), 6),
        'downfall_risk_indicator': round(_safe_rate(phase_counter.get('downfall', 0), max(len(forecasts), 1)), 6),
        'opportunity_indicator': round(_safe_rate(phase_counter.get('upcoming_forecast', 0) + phase_counter.get('emerging', 0), max(len(forecasts), 1)), 6),
    }

    return {
        'window_days': days,
        'summary': {
            'tracked_trends': len(forecasts),
            'tracked_posts_ads': len(perf),
            'phase_distribution': phase_counter,
            'totals': totals,
        },
        'kpi': kpi,
        'performance_indicators': performance_indicators,
        'graphs': {
            'trend_strength_history': strength_points,
            'engagement_funnel': {'views': totals['views'], 'clicks': totals['clicks'], 'conversions': totals['conversions']},
            'posting_heatmap': heatmap_rows,
            'achievable_projection': achievable,
        },
    }


def _register_signal_routes(router: APIRouter, ctx: _TrendCtx) -> None:
    @router.post('/trends/signals/ingest')
    def ingest_signal(payload: TrendSignalRequest, auth: AuthDep) -> dict[str, Any]:
        ctx.enforce_rate_limit(f'{auth.tenant_id}:trends:signals:ingest', 600, 60)
        captured_at = _to_dt(payload.captured_at, datetime.now(UTC))

        total_engagement = payload.likes + payload.comments + payload.shares + payload.saves
        engagement_rate = _safe_rate(total_engagement, max(payload.views, payload.mentions, 1))
        ctr = _safe_rate(payload.clicks, max(payload.views, 1))
        conversion_rate = _safe_rate(payload.conversions, max(payload.clicks, 1))
        negative_ratio = _safe_rate(payload.negative_feedback, max(payload.views, 1))
        virality_score = _clip((engagement_rate * 0.45) + (_safe_rate(payload.shares, max(payload.views, 1)) * 0.35) + (ctr * 0.2))
        quality_index = _clip(virality_score * 0.7 + conversion_rate * 0.4 - negative_ratio * 0.25)

        signal = {
            'id': len(ctx.signals_memory) + 1,
            'tenant_id': auth.tenant_id,
            'source_type': payload.source_type.strip().lower(),
            'source_platform': payload.source_platform.strip().lower(),
            'topic': payload.topic.strip().lower(),
            'keywords': [k.strip().lower() for k in payload.keywords if k.strip()],
            'captured_at': captured_at.isoformat(),
            'mentions': payload.mentions,
            'likes': payload.likes,
            'comments': payload.comments,
            'shares': payload.shares,
            'saves': payload.saves,
            'views': payload.views,
            'clicks': payload.clicks,
            'conversions': payload.conversions,
            'spend': round(payload.spend, 2),
            'dwell_seconds': payload.dwell_seconds,
            'negative_feedback': payload.negative_feedback,
            'audience_segments': payload.audience_segments,
            'not_viewed_reasons': payload.not_viewed_reasons,
            'raw_payload': payload.raw_payload,
            'engagement_rate': round(engagement_rate, 6),
            'ctr': round(ctr, 6),
            'conversion_rate': round(conversion_rate, 6),
            'virality_score': round(virality_score, 6),
            'quality_index': round(quality_index, 6),
            'created_at': datetime.now(UTC).isoformat(),
        }
        with ctx.lock:
            ctx.signals_memory.append(signal)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'signal': signal}

    @router.get('/trends/signals')
    def list_signals(
        auth: AuthDep,
        topic: str | None = None,
        source_platform: str | None = None,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        ctx.enforce_rate_limit(f'{auth.tenant_id}:trends:signals:list', 240, 60)
        with ctx.lock:
            items = [s.copy() for s in ctx.signals_memory if s.get('tenant_id') == auth.tenant_id]
        if topic:
            topic_l = topic.strip().lower()
            items = [s for s in items if s.get('topic') == topic_l]
        if source_platform:
            platform_l = source_platform.strip().lower()
            items = [s for s in items if s.get('source_platform') == platform_l]
        items.sort(key=lambda x: str(x.get('captured_at', '')), reverse=True)
        sliced = items[offset: offset + limit]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(sliced), 'items': sliced, 'total': len(items)}


def _register_forecast_routes(router: APIRouter, ctx: _TrendCtx) -> None:
    @router.post('/trends/forecast/generate')
    def generate_forecast(payload: ForecastRequest, auth: AuthDep) -> dict[str, Any]:
        ctx.enforce_rate_limit(f'{auth.tenant_id}:trends:forecast:generate', 60, 60)
        now = datetime.now(UTC)
        forecasts = _compute_forecasts(ctx, auth.tenant_id, payload, now)
        with ctx.lock:
            ctx.forecasts_memory.extend(forecasts)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'generated_at': now.isoformat(), 'count': len(forecasts), 'forecasts': forecasts}

    @router.get('/trends/forecast')
    def list_forecasts(
        auth: AuthDep,
        phase: str | None = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> dict[str, Any]:
        ctx.enforce_rate_limit(f'{auth.tenant_id}:trends:forecast:list', 120, 60)
        with ctx.lock:
            items = [f.copy() for f in ctx.forecasts_memory if f.get('tenant_id') == auth.tenant_id]
        if phase:
            phase_l = phase.strip().lower()
            items = [f for f in items if str(f.get('phase', '')).lower() == phase_l]
        items.sort(key=lambda row: str(row.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': min(len(items), limit), 'forecasts': items[:limit]}

    @router.post('/trends/select', responses={404: {'description': 'Trend not found for this tenant.'}})
    def select_trend(payload: TrendSelectionRequest, auth: AuthDep) -> dict[str, Any]:
        ctx.enforce_rate_limit(f'{auth.tenant_id}:trends:select', 120, 60)
        with ctx.lock:
            trend = next(
                (f for f in reversed(ctx.forecasts_memory) if f.get('tenant_id') == auth.tenant_id and f.get('trend_id') == payload.trend_id),
                None,
            )
            if trend is None:
                raise HTTPException(status_code=404, detail='Trend not found for this tenant.')

            selection = {
                'id': len(ctx.selections_memory) + 1,
                'tenant_id': auth.tenant_id,
                'trend_id': payload.trend_id,
                'topic': trend.get('topic'),
                'phase': trend.get('phase'),
                'objective': payload.objective,
                'channels': [c.strip().lower() for c in payload.channels if c.strip()],
                'budget': round(payload.budget, 2),
                'created_at': datetime.now(UTC).isoformat(),
            }
            ctx.selections_memory.append(selection)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'selection': selection}


def _resolve_content_trend(ctx: _TrendCtx, tenant_id: str, payload: ContentGenerateRequest) -> dict[str, Any] | None:
    with ctx.lock:
        if payload.trend_id:
            return next(
                (f for f in reversed(ctx.forecasts_memory) if f.get('tenant_id') == tenant_id and f.get('trend_id') == payload.trend_id),
                None,
            )
        if payload.selection_id:
            selection = next(
                (s for s in ctx.selections_memory if s.get('tenant_id') == tenant_id and s.get('id') == payload.selection_id),
                None,
            )
            if selection is not None:
                return next(
                    (f for f in reversed(ctx.forecasts_memory) if f.get('tenant_id') == tenant_id and f.get('trend_id') == selection.get('trend_id')),
                    None,
                )
    return None


def _asset_text(topic: str, phase: str, best_platform: str, kind: str) -> str:
    if kind == 'social_post':
        return (
            f"{topic.title()} is {phase.replace('_', ' ')} right now. "
            f'If you are building on {best_platform}, lead with a bold point of view, then prove it with one data-backed example.'
        )
    if kind == 'short_ad_copy':
        return (
            f'{topic.title()} is gaining traction. Launch a 15-second ad highlighting one urgent pain and one clear benefit. '
            'Use a strong CTA to capture intent now.'
        )
    if kind == 'hook':
        return f'Most brands miss {topic} early. Here is how to turn it into measurable traction this week.'
    if kind == 'cta':
        return 'Save this, test it today, and share results in 24 hours to compound reach.'
    return f'{topic.title()} trend play for {kind}: focus on speed, clarity, and proof.'


def _build_content_assets(topic: str, phase: str, best_platform: str, output_types: list[str], target_channel: str) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for output_type in output_types:
        kind = output_type.strip().lower()
        assets.append({'type': kind, 'channel': target_channel, 'text': _asset_text(topic, phase, best_platform, kind), 'phase': phase})
    return assets


def _build_performance_diagnostics(tenant_perf: list[dict[str, Any]], engagement_rate: float) -> dict[str, Any]:
    reason_counter: dict[str, int] = defaultdict(int)
    hour_counter: dict[int, int] = defaultdict(int)
    for row in tenant_perf:
        reasons = row.get('not_viewed_reasons', {})
        if isinstance(reasons, dict):
            for reason, count in reasons.items():
                reason_counter[str(reason)] += int(count)
        dt = _to_dt(str(row.get('posted_at')), datetime.now(UTC))
        hour_counter[dt.hour] += int(row.get('views') or 0)

    best_hour = max(hour_counter, key=lambda key, counter=hour_counter: counter.get(key, 0)) if hour_counter else None
    top_not_viewed = sorted(reason_counter.items(), key=lambda item: item[1], reverse=True)[:5]
    return {
        'top_not_viewed_reasons': [{'reason': reason, 'count': count} for reason, count in top_not_viewed],
        'best_hour': best_hour,
        'improvement_focus': 'hook_quality' if engagement_rate < 0.03 else 'cta_optimization',
    }


def _register_content_generate_route(router: APIRouter, ctx: _TrendCtx) -> None:
    @router.post('/trends/content/generate', responses={404: {'description': 'No trend context found.'}})
    def generate_content(payload: ContentGenerateRequest, auth: AuthDep) -> dict[str, Any]:
        ctx.enforce_rate_limit(f'{auth.tenant_id}:trends:content:generate', 60, 60)
        trend = _resolve_content_trend(ctx, auth.tenant_id, payload)
        if trend is None:
            raise HTTPException(status_code=404, detail='No trend context found. Provide trend_id or valid selection_id.')

        topic = str(trend.get('topic') or 'trend opportunity')
        phase = str(trend.get('phase') or 'emerging')
        best_platform = str(trend.get('best_platform') or payload.target_channel)
        strength = float(trend.get('trend_strength') or 0.0)
        assets = _build_content_assets(topic, phase, best_platform, payload.output_types, payload.target_channel)

        generation = {
            'id': len(ctx.content_memory) + 1,
            'tenant_id': auth.tenant_id,
            'trend_id': trend.get('trend_id'),
            'topic': topic,
            'phase': phase,
            'target_channel': payload.target_channel,
            'tone': payload.tone,
            'language': payload.language,
            'ai_model_hints': ['gpt-4.1', 'claude-3.7-sonnet', 'gemini-2.5-pro'],
            'confidence': round(_clip(0.45 + strength * 0.5), 4),
            'assets': assets,
            'created_at': datetime.now(UTC).isoformat(),
        }
        with ctx.lock:
            ctx.content_memory.append(generation)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'generation': generation}


def _register_performance_track_route(router: APIRouter, ctx: _TrendCtx) -> None:

    @router.post('/trends/performance/track')
    def track_performance(payload: PerformanceTrackRequest, auth: AuthDep) -> dict[str, Any]:
        ctx.enforce_rate_limit(f'{auth.tenant_id}:trends:performance:track', 300, 60)
        posted_at = _to_dt(payload.posted_at, datetime.now(UTC))
        engagement_total = payload.likes + payload.comments + payload.shares + payload.saves
        engagement_rate = _safe_rate(engagement_total, max(payload.views, 1))
        ctr = _safe_rate(payload.clicks, max(payload.views, 1))
        conversion_rate = _safe_rate(payload.conversions, max(payload.clicks, 1))
        roi = _safe_rate(payload.revenue - payload.spend, max(payload.spend, 1))

        record = {
            'id': len(ctx.performance_memory) + 1,
            'tenant_id': auth.tenant_id,
            'trend_id': payload.trend_id,
            'content_id': payload.content_id,
            'channel': payload.channel.strip().lower(),
            'posted_at': posted_at.isoformat(),
            'likes': payload.likes,
            'comments': payload.comments,
            'shares': payload.shares,
            'saves': payload.saves,
            'views': payload.views,
            'clicks': payload.clicks,
            'conversions': payload.conversions,
            'spend': round(payload.spend, 2),
            'revenue': round(payload.revenue, 2),
            'watch_time_seconds': payload.watch_time_seconds,
            'not_viewed_reasons': payload.not_viewed_reasons,
            'engagement_rate': round(engagement_rate, 6),
            'ctr': round(ctr, 6),
            'conversion_rate': round(conversion_rate, 6),
            'roi': round(roi, 6),
            'created_at': datetime.now(UTC).isoformat(),
        }

        with ctx.lock:
            ctx.performance_memory.append(record)
            tenant_perf = [p for p in ctx.performance_memory if p.get('tenant_id') == auth.tenant_id]
        diagnostics = _build_performance_diagnostics(tenant_perf, engagement_rate)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'performance': record, 'diagnostics': diagnostics}


def _register_content_routes(router: APIRouter, ctx: _TrendCtx) -> None:
    _register_content_generate_route(router, ctx)
    _register_performance_track_route(router, ctx)


def _register_analytics_routes(router: APIRouter, ctx: _TrendCtx) -> None:
    @router.get('/trends/analytics/dashboard')
    def trend_analytics_dashboard(
        auth: AuthDep,
        trend_id: str | None = None,
        days: Annotated[int, Query(ge=7, le=180)] = 30,
    ) -> dict[str, Any]:
        ctx.enforce_rate_limit(f'{auth.tenant_id}:trends:analytics:dashboard', 120, 60)
        now = datetime.now(UTC)
        cutoff = now - timedelta(days=days)
        with ctx.lock:
            forecasts = [f.copy() for f in ctx.forecasts_memory if f.get('tenant_id') == auth.tenant_id]
            perf = [
                p.copy()
                for p in ctx.performance_memory
                if p.get('tenant_id') == auth.tenant_id and _to_dt(str(p.get('posted_at')), now) >= cutoff
            ]
        if trend_id:
            forecasts = [f for f in forecasts if f.get('trend_id') == trend_id]
            perf = [p for p in perf if p.get('trend_id') == trend_id]

        analytics = _aggregate_analytics(forecasts, perf, days)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, **analytics}

    @router.get('/trends/analytics/indicators')
    def trend_performance_indicators(
        auth: AuthDep,
        trend_id: str | None = None,
        days: Annotated[int, Query(ge=7, le=180)] = 30,
    ) -> dict[str, Any]:
        ctx.enforce_rate_limit(f'{auth.tenant_id}:trends:analytics:indicators', 120, 60)
        now = datetime.now(UTC)
        cutoff = now - timedelta(days=days)
        with ctx.lock:
            forecasts = [f.copy() for f in ctx.forecasts_memory if f.get('tenant_id') == auth.tenant_id]
            perf = [
                p.copy()
                for p in ctx.performance_memory
                if p.get('tenant_id') == auth.tenant_id and _to_dt(str(p.get('posted_at')), now) >= cutoff
            ]
        if trend_id:
            forecasts = [f for f in forecasts if f.get('trend_id') == trend_id]
            perf = [p for p in perf if p.get('trend_id') == trend_id]

        analytics = _aggregate_analytics(forecasts, perf, days)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'window_days': days,
            'kpi': analytics['kpi'],
            'performance_indicators': analytics['performance_indicators'],
        }


def _register_recommendation_routes(router: APIRouter, ctx: _TrendCtx) -> None:
    @router.get('/trends/recommendations', responses={404: {'description': 'No trend forecast data available.'}})
    def trend_recommendations(auth: AuthDep, trend_id: str | None = None) -> dict[str, Any]:
        ctx.enforce_rate_limit(f'{auth.tenant_id}:trends:recommendations', 120, 60)
        now = datetime.now(UTC)
        with ctx.lock:
            forecasts = [f for f in ctx.forecasts_memory if f.get('tenant_id') == auth.tenant_id]
            perf = [p for p in ctx.performance_memory if p.get('tenant_id') == auth.tenant_id]
        if trend_id:
            forecasts = [f for f in forecasts if f.get('trend_id') == trend_id]
            perf = [p for p in perf if p.get('trend_id') == trend_id]
        if not forecasts:
            raise HTTPException(status_code=404, detail='No trend forecast data available. Generate forecast first.')

        forecasts_sorted = sorted(
            forecasts,
            key=lambda row: (float(row.get('trend_strength') or 0.0), float(row.get('roi_score') or 0.0)),
            reverse=True,
        )
        items = [_recommendation_item(forecast, perf, now) for forecast in forecasts_sorted[:10]]

        with ctx.lock:
            ctx.recommendations_memory.append(
                {'id': len(ctx.recommendations_memory) + 1, 'tenant_id': auth.tenant_id, 'created_at': now.isoformat(), 'items': items}
            )
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'items': items}


def create_trend_intelligence_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    signals_memory: list[dict[str, Any]],
    forecasts_memory: list[dict[str, Any]],
    selections_memory: list[dict[str, Any]],
    content_memory: list[dict[str, Any]],
    performance_memory: list[dict[str, Any]],
    recommendations_memory: list[dict[str, Any]],
) -> APIRouter:
    router = APIRouter()
    ctx = _TrendCtx(
        enforce_rate_limit=enforce_rate_limit,
        signals_memory=signals_memory,
        forecasts_memory=forecasts_memory,
        selections_memory=selections_memory,
        content_memory=content_memory,
        performance_memory=performance_memory,
        recommendations_memory=recommendations_memory,
        lock=threading.Lock(),
    )
    _register_signal_routes(router, ctx)
    _register_forecast_routes(router, ctx)
    _register_content_routes(router, ctx)
    _register_analytics_routes(router, ctx)
    _register_recommendation_routes(router, ctx)
    return router
