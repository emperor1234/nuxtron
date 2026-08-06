# pyright: reportUnusedFunction=false

from __future__ import annotations

import hashlib
import secrets
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth
from ..integrations.vendor_manager import VendorCredentials, VendorType, get_vendor_manager

AuthDep = Annotated[AuthContext, Depends(require_auth)]

SUPPORTED_PLATFORMS = {
    "google_ads",
    "microsoft_ads",
    "amazon_ads",
    "apple_search_ads",
    "youtube_ads",
}

PLATFORM_META: dict[str, dict[str, str]] = {
    "google_ads": {
        "description": "Search and performance campaigns with broad reach across Google inventory.",
        "accent": "#4285F4",
    },
    "microsoft_ads": {
        "description": "Bing and Microsoft Audience ads for incremental CPC-efficient traffic.",
        "accent": "#00A4EF",
    },
    "amazon_ads": {
        "description": "Retail and marketplace ad placements focused on high-intent shoppers.",
        "accent": "#f59e0b",
    },
    "apple_search_ads": {
        "description": "App Store search placements optimized for mobile app acquisition.",
        "accent": "#cbd5e1",
    },
    "youtube_ads": {
        "description": "Video-first campaigns with skippable and in-feed ad placements.",
        "accent": "#ef4444",
    },
}

