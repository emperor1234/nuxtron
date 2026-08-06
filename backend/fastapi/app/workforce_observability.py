"""
Autonomous Workforce Observability

Tracks metrics for mission execution, provider performance, and agent health:
- Mission success/failure rates
- Provider action latency and error rates
- Retry queue depth and aging
- Tool execution times
- Artifact generation latency
- End-to-end mission completion time
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel


class MetricPoint:
    """Single metric measurement."""

    def __init__(self, name: str, value: float, labels: dict[str, str] | None = None, timestamp: datetime | None = None):
        self.name = name
        self.value = value
        self.labels = labels or {}
        self.timestamp = timestamp or datetime.now(UTC)


class MetricsCollector:
    """In-memory metrics collection and aggregation."""

    def __init__(self):
        self.metrics: dict[str, list[MetricPoint]] = defaultdict(list)
        self.aggregates: dict[str, dict[str, Any]] = {}
        self._lock = None  # Optional thread lock

    def record(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Record a metric point."""
        point = MetricPoint(name, value, labels)
        self.metrics[name].append(point)

        # Keep only last 1000 points per metric to avoid memory bloat
        if len(self.metrics[name]) > 1000:
            self.metrics[name] = self.metrics[name][-1000:]

    def record_duration(self, name: str, seconds: float, labels: dict[str, str] | None = None) -> None:
        """Record timing metric (in seconds)."""
        self.record(f"{name}_seconds", seconds, labels)

    def record_counter(self, name: str, amount: int = 1, labels: dict[str, str] | None = None) -> None:
        """Record counter metric."""
        self.record(name, float(amount), labels)

    def get_metric_summary(self, name: str, time_window_minutes: int = 60) -> dict[str, Any]:
        """Get summary statistics for a metric."""
        cutoff_time = datetime.now(UTC) - timedelta(minutes=time_window_minutes)
        points = [p for p in self.metrics.get(name, []) if p.timestamp >= cutoff_time]

        if not points:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}

        values = [p.value for p in points]
        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "p50": sorted(values)[len(values) // 2],
            "p95": sorted(values)[int(len(values) * 0.95)],
            "p99": sorted(values)[int(len(values) * 0.99)],
        }

    def get_dashboard(self, time_window_minutes: int = 60) -> dict[str, Any]:
        """Get complete observability dashboard."""
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "window_minutes": time_window_minutes,
            "mission_success_rate": self.get_metric_summary("mission_success", time_window_minutes),
            "mission_duration": self.get_metric_summary("mission_duration_seconds", time_window_minutes),
            "artifact_generation_latency": self.get_metric_summary("artifact_generation_seconds", time_window_minutes),
            "provider_action_latency": self.get_metric_summary("provider_action_seconds", time_window_minutes),
            "retry_queue_depth": self.get_metric_summary("retry_queue_depth", time_window_minutes),
            "tool_execution_latency": self.get_metric_summary("tool_execution_seconds", time_window_minutes),
        }

    def get_provider_stats(self, provider: str, time_window_minutes: int = 60) -> dict[str, Any]:
        """Get performance stats for a provider."""
        cutoff_time = datetime.now(UTC) - timedelta(minutes=time_window_minutes)
        provider_metrics = [
            p
            for p in self.metrics.get("provider_action_seconds", [])
            if p.timestamp >= cutoff_time and p.labels.get("provider") == provider
        ]

        if not provider_metrics:
            return {"provider": provider, "call_count": 0}

        values = [p.value for p in provider_metrics]
        success_points = [p for p in provider_metrics if p.labels.get("status") == "success"]

        return {
            "provider": provider,
            "call_count": len(provider_metrics),
            "success_rate": len(success_points) / len(provider_metrics) if provider_metrics else 0,
            "avg_latency_seconds": sum(values) / len(values),
            "p95_latency_seconds": sorted(values)[int(len(values) * 0.95)] if values else 0,
        }

    def get_all_provider_stats(self, time_window_minutes: int = 60) -> list[dict[str, Any]]:
        """Get stats for all providers."""
        providers = set()
        for point in self.metrics.get("provider_action_seconds", []):
            if provider := point.labels.get("provider"):
                providers.add(provider)

        return [self.get_provider_stats(p, time_window_minutes) for p in sorted(providers)]


class MissionExecutionTimer:
    """Context manager for timing mission execution."""

    def __init__(self, metrics: MetricsCollector, mission_id: str, role: str):
        self.metrics = metrics
        self.mission_id = mission_id
        self.role = role
        self.start_time = 0.0

    def __enter__(self) -> MissionExecutionTimer:
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration = time.time() - self.start_time
        labels = {"mission_id": self.mission_id, "role": self.role, "status": "success" if exc_type is None else "error"}
        self.metrics.record_duration("mission_duration", duration, labels)


class ProviderActionTimer:
    """Context manager for timing provider actions."""

    def __init__(self, metrics: MetricsCollector, provider: str, action: str):
        self.metrics = metrics
        self.provider = provider
        self.action = action
        self.start_time = 0.0

    def __enter__(self) -> ProviderActionTimer:
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration = time.time() - self.start_time
        labels = {"provider": self.provider, "action": self.action, "status": "success" if exc_type is None else "error"}
        self.metrics.record_duration("provider_action", duration, labels)


class MetricsEndpointModels:
    """Pydantic models for metrics API."""

    class MetricSummaryResponse(BaseModel):
        count: int
        sum: float
        avg: float
        min: float
        max: float
        p50: float
        p95: float
        p99: float

    class DashboardResponse(BaseModel):
        timestamp: str
        window_minutes: int
        mission_success_rate: dict[str, Any]
        mission_duration: dict[str, Any]
        artifact_generation_latency: dict[str, Any]
        provider_action_latency: dict[str, Any]
        retry_queue_depth: dict[str, Any]
        tool_execution_latency: dict[str, Any]

    class ProviderStatsResponse(BaseModel):
        provider: str
        call_count: int
        success_rate: float = 0.0
        avg_latency_seconds: float = 0.0
        p95_latency_seconds: float = 0.0
