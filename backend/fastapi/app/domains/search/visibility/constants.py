"""Search/Visibility constants and configuration vocabulary."""

from __future__ import annotations
from ....deps import AuthContext
from ....deps import require_auth
from fastapi import Depends
from typing import Annotated

AuthDep = Annotated[AuthContext, Depends(require_auth)]

StoreItem = dict[str, object]

StoreList = list[StoreItem]

TRIGGER_EPISTEMIC_CURIOSITY = "Epistemic Curiosity"

TRIGGER_IDENTITY_SIGNAL = "Identity Signal"

TRIGGER_SOCIAL_CURRENCY = "Social Currency"

TRIGGER_EMOTIONAL_AROUSAL = "Emotional Arousal"

TRIGGER_PRACTICAL_UTILITY = "Practical Utility"

LOW_MEDIUM_HIGH_DESC = "low|medium|high"

VSE_ENGINES: list[dict] = [
    {
        "id": "VSE-1",
        "name": "Psychological Ignition Matrix",
        "class": "SINGULARITY",
        "automation_pct": 97,
        "triggers": 247,
    },
    {
        "id": "VSE-2",
        "name": "Algorithmic Gravity System",
        "class": "SINGULARITY",
        "automation_pct": 99,
        "platforms": 25,
    },
    {"id": "VSE-3", "name": "Network Topology Detonator", "class": "QUANTUM", "automation_pct": 90, "accuracy_pct": 94},
    {
        "id": "VSE-4",
        "name": "Cross-Platform Detonation Matrix",
        "class": "SINGULARITY",
        "automation_pct": 99,
        "platforms": 25,
    },
    {
        "id": "VSE-5",
        "name": "Influencer Swarm Activator",
        "class": "APEX",
        "automation_pct": 92,
        "database_size": 12000000,
    },
    {
        "id": "VSE-6",
        "name": "Real-Time Viral Momentum Engine",
        "class": "SINGULARITY",
        "automation_pct": 95,
        "signals_monitored": 47,
    },
    {
        "id": "VSE-7",
        "name": "Viral Content Factory",
        "class": "APEX",
        "automation_pct": 95,
        "avg_viral_prob_score": 91.3,
    },
    {
        "id": "VSE-8",
        "name": "Emotional Contagion Amplifier",
        "class": "QUANTUM",
        "automation_pct": 93,
        "contagion_velocity": "3.4x",
    },
    {
        "id": "VSE-9",
        "name": "Real-Time Trend Hijack System",
        "class": "APEX",
        "automation_pct": 95,
        "detection_seconds": 60,
    },
    {
        "id": "VSE-10",
        "name": "Viral Paid Amplification Matrix",
        "class": "APEX",
        "automation_pct": 98,
        "roas_improvement": "15-40x",
    },
    {
        "id": "VSE-11",
        "name": "Dark Social Penetration System",
        "class": "QUANTUM",
        "automation_pct": 80,
        "channel_types": 12,
    },
    {
        "id": "VSE-12",
        "name": "Viral Immortalisation Protocol",
        "class": "APEX",
        "automation_pct": 99,
        "assets_per_event": 18,
    },
]