# Best-time lookup table keyed by platform → objective → data
# Heatmap keys: day abbreviation → hour (int) → engagement score 0-100
_BEST_TIME_TABLE: dict[str, dict[str, dict]] = {
    "google_ads": {
        "conversions": {
            "best_days": ["Tuesday", "Wednesday", "Thursday"],
            "heatmap": {
                "Mon": {8: 72, 9: 85, 10: 90, 11: 88, 12: 74, 14: 89, 15: 87, 16: 82},
                "Tue": {8: 78, 9: 92, 10: 96, 11: 94, 12: 78, 14: 93, 15: 91, 16: 86},
                "Wed": {8: 77, 9: 91, 10: 95, 11: 93, 12: 77, 14: 92, 15: 90, 16: 85},
                "Thu": {8: 75, 9: 89, 10: 93, 11: 91, 12: 75, 14: 90, 15: 88, 16: 83},
                "Fri": {8: 68, 9: 82, 10: 86, 11: 84, 12: 71, 14: 83, 15: 81, 16: 76},
                "Sat": {10: 44, 11: 48, 12: 52, 13: 50},
                "Sun": {10: 38, 11: 42, 12: 46, 13: 44},
            },
            "peak_hour": 10, "avoid_hours": [0, 1, 2, 3, 4, 22, 23],
            "human_review_window": [9, 10],
            "rationale": "B2B decision-makers research solutions mid-morning Tue–Thu before committing budgets. Avoid weekends and late nights.",
        },
        "brand_awareness": {
            "best_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "heatmap": {
                "Mon": {7: 68, 8: 80, 9: 88, 10: 85, 11: 82, 12: 76, 14: 80, 15: 78},
                "Tue": {7: 70, 8: 82, 9: 90, 10: 87, 11: 84, 12: 78, 14: 82, 15: 80},
                "Wed": {7: 69, 8: 81, 9: 89, 10: 86, 11: 83, 12: 77, 14: 81, 15: 79},
                "Thu": {7: 67, 8: 79, 9: 87, 10: 84, 11: 81, 12: 75, 14: 79, 15: 77},
                "Fri": {7: 60, 8: 72, 9: 78, 10: 76, 11: 74, 12: 69, 14: 74, 15: 72},
                "Sat": {10: 52, 11: 58, 12: 60, 13: 56},
                "Sun": {10: 45, 11: 50, 12: 52, 13: 48},
            },
            "peak_hour": 9, "avoid_hours": [0, 1, 2, 3, 4, 22, 23],
            "human_review_window": [8, 9],
            "rationale": "Brand impressions peak at workday start when users check news and email. Morning slots have 34% lower CPM.",
        },
        "traffic": {
            "best_days": ["Monday", "Tuesday", "Wednesday", "Thursday"],
            "heatmap": {
                "Mon": {7: 74, 8: 84, 9: 88, 10: 90, 11: 87, 12: 80, 13: 82, 14: 86, 15: 84, 16: 78},
                "Tue": {7: 76, 8: 86, 9: 90, 10: 92, 11: 89, 12: 82, 13: 84, 14: 88, 15: 86, 16: 80},
                "Wed": {7: 75, 8: 85, 9: 89, 10: 91, 11: 88, 12: 81, 13: 83, 14: 87, 15: 85, 16: 79},
                "Thu": {7: 73, 8: 83, 9: 87, 10: 89, 11: 86, 12: 79, 13: 81, 14: 85, 15: 83, 16: 77},
                "Fri": {7: 66, 8: 76, 9: 80, 10: 82, 11: 79, 12: 73, 14: 78, 15: 76, 16: 70},
                "Sat": {9: 48, 10: 54, 11: 58, 12: 62, 13: 60},
                "Sun": {9: 42, 10: 48, 11: 52, 12: 56, 13: 54},
            },
            "peak_hour": 10, "avoid_hours": [0, 1, 2, 3, 4, 5],
            "human_review_window": [9, 10],
            "rationale": "Search traffic peaks during commute and core office hours. Bidding 9–11am captures high-intent early sessions.",
        },
    },
    "microsoft_ads": {
        "conversions": {
            "best_days": ["Monday", "Tuesday", "Wednesday"],
            "heatmap": {
                "Mon": {8: 76, 9: 90, 10: 93, 11: 91, 12: 76, 14: 89, 15: 87, 16: 80},
                "Tue": {8: 78, 9: 92, 10: 95, 11: 93, 12: 78, 14: 91, 15: 89, 16: 82},
                "Wed": {8: 77, 9: 91, 10: 94, 11: 92, 12: 77, 14: 90, 15: 88, 16: 81},
                "Thu": {8: 72, 9: 86, 10: 89, 11: 87, 12: 72, 14: 85, 15: 83, 16: 76},
                "Fri": {8: 65, 9: 79, 10: 82, 11: 80, 12: 66, 14: 78, 15: 76, 16: 69},
                "Sat": {10: 36, 11: 40, 12: 44},
                "Sun": {10: 30, 11: 34, 12: 38},
            },
            "peak_hour": 10, "avoid_hours": [0, 1, 2, 3, 4, 20, 21, 22, 23],
            "human_review_window": [9, 10],
            "rationale": "Microsoft Ads skews enterprise/government. Decision-making peaks Mon–Wed during core business hours.",
        },
        "brand_awareness": {
            "best_days": ["Monday", "Tuesday", "Wednesday", "Thursday"],
            "heatmap": {
                "Mon": {8: 72, 9: 85, 10: 88, 11: 86, 12: 72, 14: 84, 15: 82},
                "Tue": {8: 74, 9: 87, 10: 90, 11: 88, 12: 74, 14: 86, 15: 84},
                "Wed": {8: 73, 9: 86, 10: 89, 11: 87, 12: 73, 14: 85, 15: 83},
                "Thu": {8: 69, 9: 82, 10: 85, 11: 83, 12: 70, 14: 81, 15: 79},
                "Fri": {8: 62, 9: 75, 10: 78, 11: 76, 12: 63, 14: 74, 15: 72},
                "Sat": {10: 34, 11: 38, 12: 42},
                "Sun": {10: 28, 11: 32, 12: 36},
            },
            "peak_hour": 10, "avoid_hours": [0, 1, 2, 3, 4, 21, 22, 23],
            "human_review_window": [9, 10],
            "rationale": "Brand reach on Microsoft's network is highest early in the workweek when professionals check industry news.",
        },
        "traffic": {
            "best_days": ["Monday", "Tuesday", "Wednesday", "Thursday"],
            "heatmap": {
                "Mon": {8: 74, 9: 87, 10: 90, 11: 88, 12: 74, 14: 86, 15: 84},
                "Tue": {8: 76, 9: 89, 10: 92, 11: 90, 12: 76, 14: 88, 15: 86},
                "Wed": {8: 75, 9: 88, 10: 91, 11: 89, 12: 75, 14: 87, 15: 85},
                "Thu": {8: 71, 9: 84, 10: 87, 11: 85, 12: 71, 14: 83, 15: 81},
                "Fri": {8: 64, 9: 77, 10: 80, 11: 78, 12: 65, 14: 76, 15: 74},
                "Sat": {10: 38, 11: 42, 12: 46},
                "Sun": {10: 32, 11: 36, 12: 40},
            },
            "peak_hour": 10, "avoid_hours": [0, 1, 2, 3, 4, 22, 23],
            "human_review_window": [9, 10],
            "rationale": "Bing search volume from professional users peaks in the morning. Traffic campaigns capture high-intent sessions before noon.",
        },
    },
    "amazon_ads": {
        "conversions": {
            "best_days": ["Friday", "Saturday", "Sunday"],
            "heatmap": {
                "Mon": {12: 52, 13: 54, 18: 64, 19: 68, 20: 72, 21: 66},
                "Tue": {12: 50, 13: 52, 18: 62, 19: 66, 20: 70, 21: 64},
                "Wed": {12: 51, 13: 53, 18: 63, 19: 67, 20: 71, 21: 65},
                "Thu": {12: 54, 13: 56, 18: 70, 19: 76, 20: 82, 21: 78},
                "Fri": {12: 60, 13: 62, 17: 74, 18: 82, 19: 90, 20: 94, 21: 88, 22: 76},
                "Sat": {10: 66, 11: 72, 12: 78, 13: 80, 18: 84, 19: 92, 20: 96, 21: 90},
                "Sun": {10: 62, 11: 68, 12: 74, 13: 76, 18: 80, 19: 88, 20: 92, 21: 86},
            },
            "peak_hour": 20, "avoid_hours": [0, 1, 2, 3, 4, 5, 6, 7],
            "human_review_window": [19, 20],
            "rationale": "Amazon purchase intent spikes Thu evening through Sunday. Prime evening hours 7–10pm drive 62% of weekly conversions.",
        },
        "brand_awareness": {
            "best_days": ["Thursday", "Friday", "Saturday", "Sunday"],
            "heatmap": {
                "Mon": {12: 48, 13: 50, 18: 58, 19: 62, 20: 66},
                "Tue": {12: 46, 13: 48, 18: 56, 19: 60, 20: 64},
                "Wed": {12: 47, 13: 49, 18: 57, 19: 61, 20: 65},
                "Thu": {12: 56, 13: 58, 18: 72, 19: 78, 20: 84, 21: 80},
                "Fri": {12: 62, 13: 64, 17: 76, 18: 84, 19: 90, 20: 94},
                "Sat": {10: 68, 11: 74, 12: 80, 18: 86, 19: 92, 20: 96},
                "Sun": {10: 64, 11: 70, 12: 76, 18: 82, 19: 88, 20: 92},
            },
            "peak_hour": 20, "avoid_hours": [0, 1, 2, 3, 4, 5, 6],
            "human_review_window": [19, 20],
            "rationale": "Amazon brand impressions amplify during weekend browsing. Evening slots 7–9pm see 3× higher brand recall.",
        },
        "traffic": {
            "best_days": ["Friday", "Saturday", "Sunday"],
            "heatmap": {
                "Mon": {12: 50, 13: 52, 18: 62, 19: 66, 20: 70},
                "Tue": {12: 48, 13: 50, 18: 60, 19: 64, 20: 68},
                "Wed": {12: 49, 13: 51, 18: 61, 19: 65, 20: 69},
                "Thu": {12: 56, 13: 58, 18: 72, 19: 78, 20: 84},
                "Fri": {12: 64, 13: 66, 17: 78, 18: 86, 19: 92, 20: 96},
                "Sat": {10: 70, 11: 76, 12: 82, 13: 84, 18: 88, 19: 94, 20: 98},
                "Sun": {10: 66, 11: 72, 12: 78, 13: 80, 18: 84, 19: 90, 20: 94},
            },
            "peak_hour": 20, "avoid_hours": [0, 1, 2, 3, 4, 5, 6, 7],
            "human_review_window": [19, 20],
            "rationale": "Amazon traffic peaks on weekends. Shoppers browse product discovery pages extensively Fri–Sun evenings.",
        },
    },
    "apple_search_ads": {
        "conversions": {
            "best_days": ["Monday", "Tuesday", "Wednesday", "Thursday"],
            "heatmap": {
                "Mon": {7: 70, 8: 82, 9: 88, 10: 86, 11: 84, 12: 78, 17: 76, 18: 80, 19: 84, 20: 80},
                "Tue": {7: 72, 8: 84, 9: 90, 10: 88, 11: 86, 12: 80, 17: 78, 18: 82, 19: 86, 20: 82},
                "Wed": {7: 71, 8: 83, 9: 89, 10: 87, 11: 85, 12: 79, 17: 77, 18: 81, 19: 85, 20: 81},
                "Thu": {7: 69, 8: 81, 9: 87, 10: 85, 11: 83, 12: 77, 17: 75, 18: 79, 19: 83, 20: 79},
                "Fri": {7: 62, 8: 74, 9: 80, 10: 78, 11: 76, 12: 71, 17: 70, 18: 75, 19: 80, 20: 76},
                "Sat": {9: 58, 10: 64, 11: 68, 12: 66, 18: 70, 19: 74, 20: 72},
                "Sun": {9: 54, 10: 60, 11: 64, 12: 62, 18: 66, 19: 70, 20: 68},
            },
            "peak_hour": 9, "avoid_hours": [0, 1, 2, 3, 4, 5],
            "human_review_window": [9, 10],
            "rationale": "App Store search intent spikes at commute time (7–9am) and evening leisure (7–9pm). Both windows convert well.",
        },
        "brand_awareness": {
            "best_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "heatmap": {
                "Mon": {7: 68, 8: 80, 9: 86, 10: 84, 11: 82, 12: 76, 17: 74, 18: 78, 19: 82, 20: 78},
                "Tue": {7: 70, 8: 82, 9: 88, 10: 86, 11: 84, 12: 78, 17: 76, 18: 80, 19: 84, 20: 80},
                "Wed": {7: 69, 8: 81, 9: 87, 10: 85, 11: 83, 12: 77, 17: 75, 18: 79, 19: 83, 20: 79},
                "Thu": {7: 67, 8: 79, 9: 85, 10: 83, 11: 81, 12: 75, 17: 73, 18: 77, 19: 81, 20: 77},
                "Fri": {7: 60, 8: 72, 9: 78, 10: 76, 11: 74, 12: 69, 17: 68, 18: 73, 19: 78, 20: 74},
                "Sat": {9: 56, 10: 62, 11: 66, 12: 64, 18: 68, 19: 72, 20: 70},
                "Sun": {9: 52, 10: 58, 11: 62, 12: 60, 18: 64, 19: 68, 20: 66},
            },
            "peak_hour": 9, "avoid_hours": [0, 1, 2, 3, 4, 5],
            "human_review_window": [9, 10],
            "rationale": "App discovery happens throughout the day. Commute slots see the highest brand impression rates on iOS.",
        },
        "traffic": {
            "best_days": ["Monday", "Tuesday", "Wednesday", "Thursday"],
            "heatmap": {
                "Mon": {7: 72, 8: 84, 9: 90, 10: 88, 11: 86, 12: 80, 17: 78, 18: 82, 19: 86, 20: 82},
                "Tue": {7: 74, 8: 86, 9: 92, 10: 90, 11: 88, 12: 82, 17: 80, 18: 84, 19: 88, 20: 84},
                "Wed": {7: 73, 8: 85, 9: 91, 10: 89, 11: 87, 12: 81, 17: 79, 18: 83, 19: 87, 20: 83},
                "Thu": {7: 71, 8: 83, 9: 89, 10: 87, 11: 85, 12: 79, 17: 77, 18: 81, 19: 85, 20: 81},
                "Fri": {7: 64, 8: 76, 9: 82, 10: 80, 11: 78, 12: 73, 17: 72, 18: 77, 19: 82, 20: 78},
                "Sat": {9: 60, 10: 66, 11: 70, 12: 68, 18: 72, 19: 76, 20: 74},
                "Sun": {9: 56, 10: 62, 11: 66, 12: 64, 18: 68, 19: 72, 20: 70},
            },
            "peak_hour": 9, "avoid_hours": [0, 1, 2, 3, 4, 5],
            "human_review_window": [9, 10],
            "rationale": "App Store search traffic is highest during morning commute. Targeting these windows reduces CPI by up to 28%.",
        },
    },
    "youtube_ads": {
        "conversions": {
            "best_days": ["Thursday", "Friday", "Saturday"],
            "heatmap": {
                "Mon": {12: 52, 13: 54, 17: 62, 18: 68, 19: 74, 20: 72, 21: 66},
                "Tue": {12: 50, 13: 52, 17: 60, 18: 66, 19: 72, 20: 70, 21: 64},
                "Wed": {12: 51, 13: 53, 17: 61, 18: 67, 19: 73, 20: 71, 21: 65},
                "Thu": {12: 58, 13: 60, 17: 70, 18: 78, 19: 86, 20: 90, 21: 84},
                "Fri": {12: 62, 13: 64, 17: 74, 18: 82, 19: 90, 20: 94, 21: 88},
                "Sat": {10: 62, 11: 68, 12: 74, 17: 78, 18: 84, 19: 90, 20: 94, 21: 88},
                "Sun": {10: 58, 11: 64, 12: 70, 17: 74, 18: 80, 19: 86, 20: 90, 21: 84},
            },
            "peak_hour": 20, "avoid_hours": [0, 1, 2, 3, 4, 5, 6, 7],
            "human_review_window": [19, 20],
            "rationale": "YouTube conversion intent is highest Thu–Sat evening. Viewers in a relaxed state are 2.4× more likely to click through.",
        },
        "brand_awareness": {
            "best_days": ["Thursday", "Friday", "Saturday", "Sunday"],
            "heatmap": {
                "Mon": {12: 56, 13: 58, 17: 66, 18: 72, 19: 78, 20: 76},
                "Tue": {12: 54, 13: 56, 17: 64, 18: 70, 19: 76, 20: 74},
                "Wed": {12: 55, 13: 57, 17: 65, 18: 71, 19: 77, 20: 75},
                "Thu": {12: 62, 13: 64, 17: 74, 18: 82, 19: 90, 20: 94},
                "Fri": {12: 66, 13: 68, 17: 78, 18: 86, 19: 92, 20: 96},
                "Sat": {10: 66, 11: 72, 12: 78, 17: 82, 18: 88, 19: 94, 20: 96},
                "Sun": {10: 62, 11: 68, 12: 74, 17: 78, 18: 84, 19: 90, 20: 94},
            },
            "peak_hour": 20, "avoid_hours": [0, 1, 2, 3, 4, 5, 6],
            "human_review_window": [19, 20],
            "rationale": "YouTube brand recall is 89% higher on weekend evenings. Longer view durations during leisure time boost brand association.",
        },
        "traffic": {
            "best_days": ["Friday", "Saturday", "Sunday"],
            "heatmap": {
                "Mon": {12: 54, 13: 56, 17: 64, 18: 70, 19: 76, 20: 74},
                "Tue": {12: 52, 13: 54, 17: 62, 18: 68, 19: 74, 20: 72},
                "Wed": {12: 53, 13: 55, 17: 63, 18: 69, 19: 75, 20: 73},
                "Thu": {12: 60, 13: 62, 17: 72, 18: 80, 19: 88, 20: 92},
                "Fri": {12: 64, 13: 66, 17: 76, 18: 84, 19: 92, 20: 96, 21: 90},
                "Sat": {10: 64, 11: 70, 12: 76, 17: 80, 18: 86, 19: 92, 20: 96},
                "Sun": {10: 60, 11: 66, 12: 72, 17: 76, 18: 82, 19: 88, 20: 92},
            },
            "peak_hour": 20, "avoid_hours": [0, 1, 2, 3, 4, 5, 6, 7],
            "human_review_window": [19, 20],
            "rationale": "YouTube traffic campaigns benefit from high weekend engagement. Evening slots deliver 47% lower CPV vs daytime.",
        },
    },
}

