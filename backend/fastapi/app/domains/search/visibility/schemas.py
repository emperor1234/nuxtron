"""Search/Visibility request contracts."""

from __future__ import annotations
from .constants import LOW_MEDIUM_HIGH_DESC
from pydantic import BaseModel
from pydantic import Field


class ViralBriefRequest(BaseModel):
    objective: str = Field(..., description="High-level marketing objective")
    audience: str = Field(..., description="Target audience segment")
    platforms: list[str] = Field(default=["linkedin", "x", "instagram"])
    tone: str = Field(default="professional")
    urgency: str = Field(default="standard", description="standard|high|breaking")


class TriggerAnalyzeRequest(BaseModel):
    content: str = Field(..., description="Content text to analyze")
    platform: str = Field(default="linkedin")
    audience: str = Field(default="b2b professionals")


class AlgorithmOptimizeRequest(BaseModel):
    content: str = Field(..., description="Content to optimise")
    platform: str = Field(..., description="Target platform")
    content_type: str = Field(default="text", description="text|video|image|carousel")


class NetworkMapRequest(BaseModel):
    audience_segment: str = Field(..., description="Target audience segment to map")
    depth: int = Field(default=2, ge=1, le=3, description="Graph traversal depth")


class CascadeSimulateRequest(BaseModel):
    content_summary: str = Field(..., description="Summary of content to simulate")
    trigger_ids: list[int] = Field(default=[], description="Psychological trigger IDs to apply")
    platform: str = Field(default="linkedin")
    audience_size: int = Field(default=10000, ge=100)


class DetonationPlanRequest(BaseModel):
    content: str = Field(..., description="Core content to detonate")
    platforms: list[str] = Field(default=["linkedin", "x", "instagram", "tiktok"])
    target_launch_time: str | None = Field(default=None, description="ISO datetime or None for auto")
    objective: str = Field(default="reach")


class SwarmComposeRequest(BaseModel):
    post_summary: str = Field(..., description="Post content summary for swarm matching")
    niche: str = Field(..., description="Content niche/topic")
    platforms: list[str] = Field(default=["linkedin"])
    swarm_size: int = Field(default=50, ge=5, le=500)


class SwarmActivateRequest(BaseModel):
    swarm_id: str
    post_url: str | None = Field(default=None)
    activation_note: str | None = Field(default=None)


class MomentumStartRequest(BaseModel):
    post_url: str | None = Field(default=None)
    post_summary: str = Field(...)
    platform: str = Field(default="linkedin")
    target_viral_threshold: int = Field(default=50, ge=1)


class MomentumInjectRequest(BaseModel):
    injection_type: str = Field(..., description="comment_campaign|influencer_tier2|paid_boost|cross_platform")
    intensity: str = Field(default="medium", description=LOW_MEDIUM_HIGH_DESC)


class ViralContentRequest(BaseModel):
    topic: str = Field(...)
    objective: str = Field(default="reach", description="reach|conversion|engagement|authority")
    platform: str = Field(default="linkedin")
    format: str = Field(default="auto", description="auto|thread|carousel|short_video|infographic")
    emotional_vector: str = Field(default="curiosity", description="curiosity|awe|inspiration|anger|identity")
    trigger_ids: list[int] = Field(default=[], description="Specific trigger IDs to apply")
    avoid_duplicates: bool = Field(default=True, description="If true, auto-remix when similar content exists")
    uniqueness_boost: str = Field(default="medium", description=LOW_MEDIUM_HIGH_DESC)


class ViralContentVariantsRequest(BaseModel):
    topic: str = Field(...)
    objective: str = Field(default="reach", description="reach|conversion|engagement|authority")
    platform: str = Field(default="linkedin")
    format: str = Field(default="auto", description="auto|thread|carousel|short_video|infographic")
    emotional_vector: str = Field(default="curiosity", description="curiosity|awe|inspiration|anger|identity")
    trigger_ids: list[int] = Field(default=[])
    count: int = Field(default=3, ge=2, le=8)


class HooksRequest(BaseModel):
    topic: str = Field(...)
    platform: str = Field(default="linkedin")
    count: int = Field(default=50, ge=5, le=50)


class ContentScoreRequest(BaseModel):
    content: str = Field(...)
    platform: str = Field(default="linkedin")
    trigger_ids: list[int] = Field(default=[])


class EmotionAnalyzeRequest(BaseModel):
    content: str = Field(...)
    target_emotion: str | None = Field(default=None)


class EmotionEngineerRequest(BaseModel):
    content: str = Field(...)
    target_vector: str = Field(
        default="inspiration", description="awe|anger|inspiration|curiosity|identity|moral_elevation"
    )
    intensity: str = Field(default="medium", description=LOW_MEDIUM_HIGH_DESC)


class TrendHijackRequest(BaseModel):
    trend_id: int = Field(..., description="Trend ID from /vse/trends/live")
    brand_voice: str = Field(default="professional")
    platform: str = Field(default="linkedin")
    content_angle: str | None = Field(default=None)


class PaidAssessRequest(BaseModel):
    post_id: str | None = Field(default=None)
    post_summary: str = Field(...)
    organic_engagement_rate: float = Field(..., ge=0, le=100, description="Current organic ER %")
    organic_impressions: int = Field(default=0)
    minutes_live: int = Field(default=30, ge=1)


class PaidAmplifyRequest(BaseModel):
    assessment_id: str
    budget_gbp: float = Field(..., ge=1)
    platforms: list[str] = Field(default=["linkedin"])
    objective: str = Field(default="reach")


class DarkSocialSeedRequest(BaseModel):
    content: str = Field(...)
    channel_types: list[str] = Field(default=["whatsapp", "slack", "discord"])
    niche_communities: list[str] = Field(default=[])
    forwarding_hook: str | None = Field(default=None)


class DarkSocialAttributionRequest(BaseModel):
    campaign_id: str
    touchpoints: list[str] = Field(default=[])
    conversions: int = Field(default=0, ge=0)
    conversion_value: float = Field(default=0.0, ge=0.0)


class ImmortaliseRequest(BaseModel):
    viral_event_id: str
    post_summary: str = Field(...)
    viral_impressions: int = Field(..., ge=1000)
    platforms_achieved: list[str] = Field(default=[])
    key_insight: str | None = Field(default=None)