VSE_SUBSYSTEMS: list[dict] = [
    {"id": "VS-01", "name": "Viral Brief Generator", "parent": "VSE-7", "automation_pct": 95},
    {"id": "VS-02", "name": "Psychological Trigger Matrix Selector", "parent": "VSE-1", "automation_pct": 97},
    {"id": "VS-03", "name": "Hook Testing Laboratory", "parent": "VSE-7", "automation_pct": 90},
    {"id": "VS-04", "name": "Optimal Timing Calculator", "parent": "VSE-2", "automation_pct": 95},
    {"id": "VS-05", "name": "Pre-Publication Cascade Simulation", "parent": "VSE-3", "automation_pct": 85},
    {"id": "VS-06", "name": "Coordinated Detonation Controller", "parent": "VSE-4", "automation_pct": 99},
    {"id": "VS-07", "name": "Engagement Velocity Guardian", "parent": "VSE-6", "automation_pct": 95},
    {"id": "VS-08", "name": "Comment Conversation Architect", "parent": "VSE-1", "automation_pct": 80},
    {"id": "VS-09", "name": "Real-Time Content Variants Deployer", "parent": "VSE-7", "automation_pct": 90},
    {"id": "VS-10", "name": "Media Ignition Activator", "parent": "VSE-6", "automation_pct": 75},
    {"id": "VS-11", "name": "Cultural Remix Facilitator", "parent": "VSE-8", "automation_pct": 70},
    {"id": "VS-12", "name": "Cross-Vertical Audience Bridge", "parent": "VSE-3", "automation_pct": 80},
    {"id": "VS-13", "name": "Second-Wave Engineering System", "parent": "VSE-6", "automation_pct": 85},
    {"id": "VS-14", "name": "Viral Suppression Counter-System", "parent": "VSE-2", "automation_pct": 95},
    {"id": "VS-15", "name": "Viral Autopsy System", "parent": "VSE-1", "automation_pct": 90},
    {"id": "VS-16", "name": "Competitor Viral Intelligence", "parent": "VSE-9", "automation_pct": 88},
    {"id": "VS-17", "name": "Audience Viral Appetite Tracker", "parent": "VSE-8", "automation_pct": 92},
    {"id": "VS-18", "name": "Dark Social Measurement Network", "parent": "VSE-11", "automation_pct": 80},
    {"id": "VS-19", "name": "WhatsApp Status Seeding Engine", "parent": "VSE-11", "automation_pct": 75},
    {"id": "VS-20", "name": "Private Community Seeding Network", "parent": "VSE-11", "automation_pct": 60},
    {"id": "VS-21", "name": "Viral Paid Activation Trigger", "parent": "VSE-10", "automation_pct": 98},
    {"id": "VS-22", "name": "Lookalike Seed Audience Builder", "parent": "VSE-10", "automation_pct": 95},
    {"id": "VS-23", "name": "Budget Velocity Allocator", "parent": "VSE-10", "automation_pct": 99},
    {"id": "VS-24", "name": "AI Citation Harvesting Protocol", "parent": "VSE-12", "automation_pct": 85},
    {"id": "VS-25", "name": "SEO Immortalisation Converter", "parent": "VSE-12", "automation_pct": 88},
    {"id": "VS-26", "name": "Wikipedia Citation Submitter", "parent": "VSE-12", "automation_pct": 70},
    {"id": "VS-27", "name": "Viral Content Syndication Engine", "parent": "VSE-12", "automation_pct": 85},
    {"id": "VS-28", "name": "Emotional Arousal Calibrator", "parent": "VSE-8", "automation_pct": 93},
    {"id": "VS-29", "name": "Moral Elevation Architect", "parent": "VSE-8", "automation_pct": 80},
    {"id": "VS-30", "name": "Comment Sentiment Volcano Monitor", "parent": "VSE-6", "automation_pct": 97},
    {"id": "VS-31", "name": "Trending Topic Signal Monitor", "parent": "VSE-9", "automation_pct": 99},
    {"id": "VS-32", "name": "Trend Authenticity Validator", "parent": "VSE-9", "automation_pct": 85},
    {"id": "VS-33", "name": "Trend Timing Precision Scheduler", "parent": "VSE-9", "automation_pct": 95},
    {"id": "VS-34", "name": "Influencer Fraud Detection Gate", "parent": "VSE-5", "automation_pct": 90},
    {"id": "VS-35", "name": "Influencer Pre-Warming System", "parent": "VSE-5", "automation_pct": 80},
    {"id": "VS-36", "name": "Swarm Composition Optimiser", "parent": "VSE-5", "automation_pct": 92},
    {"id": "VS-37", "name": "Long-Term Influencer Relationship Engine", "parent": "VSE-5", "automation_pct": 70},
    {"id": "VS-38", "name": "Social Graph Topology Mapper", "parent": "VSE-3", "automation_pct": 85},
    {"id": "VS-39", "name": "Bridge Node Identifier", "parent": "VSE-3", "automation_pct": 88},
    {"id": "VS-40", "name": "Cascade Propagation Simulator", "parent": "VSE-3", "automation_pct": 90},
    {"id": "VS-41", "name": "Algorithm Update Detection System", "parent": "VSE-2", "automation_pct": 99},
    {"id": "VS-42", "name": "Shadow-Ban Detection Protocol", "parent": "VSE-2", "automation_pct": 95},
    {"id": "VS-43", "name": "Platform Signal Optimiser", "parent": "VSE-2", "automation_pct": 97},
    {"id": "VS-44", "name": "Brand Authenticity Viral Gate", "parent": "VSE-7", "automation_pct": 99},
    {"id": "VS-45", "name": "Viral Probability Scorer", "parent": "VSE-7", "automation_pct": 95},
    {"id": "VS-46", "name": "Viral Half-Life Predictor", "parent": "VSE-6", "automation_pct": 87},
    {"id": "VS-47", "name": "Permanent Viral Asset Archive", "parent": "VSE-12", "automation_pct": 99},
]