_DEFAULT_BEST_TIME: dict[str, Any] = {
    "best_days": ["Tuesday", "Wednesday", "Thursday"],
    "heatmap": {
        "Mon": {9: 72, 10: 80, 11: 78, 14: 75, 15: 73},
        "Tue": {9: 78, 10: 86, 11: 84, 14: 81, 15: 79},
        "Wed": {9: 76, 10: 84, 11: 82, 14: 79, 15: 77},
        "Thu": {9: 74, 10: 82, 11: 80, 14: 77, 15: 75},
        "Fri": {9: 68, 10: 76, 11: 74, 14: 71, 15: 69},
        "Sat": {10: 44, 11: 48, 12: 50},
        "Sun": {10: 40, 11: 44, 12: 46},
    },
    "peak_hour": 10, "avoid_hours": [0, 1, 2, 3, 4, 22, 23],
    "human_review_window": [9, 10],
    "rationale": "General best practice: target mid-morning and early afternoon on weekdays for balanced reach and intent.",
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _platform_oauth_url(platform: str) -> str:
    urls = {
        "google_ads": "https://accounts.google.com/o/oauth2/v2/auth",
        "microsoft_ads": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "amazon_ads": "https://www.amazon.com/ap/oa",
        "apple_search_ads": "https://appleid.apple.com/auth/authorize",
        "youtube_ads": "https://accounts.google.com/o/oauth2/v2/auth",
    }
    return urls.get(platform, "https://example.com/oauth")


def _platform_vendor_id(platform: str) -> str | None:
    mapping = {
        "google_ads": "google_ads_api",
        "microsoft_ads": "microsoft_ads_api",
        "amazon_ads": "amazon_ads_api",
        "apple_search_ads": "apple_search_ads_api",
        "youtube_ads": "youtube_ads_api",
    }
    return mapping.get(platform)


def _seed_connector(tenant_id: str, platform: str) -> dict[str, Any]:
    meta = PLATFORM_META.get(platform, {})
    return {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "platform": platform,
        "platform_description": meta.get("description", ""),
        "platform_accent": meta.get("accent", "#3b82f6"),
        "status": "disconnected",
        "connected": False,
        "account_name": "",
        "account_id": "",
        "scopes": [],
        "token_fingerprint": None,
        "refresh_token_present": False,
        "credit_currency": "USD",
        "credit_total": 0.0,
        "credit_remaining": 0.0,
        "last_sync_at": None,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }


class ConnectorStartResponse(BaseModel):
    platform: str
    state: str
    authorization_url: str
    callback_path: str


class ConnectorCallbackRequest(BaseModel):
    state: str = Field(min_length=8, max_length=256)
    code: str = Field(min_length=4, max_length=2000)
    account_name: str = Field(default="Primary Account", min_length=2, max_length=160)
    account_id: str = Field(default="", max_length=200)
    scopes: list[str] = Field(default_factory=list, max_length=40)
    credit_total: float = Field(default=0.0, ge=0)
    credit_remaining: float = Field(default=0.0, ge=0)
    credit_currency: str = Field(default="USD", min_length=3, max_length=8)


class ConnectorListResponse(BaseModel):
    status: str
    tenant_id: str
    connectors: list[dict[str, Any]]


class KeywordConfig(BaseModel):
    keyword: str = Field(min_length=1, max_length=200)
    cpc_bid: float = Field(default=0.0, ge=0)
    cost_today: float = Field(default=0.0, ge=0)
    rank: int = Field(default=0, ge=0)


class CampaignCreative(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    description: str = Field(min_length=2, max_length=2000)
    cta: str = Field(default="Learn More", min_length=2, max_length=80)
    media_urls: list[str] = Field(default_factory=list, max_length=20)


class CampaignSchedule(BaseModel):
    timezone: str = Field(default="UTC", min_length=2, max_length=80)
    start_at: str | None = None
    end_at: str | None = None
    auto_post: bool = True
    posting_dates: list[str] = Field(default_factory=list, max_length=366)


class CampaignCreateRequest(BaseModel):
    platform: str = Field(pattern=r"^(google_ads|microsoft_ads|amazon_ads|apple_search_ads|youtube_ads)$")
    campaign_name: str = Field(min_length=2, max_length=180)
    objective: str = Field(default="conversions", min_length=2, max_length=80)
    status: Literal["draft", "active", "paused"] = "draft"
    budget_daily: float = Field(default=0.0, ge=0)
    budget_total: float = Field(default=0.0, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=8)
    keywords: list[KeywordConfig] = Field(default_factory=list, max_length=300)
    creative: CampaignCreative
    schedule: CampaignSchedule = Field(default_factory=CampaignSchedule)
    connected_accounts: list[str] = Field(default_factory=list, max_length=20)


class CampaignUpdateRequest(BaseModel):
    campaign_name: str | None = Field(default=None, min_length=2, max_length=180)
    objective: str | None = Field(default=None, min_length=2, max_length=80)
    status: Literal["draft", "active", "paused"] | None = None
    budget_daily: float | None = Field(default=None, ge=0)
    budget_total: float | None = Field(default=None, ge=0)
    keywords: list[KeywordConfig] | None = Field(default=None, max_length=300)
    creative: CampaignCreative | None = None
    schedule: CampaignSchedule | None = None


class CampaignPublishRequest(BaseModel):
    publish_all_connected_accounts: bool = True


class CampaignMetricsPatchRequest(BaseModel):
    likes: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    impressions: int = Field(default=0, ge=0)
    conversions: int = Field(default=0, ge=0)
    spend: float = Field(default=0.0, ge=0)
    revenue: float = Field(default=0.0, ge=0)


class CalendarRescheduleRequest(BaseModel):
    campaign_id: str = Field(min_length=8, max_length=120)
    from_date: str = Field(min_length=8, max_length=40)
    to_date: str = Field(min_length=8, max_length=40)
    auto_select_window_days: int = Field(default=7, ge=1, le=90)


class AssetAutoResizeRequest(BaseModel):
    asset_url: str = Field(min_length=5, max_length=1200)
    platforms: list[str] = Field(default_factory=lambda: ["google_ads", "amazon_ads", "microsoft_ads"], max_length=10)


class ApprovalRequestModel(BaseModel):
    reviewer_email: str = Field(min_length=5, max_length=254)
    message: str = Field(default="", max_length=1000)
    auto_publish_on_approve: bool = True


class ApprovalDecisionModel(BaseModel):
    decision: Literal["approved", "rejected"]
    reason: str = Field(default="", max_length=1000)
    reviewer_name: str = Field(default="Reviewer", min_length=2, max_length=120)


class CampaignDuplicateRequest(BaseModel):
    new_name: str = Field(min_length=2, max_length=180)
    status: Literal["draft", "active", "paused"] = "draft"


class ForecastResponse(BaseModel):
    status: str
    tenant_id: str
    horizon_days: int
    projected_spend: float
    projected_clicks: int
    projected_conversions: int
    projected_roi_pct: float


def create_ads_control_tower_router(
    *,
    enforce_rate_limit: Callable[..., None],
    notifications_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
    connectors_memory: list[dict[str, Any]] | None = None,
    campaigns_memory: list[dict[str, Any]] | None = None,
    scheduler_memory: list[dict[str, Any]] | None = None,
    forecast_memory: list[dict[str, Any]] | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/ads-control-tower", tags=["ads-control-tower"])
    lock = threading.Lock()
    vendor_manager = get_vendor_manager()

    _connectors = connectors_memory if connectors_memory is not None else []
    _campaigns = campaigns_memory if campaigns_memory is not None else []
    _scheduler = scheduler_memory if scheduler_memory is not None else []
    _forecasts = forecast_memory if forecast_memory is not None else []

    def _append_notification(tenant_id: str, title: str, message: str, priority: str = "info") -> None:
        with lock:
            notifications_memory.append(
                {
                    "id": len(notifications_memory) + 1,
                    "tenant_id": tenant_id,
                    "title": title,
                    "message": message,
                    "category": "ads_control_tower",
                    "priority": priority,
                    "is_read": False,
                    "source": "ads-control-tower",
                    "created_at": _now_iso(),
                }
            )

    def _log_audit(tenant_id: str, action: str, payload: dict[str, Any]) -> None:
        with lock:
            audit_log_memory.append(
                {
                    "id": len(audit_log_memory) + 1,
                    "tenant_id": tenant_id,
                    "event": action,
                    "payload": payload,
                    "source": "ads-control-tower",
                    "created_at": _now_iso(),
                }
            )

    def _tenant_connectors(tenant_id: str) -> list[dict[str, Any]]:
        return [item for item in _connectors if item.get("tenant_id") == tenant_id]

    def _tenant_campaigns(tenant_id: str) -> list[dict[str, Any]]:
        return [item for item in _campaigns if item.get("tenant_id") == tenant_id]

    def _get_campaign(tenant_id: str, campaign_id: str) -> dict[str, Any] | None:
        return next((item for item in _campaigns if item.get("tenant_id") == tenant_id and item.get("id") == campaign_id), None)

    def _ensure_connector(tenant_id: str, platform: str) -> dict[str, Any]:
        existing = next((item for item in _connectors if item.get("tenant_id") == tenant_id and item.get("platform") == platform), None)
        if existing is not None:
            return existing
        seeded = _seed_connector(tenant_id, platform)
        _connectors.append(seeded)
        return seeded

    @router.get("/connectors", response_model=ConnectorListResponse)
    async def list_connectors(auth: AuthDep):
        enforce_rate_limit(f"{auth.tenant_id}:ads:connectors", limit=80, window_seconds=60)
        with lock:
            connectors = [_ensure_connector(auth.tenant_id, platform) for platform in sorted(SUPPORTED_PLATFORMS)]
        return {"status": "ok", "tenant_id": auth.tenant_id, "connectors": connectors}

    @router.post("/connectors/{platform}/oauth/start", response_model=ConnectorStartResponse)
    async def oauth_start(platform: str, auth: AuthDep):
        platform_key = platform.strip().lower()
        if platform_key not in SUPPORTED_PLATFORMS:
            raise HTTPException(status_code=404, detail=f"Unsupported platform: {platform}")
        enforce_rate_limit(f"{auth.tenant_id}:ads:{platform_key}:oauth:start", limit=20, window_seconds=60)

        state = secrets.token_urlsafe(24)
        with lock:
            connector = _ensure_connector(auth.tenant_id, platform_key)
            connector["oauth_state"] = state
            connector["oauth_started_at"] = _now_iso()
            connector["status"] = "auth_pending"
            connector["updated_at"] = _now_iso()

        auth_url = (
            f"{_platform_oauth_url(platform_key)}"
            f"?client_id=configure-me&response_type=code&redirect_uri=configure-me"
            f"&scope=ads.read+ads.write&state={state}"
        )
        _log_audit(auth.tenant_id, "ads_oauth_start", {"platform": platform_key})
        return {
            "platform": platform_key,
            "state": state,
            "authorization_url": auth_url,
            "callback_path": f"/ads-control-tower/connectors/{platform_key}/oauth/callback",
        }

    @router.post("/connectors/{platform}/oauth/callback")
    async def oauth_callback(platform: str, body: ConnectorCallbackRequest, auth: AuthDep):
        platform_key = platform.strip().lower()
        if platform_key not in SUPPORTED_PLATFORMS:
            raise HTTPException(status_code=404, detail=f"Unsupported platform: {platform}")
        enforce_rate_limit(f"{auth.tenant_id}:ads:{platform_key}:oauth:callback", limit=30, window_seconds=60)

        with lock:
            connector = _ensure_connector(auth.tenant_id, platform_key)
            expected_state = str(connector.get("oauth_state", ""))
            if not expected_state or expected_state != body.state:
                raise HTTPException(status_code=400, detail="OAuth state mismatch.")

            token_fingerprint = hashlib.sha256(body.code.encode("utf-8")).hexdigest()[:16]
            connector.update(
                {
                    "connected": True,
                    "status": "connected",
                    "account_name": body.account_name,
                    "account_id": body.account_id or f"{platform_key}-acct-{token_fingerprint[:8]}",
                    "scopes": body.scopes,
                    "token_fingerprint": token_fingerprint,
                    "refresh_token_present": True,
                    "credit_total": float(body.credit_total),
                    "credit_remaining": float(body.credit_remaining),
                    "credit_currency": body.credit_currency.upper(),
                    "last_sync_at": _now_iso(),
                    "updated_at": _now_iso(),
                }
            )

        vendor_id = _platform_vendor_id(platform_key)
        if vendor_id:
            vendor_manager.store_credentials(
                vendor_id,
                VendorCredentials(
                    vendor_type=VendorType.ANALYTICS,
                    platform=platform_key,
                    api_key=body.code,
                    access_token=body.code,
                    refresh_token="present",
                    additional_config={
                        "tenant_id": auth.tenant_id,
                        "account_id": connector.get("account_id", ""),
                        "account_name": connector.get("account_name", ""),
                        "scopes": list(body.scopes),
                    },
                ),
            )

        _append_notification(auth.tenant_id, f"{platform_key} connected", f"OAuth connected for {body.account_name}", "success")
        _log_audit(auth.tenant_id, "ads_oauth_connected", {"platform": platform_key, "account_id": connector["account_id"]})
        return {"status": "ok", "tenant_id": auth.tenant_id, "connector": connector}

    @router.get("/connectors/{platform}/credentials/status")
    async def connector_credentials_status(platform: str, auth: AuthDep):
        platform_key = platform.strip().lower()
        if platform_key not in SUPPORTED_PLATFORMS:
            raise HTTPException(status_code=404, detail=f"Unsupported platform: {platform}")

        connector = _ensure_connector(auth.tenant_id, platform_key)
        vendor_id = _platform_vendor_id(platform_key)
        has_credentials = bool(vendor_id and vendor_manager.has_credentials(vendor_id))

        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "platform": platform_key,
            "connector_connected": bool(connector.get("connected")),
            "vendor_credentials_configured": has_credentials,
        }

    @router.delete("/connectors/{platform}")
    async def disconnect_connector(platform: str, auth: AuthDep):
        platform_key = platform.strip().lower()
        if platform_key not in SUPPORTED_PLATFORMS:
            raise HTTPException(status_code=404, detail=f"Unsupported platform: {platform}")

        with lock:
            connector = _ensure_connector(auth.tenant_id, platform_key)
            connector.update(
                {
                    "connected": False,
                    "status": "disconnected",
                    "token_fingerprint": None,
                    "refresh_token_present": False,
                    "updated_at": _now_iso(),
                }
            )

        vendor_id = _platform_vendor_id(platform_key)
        if vendor_id:
            vendor_manager.revoke_credentials(vendor_id)

        _append_notification(auth.tenant_id, f"{platform_key} disconnected", "Connector disconnected from control tower.", "warning")
        _log_audit(auth.tenant_id, "ads_oauth_disconnected", {"platform": platform_key})
        return {"status": "ok", "tenant_id": auth.tenant_id, "connector": connector}

    @router.get("/credits")
    async def get_credit_balances(auth: AuthDep):
        connectors = _tenant_connectors(auth.tenant_id)
        balances = [
            {
                "platform": item.get("platform"),
                "account_name": item.get("account_name"),
                "account_id": item.get("account_id"),
                "currency": item.get("credit_currency", "USD"),
                "credit_total": float(item.get("credit_total", 0.0) or 0.0),
                "credit_remaining": float(item.get("credit_remaining", 0.0) or 0.0),
                "connected": bool(item.get("connected")),
            }
            for item in connectors
        ]
        total = sum(float(item["credit_total"]) for item in balances)
        remaining = sum(float(item["credit_remaining"]) for item in balances)
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "accounts": balances,
            "portfolio_credit_total": round(total, 2),
            "portfolio_credit_remaining": round(remaining, 2),
        }

    @router.post("/campaigns")
    async def create_campaign(payload: CampaignCreateRequest, auth: AuthDep):
        enforce_rate_limit(f"{auth.tenant_id}:ads:campaigns:create", limit=50, window_seconds=60)

        connector = _ensure_connector(auth.tenant_id, payload.platform)
        if not connector.get("connected"):
            raise HTTPException(status_code=422, detail=f"{payload.platform} is not connected. Complete OAuth first.")

        created_at = _now_iso()
        campaign_id = str(uuid.uuid4())
        metrics = {
            "likes": 0,
            "description_views": 0,
            "shares": 0,
            "comments": 0,
            "clicks": 0,
            "impressions": 0,
            "conversions": 0,
            "spend": 0.0,
            "revenue": 0.0,
            "roi_pct": 0.0,
            "success_ratio_pct": 0.0,
            "updated_at": created_at,
        }

        item = {
            "id": campaign_id,
            "tenant_id": auth.tenant_id,
            "platform": payload.platform,
            "campaign_name": payload.campaign_name,
            "objective": payload.objective,
            "status": payload.status,
            "budget_daily": float(payload.budget_daily),
            "budget_total": float(payload.budget_total),
            "currency": payload.currency.upper(),
            "keywords": [keyword.model_dump() for keyword in payload.keywords],
            "creative": payload.creative.model_dump(),
            "schedule": payload.schedule.model_dump(),
            "connected_accounts": payload.connected_accounts or [str(connector.get("account_id", ""))],
            "metrics": metrics,
            "created_at": created_at,
            "updated_at": created_at,
        }

        with lock:
            _campaigns.append(item)
            _scheduler.append(
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": auth.tenant_id,
                    "campaign_id": campaign_id,
                    "action": "initial_schedule",
                    "payload": payload.schedule.model_dump(),
                    "created_at": created_at,
                }
            )

        _append_notification(auth.tenant_id, "Campaign created", f"{payload.campaign_name} created for {payload.platform}.", "success")
        _log_audit(auth.tenant_id, "ads_campaign_created", {"campaign_id": campaign_id, "platform": payload.platform})
        return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": item}

    @router.get("/campaigns")
    async def list_campaigns(
        auth: AuthDep,
        platform: str | None = Query(default=None),
        status: str | None = Query(default=None),
    ):
        campaigns = _tenant_campaigns(auth.tenant_id)
        if platform:
            campaigns = [item for item in campaigns if str(item.get("platform")) == platform]
        if status:
            campaigns = [item for item in campaigns if str(item.get("status")) == status]
        return {"status": "ok", "tenant_id": auth.tenant_id, "total": len(campaigns), "campaigns": campaigns}

    @router.get("/campaigns/{campaign_id}")
    async def get_campaign(campaign_id: str, auth: AuthDep):
        campaign = _get_campaign(auth.tenant_id, campaign_id)
        if campaign is None:
            raise HTTPException(status_code=404, detail="Campaign not found.")
        return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": campaign}

    @router.patch("/campaigns/{campaign_id}")
    async def update_campaign(campaign_id: str, payload: CampaignUpdateRequest, auth: AuthDep):
        campaign = _get_campaign(auth.tenant_id, campaign_id)
        if campaign is None:
            raise HTTPException(status_code=404, detail="Campaign not found.")

        patch = payload.model_dump(exclude_none=True)
        with lock:
            if "keywords" in patch and isinstance(patch["keywords"], list):
                patch["keywords"] = [item.model_dump() if hasattr(item, "model_dump") else item for item in patch["keywords"]]
            if "creative" in patch and hasattr(patch["creative"], "model_dump"):
                patch["creative"] = patch["creative"].model_dump()
            if "schedule" in patch and hasattr(patch["schedule"], "model_dump"):
                patch["schedule"] = patch["schedule"].model_dump()
            campaign.update(patch)
            campaign["updated_at"] = _now_iso()

        _append_notification(auth.tenant_id, "Campaign updated", f"{campaign.get('campaign_name', 'Campaign')} updated.")
        _log_audit(auth.tenant_id, "ads_campaign_updated", {"campaign_id": campaign_id, "fields": list(patch.keys())})
        return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": campaign}

    @router.delete("/campaigns/{campaign_id}")
    async def delete_campaign(campaign_id: str, auth: AuthDep):
        with lock:
            idx = next((i for i, item in enumerate(_campaigns) if item.get("tenant_id") == auth.tenant_id and item.get("id") == campaign_id), None)
            if idx is None:
                raise HTTPException(status_code=404, detail="Campaign not found.")
            removed = _campaigns.pop(idx)

        _append_notification(auth.tenant_id, "Campaign deleted", f"{removed.get('campaign_name', 'Campaign')} deleted.", "warning")
        _log_audit(auth.tenant_id, "ads_campaign_deleted", {"campaign_id": campaign_id})
        return {"status": "ok", "tenant_id": auth.tenant_id, "deleted": campaign_id}

    @router.post("/campaigns/{campaign_id}/publish")
    async def publish_campaign(campaign_id: str, payload: CampaignPublishRequest, auth: AuthDep):
        campaign = _get_campaign(auth.tenant_id, campaign_id)
        if campaign is None:
            raise HTTPException(status_code=404, detail="Campaign not found.")

        platform = str(campaign.get("platform"))
        connector = _ensure_connector(auth.tenant_id, platform)
        if not connector.get("connected"):
            raise HTTPException(status_code=422, detail=f"{platform} is not connected. Complete OAuth first.")

        with lock:
            campaign["status"] = "active"
            campaign["published_at"] = _now_iso()
            campaign["updated_at"] = _now_iso()
            campaign["publish_mode"] = "all_accounts" if payload.publish_all_connected_accounts else "primary_account"

        _append_notification(auth.tenant_id, "Campaign published", f"{campaign.get('campaign_name', 'Campaign')} published to {platform}.", "success")
        _log_audit(auth.tenant_id, "ads_campaign_published", {"campaign_id": campaign_id, "platform": platform})
        return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": campaign}

    @router.post("/campaigns/{campaign_id}/metrics")
    async def patch_metrics(campaign_id: str, payload: CampaignMetricsPatchRequest, auth: AuthDep):
        campaign = _get_campaign(auth.tenant_id, campaign_id)
        if campaign is None:
            raise HTTPException(status_code=404, detail="Campaign not found.")

        with lock:
            metrics = dict(campaign.get("metrics") or {})
            metrics["likes"] = int(payload.likes)
            metrics["description_views"] = int(payload.impressions)
            metrics["shares"] = int(payload.shares)
            metrics["comments"] = int(payload.comments)
            metrics["clicks"] = int(payload.clicks)
            metrics["impressions"] = int(payload.impressions)
            metrics["conversions"] = int(payload.conversions)
            metrics["spend"] = float(payload.spend)
            metrics["revenue"] = float(payload.revenue)
            roi = ((metrics["revenue"] - metrics["spend"]) / metrics["spend"] * 100.0) if metrics["spend"] > 0 else 0.0
            success_ratio = (metrics["conversions"] / metrics["clicks"] * 100.0) if metrics["clicks"] > 0 else 0.0
            metrics["roi_pct"] = round(roi, 2)
            metrics["success_ratio_pct"] = round(success_ratio, 2)
            metrics["updated_at"] = _now_iso()
            campaign["metrics"] = metrics
            campaign["updated_at"] = _now_iso()

        _append_notification(auth.tenant_id, "Campaign metrics synced", f"{campaign.get('campaign_name', 'Campaign')} metrics updated.")
        _log_audit(auth.tenant_id, "ads_metrics_updated", {"campaign_id": campaign_id})
        return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": campaign}

    @router.get("/calendar")
    async def get_calendar(auth: AuthDep):
        campaigns = _tenant_campaigns(auth.tenant_id)
        events: list[dict[str, Any]] = []
        for campaign in campaigns:
            schedule = dict(campaign.get("schedule") or {})
            for date_value in schedule.get("posting_dates", []) or []:
                events.append(
                    {
                        "campaign_id": campaign.get("id"),
                        "campaign_name": campaign.get("campaign_name"),
                        "platform": campaign.get("platform"),
                        "date": date_value,
                        "timezone": schedule.get("timezone", "UTC"),
                        "auto_post": bool(schedule.get("auto_post", True)),
                    }
                )

        events.sort(key=lambda item: str(item.get("date", "")))
        return {"status": "ok", "tenant_id": auth.tenant_id, "events": events}

    @router.post("/calendar/drag-reschedule")
    async def drag_reschedule(payload: CalendarRescheduleRequest, auth: AuthDep):
        campaign = _get_campaign(auth.tenant_id, payload.campaign_id)
        if campaign is None:
            raise HTTPException(status_code=404, detail="Campaign not found.")

        with lock:
            schedule = dict(campaign.get("schedule") or {})
            dates = [str(item) for item in schedule.get("posting_dates", []) or []]
            if payload.from_date in dates:
                dates = [payload.to_date if item == payload.from_date else item for item in dates]
            else:
                dates.append(payload.to_date)
            dates = sorted(set(dates))
            schedule["posting_dates"] = dates
            schedule["auto_select_window_days"] = payload.auto_select_window_days
            campaign["schedule"] = schedule
            campaign["updated_at"] = _now_iso()

        _append_notification(auth.tenant_id, "Calendar updated", f"{campaign.get('campaign_name', 'Campaign')} moved to {payload.to_date}.")
        _log_audit(auth.tenant_id, "ads_calendar_rescheduled", {"campaign_id": payload.campaign_id, "to": payload.to_date})
        return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": campaign}

    @router.post("/assets/auto-resize")
    async def auto_resize_asset(payload: AssetAutoResizeRequest, auth: AuthDep):
        enforce_rate_limit(f"{auth.tenant_id}:ads:assets:resize", limit=50, window_seconds=60)

        profile_map = {
            "google_ads": [(1200, 628), (1080, 1080), (960, 1200)],
            "amazon_ads": [(1200, 628), (1024, 512)],
            "microsoft_ads": [(1200, 628), (1080, 1080)],
            "apple_search_ads": [(1200, 628), (640, 1136)],
            "youtube_ads": [(1920, 1080), (1080, 1920)],
        }
        generated: list[dict[str, Any]] = []
        for platform in payload.platforms:
            if platform not in SUPPORTED_PLATFORMS:
                continue
            for width, height in profile_map.get(platform, []):
                generated.append(
                    {
                        "platform": platform,
                        "width": width,
                        "height": height,
                        "output_url": f"{payload.asset_url}?platform={platform}&w={width}&h={height}",
                    }
                )

        _log_audit(auth.tenant_id, "ads_asset_auto_resize", {"asset": payload.asset_url, "variants": len(generated)})
        return {"status": "ok", "tenant_id": auth.tenant_id, "variants": generated}

    @router.get("/kpis")
    async def get_kpis(auth: AuthDep):
        campaigns = _tenant_campaigns(auth.tenant_id)
        total_budget_daily = sum(float(item.get("budget_daily", 0.0) or 0.0) for item in campaigns)
        total_budget_total = sum(float(item.get("budget_total", 0.0) or 0.0) for item in campaigns)
        spend = 0.0
        revenue = 0.0
        clicks = 0
        conversions = 0
        impressions = 0
        likes = 0
        shares = 0
        comments = 0
        active = 0

        for campaign in campaigns:
            if str(campaign.get("status")) == "active":
                active += 1
            metrics = dict(campaign.get("metrics") or {})
            spend += float(metrics.get("spend", 0.0) or 0.0)
            revenue += float(metrics.get("revenue", 0.0) or 0.0)
            clicks += int(metrics.get("clicks", 0) or 0)
            conversions += int(metrics.get("conversions", 0) or 0)
            impressions += int(metrics.get("impressions", 0) or 0)
            likes += int(metrics.get("likes", 0) or 0)
            shares += int(metrics.get("shares", 0) or 0)
            comments += int(metrics.get("comments", 0) or 0)

        ctr = (clicks / impressions * 100.0) if impressions > 0 else 0.0
        cpc = (spend / clicks) if clicks > 0 else 0.0
        cpa = (spend / conversions) if conversions > 0 else 0.0
        roi = ((revenue - spend) / spend * 100.0) if spend > 0 else 0.0
        success_ratio = (conversions / clicks * 100.0) if clicks > 0 else 0.0

        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "summary": {
                "campaigns_total": len(campaigns),
                "campaigns_active": active,
                "budget_daily": round(total_budget_daily, 2),
                "budget_total": round(total_budget_total, 2),
                "spend": round(spend, 2),
                "revenue": round(revenue, 2),
                "roi_pct": round(roi, 2),
                "success_ratio_pct": round(success_ratio, 2),
                "ctr_pct": round(ctr, 2),
                "cpc": round(cpc, 2),
                "cpa": round(cpa, 2),
            },
            "engagement": {
                "likes": likes,
                "shares": shares,
                "comments": comments,
                "clicks": clicks,
                "impressions": impressions,
                "conversions": conversions,
            },
        }

    @router.get("/forecast", response_model=ForecastResponse)
    async def get_forecast(auth: AuthDep, days: int = Query(default=30, ge=1, le=365)):
        campaigns = _tenant_campaigns(auth.tenant_id)
        active = [item for item in campaigns if str(item.get("status")) in {"active", "draft"}]
        daily_budget = sum(float(item.get("budget_daily", 0.0) or 0.0) for item in active)

        projected_spend = daily_budget * days
        baseline_click_rate = 0.021
        baseline_conv_rate = 0.073
        projected_clicks = int(projected_spend * 1.0 / max(0.01, 1.85) / max(0.001, baseline_click_rate)) if projected_spend > 0 else 0
        projected_conversions = int(projected_clicks * baseline_conv_rate)
        projected_revenue = projected_conversions * 48.0
        projected_roi_pct = ((projected_revenue - projected_spend) / projected_spend * 100.0) if projected_spend > 0 else 0.0

        with lock:
            _forecasts.append(
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": auth.tenant_id,
                    "horizon_days": days,
                    "projected_spend": round(projected_spend, 2),
                    "projected_clicks": projected_clicks,
                    "projected_conversions": projected_conversions,
                    "projected_roi_pct": round(projected_roi_pct, 2),
                    "created_at": _now_iso(),
                }
            )

        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "horizon_days": days,
            "projected_spend": round(projected_spend, 2),
            "projected_clicks": projected_clicks,
            "projected_conversions": projected_conversions,
            "projected_roi_pct": round(projected_roi_pct, 2),
        }

    @router.get("/notifications")
    async def list_ads_notifications(auth: AuthDep, limit: int = Query(default=50, ge=1, le=200)):
        items = [
            item
            for item in notifications_memory
            if item.get("tenant_id") == auth.tenant_id and str(item.get("category", "")).lower() == "ads_control_tower"
        ]
        items.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return {"status": "ok", "tenant_id": auth.tenant_id, "total": len(items), "notifications": items[:limit]}

    @router.get("/best-time")
    async def get_best_time(
        auth: AuthDep,
        platform: str = Query(default="google_ads"),
        objective: str = Query(default="conversions"),
    ):
        enforce_rate_limit(f"{auth.tenant_id}:ads:best-time", limit=60, window_seconds=60)
        platform_key = platform.strip().lower()
        objective_key = objective.strip().lower()
        data = _BEST_TIME_TABLE.get(platform_key, {}).get(objective_key) or _DEFAULT_BEST_TIME
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "platform": platform_key,
            "objective": objective_key,
            "best_days": data["best_days"],
            "heatmap": data["heatmap"],
            "peak_hour": data["peak_hour"],
            "avoid_hours": data["avoid_hours"],
            "human_review_window": data["human_review_window"],
            "rationale": data["rationale"],
            "all_platforms_peak": {
                "google_ads": 10, "microsoft_ads": 10,
                "amazon_ads": 20, "apple_search_ads": 9, "youtube_ads": 20,
            },
        }

    @router.post("/campaigns/{campaign_id}/request-approval")
    async def request_approval(campaign_id: str, payload: ApprovalRequestModel, auth: AuthDep):
        enforce_rate_limit(f"{auth.tenant_id}:ads:approval:request", limit=30, window_seconds=60)
        campaign = _get_campaign(auth.tenant_id, campaign_id)
        if campaign is None:
            raise HTTPException(status_code=404, detail="Campaign not found.")
        with lock:
            campaign["approval_status"] = "pending_approval"
            campaign["approval_requested_at"] = _now_iso()
            campaign["reviewer_email"] = payload.reviewer_email
            campaign["approval_message"] = payload.message
            campaign["auto_publish_on_approve"] = payload.auto_publish_on_approve
            campaign["updated_at"] = _now_iso()
        _append_notification(
            auth.tenant_id, "Approval requested",
            f"{campaign.get('campaign_name', 'Campaign')} awaiting review by {payload.reviewer_email}.", "info",
        )
        _log_audit(auth.tenant_id, "ads_approval_requested", {"campaign_id": campaign_id, "reviewer": payload.reviewer_email})
        return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": campaign}

    @router.post("/campaigns/{campaign_id}/approve")
    async def decide_campaign_approval(campaign_id: str, payload: ApprovalDecisionModel, auth: AuthDep):
        enforce_rate_limit(f"{auth.tenant_id}:ads:approval:decide", limit=30, window_seconds=60)
        campaign = _get_campaign(auth.tenant_id, campaign_id)
        if campaign is None:
            raise HTTPException(status_code=404, detail="Campaign not found.")
        with lock:
            campaign["approval_status"] = payload.decision
            campaign["approval_decided_at"] = _now_iso()
            campaign["approval_reason"] = payload.reason
            campaign["approver_name"] = payload.reviewer_name
            campaign["updated_at"] = _now_iso()
            if payload.decision == "approved" and bool(campaign.get("auto_publish_on_approve", True)):
                platform = str(campaign.get("platform"))
                connector = _ensure_connector(auth.tenant_id, platform)
                if connector.get("connected"):
                    campaign["status"] = "active"
                    campaign["published_at"] = _now_iso()
        priority = "success" if payload.decision == "approved" else "warning"
        _append_notification(
            auth.tenant_id, f"Campaign {payload.decision}",
            f"{campaign.get('campaign_name', 'Campaign')} was {payload.decision} by {payload.reviewer_name}.", priority,
        )
        _log_audit(auth.tenant_id, f"ads_campaign_{payload.decision}", {"campaign_id": campaign_id, "reviewer": payload.reviewer_name})
        return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": campaign}

    @router.post("/campaigns/{campaign_id}/duplicate")
    async def duplicate_campaign(campaign_id: str, payload: CampaignDuplicateRequest, auth: AuthDep):
        enforce_rate_limit(f"{auth.tenant_id}:ads:campaigns:duplicate", limit=30, window_seconds=60)
        import copy  # noqa: PLC0415
        source = _get_campaign(auth.tenant_id, campaign_id)
        if source is None:
            raise HTTPException(status_code=404, detail="Campaign not found.")
        new_id = str(uuid.uuid4())
        created_at = _now_iso()
        new_campaign = copy.deepcopy(source)
        new_campaign.update({
            "id": new_id, "campaign_name": payload.new_name, "status": payload.status,
            "created_at": created_at, "updated_at": created_at,
            "published_at": None, "approval_status": None, "approval_requested_at": None,
            "metrics": {
                "likes": 0, "description_views": 0, "shares": 0, "comments": 0,
                "clicks": 0, "impressions": 0, "conversions": 0,
                "spend": 0.0, "revenue": 0.0, "roi_pct": 0.0,
                "success_ratio_pct": 0.0, "updated_at": created_at,
            },
        })
        with lock:
            _campaigns.append(new_campaign)
        _append_notification(auth.tenant_id, "Campaign duplicated",
                             f"'{payload.new_name}' cloned from '{source.get('campaign_name')}'.", "info")
        _log_audit(auth.tenant_id, "ads_campaign_duplicated", {"source_id": campaign_id, "new_id": new_id})
        return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": new_campaign}

    @router.get("/ab-test/{campaign_id}/suggestions")
    async def ab_test_suggestions(campaign_id: str, auth: AuthDep):
        enforce_rate_limit(f"{auth.tenant_id}:ads:ab-test", limit=30, window_seconds=60)
        campaign = _get_campaign(auth.tenant_id, campaign_id)
        if campaign is None:
            raise HTTPException(status_code=404, detail="Campaign not found.")
        creative = dict(campaign.get("creative") or {})
        title = str(creative.get("title", "Your Product"))
        description = str(creative.get("description", "Discover what makes us different."))
        cta = str(creative.get("cta", "Learn More"))
        cta_variants: dict[str, list[str]] = {
            "Learn More": ["Get Started", "See How It Works", "Explore Now"],
            "Shop Now": ["Buy Today", "Order Now", "Claim Your Discount"],
            "Sign Up": ["Join Free", "Start Today", "Create Account"],
            "Get Started": ["Try for Free", "Start Now", "Begin Today"],
            "Contact Us": ["Talk to an Expert", "Request a Demo", "Get in Touch"],
        }
        alt_ctas = cta_variants.get(cta, ["Try Now", "Discover More", "Act Now"])
        first_word = title.split()[0] if title.split() else "Us"
        suggestions = [
            {"variant": "A", "label": "Urgency headline", "title": f"Last Chance: {title}",
             "description": description, "cta": cta, "predicted_ctr_lift_pct": 14,
             "rationale": "Urgency framing increases CTR by 12–18% on average."},
            {"variant": "B", "label": "Question hook", "title": f"Is {title} Right for You?",
             "description": f"See why thousands choose {first_word}. {description}", "cta": alt_ctas[0],
             "predicted_ctr_lift_pct": 9, "rationale": "Question headlines engage curiosity and drive 9% higher click rates."},
            {"variant": "C", "label": "Social proof", "title": f"{title} — Trusted by 10,000+",
             "description": f"Join thousands of satisfied customers. {description}", "cta": alt_ctas[1],
             "predicted_ctr_lift_pct": 18, "rationale": "Social proof reduces friction and lifts conversions by 15–22%."},
            {"variant": "D", "label": "Benefit-first", "title": f"Save Time & Money with {first_word}",
             "description": description, "cta": alt_ctas[2] if len(alt_ctas) > 2 else alt_ctas[0],
             "predicted_ctr_lift_pct": 11, "rationale": "Leading with direct benefits resonates with high-intent audiences."},
        ]
        return {
            "status": "ok", "tenant_id": auth.tenant_id, "campaign_id": campaign_id,
            "original": {"title": title, "description": description, "cta": cta},
            "suggestions": suggestions,
        }

    @router.get("/audience-insights")
    async def audience_insights(auth: AuthDep):
        enforce_rate_limit(f"{auth.tenant_id}:ads:audience-insights", limit=30, window_seconds=60)
        campaigns = _tenant_campaigns(auth.tenant_id)
        platforms_used = list({str(c.get("platform")) for c in campaigns})
        keywords_used: list[str] = []
        for c in campaigns:
            for kw in c.get("keywords", []) or []:
                kw_word = str(kw.get("keyword", "")) if isinstance(kw, dict) else ""
                if kw_word and kw_word not in keywords_used:
                    keywords_used.append(kw_word)
        overlap_pct = min(85, max(0, len(platforms_used) * 12 + len(keywords_used) * 3))
        saturation_score = min(100, max(0, len(keywords_used) * 4 + len(campaigns) * 2))
        platform_reach: dict[str, int] = {
            "google_ads": 4_200_000_000, "microsoft_ads": 540_000_000,
            "amazon_ads": 310_000_000, "apple_search_ads": 650_000_000, "youtube_ads": 2_700_000_000,
        }
        reach_estimate = sum(platform_reach.get(p, 100_000_000) for p in platforms_used)
        recommendations: list[str] = []
        if overlap_pct > 60:
            recommendations.append("High audience overlap — consider platform-specific creative to reduce ad fatigue.")
        if saturation_score > 70:
            recommendations.append("Keyword pool may be saturating — broaden match types or add long-tail variants.")
        if len(platforms_used) < 3:
            recommendations.append("Expand to 3+ platforms for diversified reach and reduced channel dependency.")
        if not recommendations:
            recommendations.append("Audience distribution looks healthy. Monitor frequency caps weekly.")
        return {
            "status": "ok", "tenant_id": auth.tenant_id,
            "platforms_active": platforms_used, "keywords_indexed": len(keywords_used),
            "audience_overlap_pct": overlap_pct, "keyword_saturation_score": saturation_score,
            "estimated_reach": reach_estimate, "recommendations": recommendations,
            "top_keywords": keywords_used[:10], "frequency_cap_suggestion": 3 if saturation_score > 60 else 5,
        }

    @router.get("/health")
    async def ads_health(auth: AuthDep):
        connectors = _tenant_connectors(auth.tenant_id)
        campaigns = _tenant_campaigns(auth.tenant_id)
        connected = sum(1 for item in connectors if bool(item.get("connected")))
        overdue = [
            item
            for item in campaigns
            if str(item.get("status")) == "active" and datetime.fromisoformat(str(item.get("updated_at", _now_iso())).replace("Z", "+00:00")) < datetime.now(UTC) - timedelta(days=2)
        ]
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "connectors_total": len(connectors),
            "connectors_connected": connected,
            "campaigns_total": len(campaigns),
            "campaigns_overdue_sync": len(overdue),
            "scheduler_jobs_total": len([item for item in _scheduler if item.get("tenant_id") == auth.tenant_id]),
            "forecast_runs_total": len([item for item in _forecasts if item.get("tenant_id") == auth.tenant_id]),
        }

    return router
