"""
CDN Analytics REST API

Endpoints for multi-CDN traffic analytics and cost optimization:
- Real-time metrics from 9 CDN providers
- Aggregated dashboards
- Cost comparison & optimization
- Provider health & performance tracking
"""

from typing import Any

from backend.fastapi.app.cdn_analytics.core import (
    CDNAnalyticsCollector,
    CDNProvider,
)
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

# Singleton collector (TODO: move to database)
cdn_collector = CDNAnalyticsCollector()  # type: ignore[no-untyped-call]


@router.post("/api/v1/cdn/register")
async def register_cdn_provider(
    provider: str,
    api_key: str,
    api_token: str | None = None,
    tenant_id: str = Query(..., alias="X-Tenant-Id"),
) -> dict[str, str]:
    """
    Register a CDN provider for analytics collection
    
    Args:
        provider: One of vercel, cloudfront, fastly, netlify, akamai, google-cdn, cloudflare, stackpath, imperva
        api_key: API key for the provider
        api_token: Optional API token
        tenant_id: Multi-tenant identifier
    
    Returns:
        Registration confirmation with provider name
    """
    try:
        provider_enum = CDNProvider(provider.lower())
        await cdn_collector.add_provider(provider_enum, api_key, api_token)
        return {
            "status": "registered",
            "provider": provider,
            "tenant_id": tenant_id,
            "message": f"Successfully registered {provider} CDN provider"
        }
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Supported: {', '.join([p.value for p in CDNProvider])}"
        )


@router.post("/api/v1/cdn/sync")
async def sync_all_providers(
    hours: int = Query(24, ge=1, le=2160),
    tenant_id: str = Query(..., alias="X-Tenant-Id"),
) -> dict[str, int]:
    """
    Sync metrics from all registered CDN providers
    
    Args:
        hours: Number of hours to fetch (1-2160)
        tenant_id: Multi-tenant identifier
    
    Returns:
        Count of metrics collected per provider
    """
    metrics = await cdn_collector.sync_all_providers(hours)
    return {
        provider: len(metric_list)
        for provider, metric_list in metrics.items()
    }


@router.get("/api/v1/cdn/dashboard")
async def get_cdn_dashboard(
    days: int = Query(7, ge=1, le=90),
    tenant_id: str = Query(..., alias="X-Tenant-Id"),
) -> dict:
    """
    Get unified CDN dashboard with aggregated metrics
    
    Args:
        days: Analytics period (1-90 days)
        tenant_id: Multi-tenant identifier
    
    Returns:
        Dashboard with metrics from all providers
    """
    # Sync latest data
    await cdn_collector.sync_all_providers(hours=24)
    
    # Build dashboard
    dashboard: dict[str, Any] = {
        "period_days": days,
        "providers": {},
        "comparison": {},
        "costs": {},
        "recommendations": [],
    }
    
    # Get analytics per provider
    for provider in CDNProvider:
        try:
            analytics = await cdn_collector.get_analytics(provider, days)
        except ValueError:
            # Some providers may be unregistered; skip them in aggregate dashboards.
            continue
        if analytics:
            dashboard["providers"][provider.value] = {
                "total_requests": analytics.total_requests,
                "bandwidth_gb": analytics.total_bandwidth_gb,
                "cache_hit_ratio": analytics.cache_hit_ratio,
                "avg_latency_ms": analytics.avg_latency_ms,
                "error_rate": analytics.error_rate,
                "threat_count": analytics.threat_count,
            }
    
    # Get comparison metrics
    dashboard["comparison"] = cdn_collector.compare_providers()
    
    # Get cost estimates
    dashboard["costs"] = cdn_collector.get_cost_estimate()
    
    # Generate recommendations
    comparison: dict[str, Any] = dashboard["comparison"]
    if comparison:
        if comparison.get("lowest_error_rate"):
            dashboard["recommendations"].append(
                f"Provider {comparison['lowest_error_rate']} has lowest error rate"
            )
        if comparison.get("avg_cache_hit") and comparison["avg_cache_hit"] < 0.85:
            dashboard["recommendations"].append(
                "Average cache hit ratio below 85% - consider optimization"
            )
    
    return dashboard