PSYCHOLOGICAL_TRIGGERS: list[dict] = [
    {"id": 1, "name": TRIGGER_EPISTEMIC_CURIOSITY, "category": "cognitive", "share_lift": 2.1},
    {"id": 2, "name": TRIGGER_IDENTITY_SIGNAL, "category": "identity", "share_lift": 2.4},
    {"id": 3, "name": TRIGGER_SOCIAL_CURRENCY, "category": "social", "share_lift": 2.8},
    {"id": 4, "name": TRIGGER_EMOTIONAL_AROUSAL, "category": "emotional", "share_lift": 3.2},
    {"id": 5, "name": "Awe", "category": "emotional", "share_lift": 3.6},
    {"id": 6, "name": "Anger", "category": "emotional", "share_lift": 4.1},
    {"id": 7, "name": "Moral Elevation", "category": "moral", "share_lift": 2.9},
    {"id": 8, "name": TRIGGER_PRACTICAL_UTILITY, "category": "cognitive", "share_lift": 1.9},
    {"id": 9, "name": "Pattern Interruption", "category": "cognitive", "share_lift": 2.6},
    {"id": 10, "name": "FOMO", "category": "social", "share_lift": 3.1},
    {"id": 11, "name": "Social Proof", "category": "social", "share_lift": 2.3},
    {"id": 12, "name": "Controversy", "category": "cognitive", "share_lift": 4.8},
    {"id": 13, "name": "Inspiration", "category": "emotional", "share_lift": 2.7},
    {"id": 14, "name": "Nostalgia", "category": "emotional", "share_lift": 2.2},
    {"id": 15, "name": "Schadenfreude", "category": "emotional", "share_lift": 3.4},
    {"id": 16, "name": "Story Arc", "category": "narrative", "share_lift": 2.5},
    {"id": 17, "name": "Specific Numbers", "category": "cognitive", "share_lift": 2.0},
    {"id": 18, "name": "Authority Signal", "category": "social", "share_lift": 2.1},
    {"id": 19, "name": "Scarcity", "category": "cognitive", "share_lift": 2.3},
    {"id": 20, "name": "Reciprocity", "category": "social", "share_lift": 1.8},
]

PLATFORM_ALGORITHM_MODELS: list[dict] = [
    {
        "platform": "linkedin",
        "top_signals": ["comments", "shares", "dwell_time"],
        "golden_window": "Tue 07:00–09:00",
        "update_lag_hours": 48,
    },
    {
        "platform": "instagram",
        "top_signals": ["saves", "shares", "comments", "likes"],
        "golden_window": "Wed 11:00, Fri 14:00",
        "update_lag_hours": 48,
    },
    {
        "platform": "tiktok",
        "top_signals": ["completion_rate", "replay", "share"],
        "golden_window": "09:00–11:00, 19:00–21:00",
        "update_lag_hours": 48,
    },
    {
        "platform": "youtube",
        "top_signals": ["watch_pct", "clicks", "comments"],
        "golden_window": "Thu 17:00, Sat 11:00",
        "update_lag_hours": 72,
    },
    {
        "platform": "x",
        "top_signals": ["replies", "retweets", "quotes"],
        "golden_window": "Mon–Fri 12:00–13:00",
        "update_lag_hours": 24,
    },
    {
        "platform": "facebook",
        "top_signals": ["shares", "comments", "reactions"],
        "golden_window": "Wed–Thu 13:00–14:00",
        "update_lag_hours": 48,
    },
    {
        "platform": "pinterest",
        "top_signals": ["saves", "clicks", "close_ups"],
        "golden_window": "Sat–Sun 20:00–23:00",
        "update_lag_hours": 96,
    },
    {
        "platform": "reddit",
        "top_signals": ["upvotes", "comments", "awards"],
        "golden_window": "Mon–Fri 07:00–09:00",
        "update_lag_hours": 12,
    },
    {
        "platform": "threads",
        "top_signals": ["replies", "reposts", "likes"],
        "golden_window": "Daily 09:00–11:00",
        "update_lag_hours": 24,
    },
    {
        "platform": "snapchat",
        "top_signals": ["story_completions", "swipe_ups"],
        "golden_window": "Daily 12:00 and 19:00",
        "update_lag_hours": 24,
    },
]

TREND_SIGNALS: list[dict] = [
    {
        "id": 1,
        "topic": "AI regulation",
        "velocity": "breaking",
        "relevance": 0.92,
        "platform": "linkedin",
        "estimated_peak_window": "2h",
    },
    {
        "id": 2,
        "topic": "Creator economy 2026",
        "velocity": "building",
        "relevance": 0.87,
        "platform": "tiktok",
        "estimated_peak_window": "6h",
    },
    {
        "id": 3,
        "topic": "Remote work reversal",
        "velocity": "building",
        "relevance": 0.81,
        "platform": "x",
        "estimated_peak_window": "4h",
    },
    {
        "id": 4,
        "topic": "Dark social analytics",
        "velocity": "emerging",
        "relevance": 0.74,
        "platform": "linkedin",
        "estimated_peak_window": "12h",
    },
    {
        "id": 5,
        "topic": "Viral probability models",
        "velocity": "emerging",
        "relevance": 0.68,
        "platform": "reddit",
        "estimated_peak_window": "24h",
    },
]