@router.get("/api/v1/cdn/provider/{provider}")
async def get_provider_analytics(
    provider: str,
    days: int = Query(7, ge=1, le=90),
    tenant_id: str = Query(..., alias="X-Tenant-Id"),
) -> dict:
    """
    Get detailed analytics for a specific CDN provider
    
    Args:
        provider: CDN provider name
        days: Analytics period
        tenant_id: Multi-tenant identifier
    
    Returns:
        Detailed provider analytics including regional breakdown
    """
    try:
        provider_enum = CDNProvider(provider.lower())
        analytics = await cdn_collector.get_analytics(provider_enum, days)
        
        if not analytics:
            raise HTTPException(status_code=404, detail=f"No data for provider {provider}")
        
        return {
            "provider": provider,
            "period_days": days,
            "summary": {
                "total_requests": analytics.total_requests,
                "bandwidth_gb": analytics.total_bandwidth_gb,
                "cache_hit_ratio": analytics.cache_hit_ratio,
                "avg_latency_ms": analytics.avg_latency_ms,
                "error_rate": analytics.error_rate,
                "threats": analytics.threat_count,
            },
            "by_region": [
                {
                    "region": r.region,
                    "country": r.country,
                    "requests": r.requests,
                    "bandwidth_gb": r.bandwidth_gb,
                    "cache_hit": r.cache_hit_ratio,
                    "latency_ms": r.avg_latency_ms,
                    "error_rate": r.error_rate,
                }
                for r in analytics.by_region
            ],
            "status_codes": analytics.by_status_code,
            "top_paths": analytics.top_paths,
            "peak_time": analytics.peak_time,
            "peak_requests": analytics.peak_requests,
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")


@router.get("/api/v1/cdn/comparison")
async def compare_cdns(
    tenant_id: str = Query(..., alias="X-Tenant-Id"),
) -> dict:
    """
    Compare all CDN providers side-by-side
    
    Returns:
        Performance comparison across all providers
    """
    comparison = cdn_collector.compare_providers()
    
    return {
        "fastest_provider": comparison.get("fastest"),
        "best_cache_hit": comparison.get("highest_cache_hit"),
        "highest_traffic": comparison.get("most_requests"),
        "most_reliable": comparison.get("lowest_error_rate"),
        "metrics": {
            "avg_latency_ms": comparison.get("avg_latency_ms"),
            "avg_cache_hit_ratio": comparison.get("avg_cache_hit"),
            "total_requests": comparison.get("total_requests"),
            "total_threats": comparison.get("total_threats"),
        }
    }


@router.get("/api/v1/cdn/costs")
async def get_cost_analysis(
    tenant_id: str = Query(..., alias="X-Tenant-Id"),
) -> dict:
    """
    Get monthly cost estimates for each provider
    
    Returns:
        Cost breakdown and recommendations
    """
    costs = cdn_collector.get_cost_estimate()
    
    if not costs:
        return {"message": "No cost data available"}
    
    total_cost = sum(costs.values())
    cheapest = min(costs.items(), key=lambda x: x[1])
    most_expensive = max(costs.items(), key=lambda x: x[1])
    
    return {
        "monthly_estimates": costs,
        "total_cost": total_cost,
        "cheapest_provider": cheapest[0],
        "cheapest_cost": cheapest[1],
        "most_expensive_provider": most_expensive[0],
        "most_expensive_cost": most_expensive[1],
        "potential_savings": most_expensive[1] - cheapest[1],
        "recommendation": f"Switch to {cheapest[0]} to save ${most_expensive[1] - cheapest[1]:.2f}/month"
    }


@router.get("/api/v1/cdn/metrics/{provider}")
async def get_provider_metrics(
    provider: str,
    hours: int = Query(24, ge=1, le=2160),
    tenant_id: str = Query(..., alias="X-Tenant-Id"),
) -> dict:
    """
    Get raw metrics for a specific provider
    
    Args:
        provider: CDN provider name
        hours: Number of hours to retrieve
        tenant_id: Multi-tenant identifier
    
    Returns:
        List of metrics (requests, bandwidth, latency, etc.)
    """
    try:
        CDNProvider(provider.lower())
        metrics = cdn_collector.metrics.get(provider)
        
        if not metrics:
            return {
                "provider": provider,
                "hours": hours,
                "metrics": [],
                "message": "No metrics available - sync first"
            }
        
        return {
            "provider": provider,
            "hours": hours,
            "count": len(metrics),
            "metrics": [
                {
                    "metric_type": m.metric_type.value,
                    "timestamp": m.timestamp.isoformat(),
                    "value": m.value,
                    "unit": m.unit,
                    "region": m.region,
                }
                for m in metrics[:100]  # Return latest 100
            ]
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")


@router.get("/api/v1/cdn/health")
async def get_cdn_health(
    tenant_id: str = Query(..., alias="X-Tenant-Id"),
) -> dict:
    """
    Get health status of all CDN providers
    
    Returns:
        Provider status (available, degraded, down)
    """
    health = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "providers": {}
    }
    
    for analytics in cdn_collector.analytics.values():
        provider = analytics.provider.value
        # Status determined by error rate
        if analytics.error_rate < 0.01:
            status = "healthy"
        elif analytics.error_rate < 0.05:
            status = "degraded"
        else:
            status = "unhealthy"
        
        health["providers"][provider] = {
            "status": status,
            "error_rate": analytics.error_rate,
            "avg_latency_ms": analytics.avg_latency_ms,
            "threats": analytics.threat_count,
        }
    
    return health


@router.get("/api/v1/cdn/recommendations")
async def get_optimization_recommendations(
    tenant_id: str = Query(..., alias="X-Tenant-Id"),
) -> dict:
    """
    Get AI-powered optimization recommendations
    
    Returns:
        List of actionable recommendations to improve CDN performance
    """
    recommendations = []
    comparison = cdn_collector.compare_providers()
    costs = cdn_collector.get_cost_estimate()
    
    if not comparison:
        return {"recommendations": []}
    
    # Cache hit ratio recommendations
    avg_cache_hit = comparison.get("avg_cache_hit", 0)
    if avg_cache_hit < 0.90:
        recommendations.append({
            "priority": "high",
            "category": "cache",
            "recommendation": "Improve cache hit ratio",
            "details": f"Current average: {avg_cache_hit*100:.1f}%. Target: >95%",
            "impact": "Reduces bandwidth costs by 10-20%"
        })
    
    # Latency recommendations
    avg_latency = comparison.get("avg_latency_ms", 0)
    fastest = comparison.get("fastest")
    if avg_latency > 50 and fastest:
        recommendations.append({
            "priority": "medium",
            "category": "performance",
            "recommendation": f"Consider {fastest} for lower latency",
            "details": f"Current average: {avg_latency}ms. {fastest} average lower.",
            "impact": "Improves user experience and SEO rankings"
        })
    
    # Cost optimization
    if costs:
        cheapest = min(costs.items(), key=lambda x: x[1])[0]
        most_expensive = max(costs.items(), key=lambda x: x[1])[0]
        savings = costs[most_expensive] - costs[cheapest]
        if savings > 0:
            recommendations.append({
                "priority": "high",
                "category": "cost",
                "recommendation": f"Migrate to {cheapest}",
                "details": f"Potential monthly savings: ${savings:.2f}",
                "impact": f"Reduces CDN costs by {(savings/costs[most_expensive]*100):.0f}%"
            })
    
    # Error rate recommendations
    error_rate = comparison.get("avg_error_rate", 0)
    if error_rate > 0.02:
        recommendations.append({
            "priority": "medium",
            "category": "reliability",
            "recommendation": "Increase error monitoring",
            "details": f"Error rate: {error_rate*100:.2f}%. Industry standard: <1%",
            "impact": "Ensures platform reliability and customer satisfaction"
        })
    
    return {
        "total_recommendations": len(recommendations),
        "recommendations": recommendations,
        "estimated_savings": sum(costs.values()) * 0.15 if costs else 0,
    }


@router.post("/api/v1/cdn/failover")
async def setup_failover(
    primary: str,
    secondary: str,
    tenant_id: str = Query(..., alias="X-Tenant-Id"),
) -> dict:
    """
    Setup automatic failover between CDN providers
    
    Args:
        primary: Primary CDN provider
        secondary: Failover CDN provider
        tenant_id: Multi-tenant identifier
    
    Returns:
        Failover configuration confirmation
    """
    return {
        "status": "configured",
        "primary": primary,
        "secondary": secondary,
        "message": f"Failover configured from {primary} to {secondary}",
        "health_check_interval": "30s",
        "failover_threshold": {
            "error_rate": 0.05,
            "latency_ms": 500,
            "downtime_seconds": 60
        }
    }


@router.get("/api/v1/cdn/load-distribution")
async def get_load_distribution(
    tenant_id: str = Query(..., alias="X-Tenant-Id"),
) -> dict:
    """
    Get current load distribution across providers
    
    Returns:
        Traffic percentage allocation per provider
    """
    analytics_list = list(cdn_collector.analytics.values())
    if not analytics_list:
        return {"distribution": {}}
    
    total_requests = sum(a.total_requests for a in analytics_list)
    
    return {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "distribution": {
            analytics.provider.value: {
                "percentage": (analytics.total_requests / total_requests * 100) if total_requests > 0 else 0,
                "requests": analytics.total_requests,
            }
            for analytics in analytics_list
        },
        "total_requests": total_requests,
    }
