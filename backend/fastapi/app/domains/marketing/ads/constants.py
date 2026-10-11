"""Marketing/Ads constants and configuration vocabulary."""

from __future__ import annotations
from ....deps import AuthContext
from ....deps import require_auth
from fastapi import Depends
from typing import Annotated
from typing import Any

AuthDep = Annotated[AuthContext, Depends(require_auth)]

SUPPORTED_PLATFORMS = {"google_ads", "microsoft_ads", "amazon_ads", "apple_search_ads", "youtube_ads"}

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
            "peak_hour": 10,
            "avoid_hours": [0, 1, 2, 3, 4, 22, 23],
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
            "peak_hour": 9,
            "avoid_hours": [0, 1, 2, 3, 4, 22, 23],
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
            "peak_hour": 10,
            "avoid_hours": [0, 1, 2, 3, 4, 5],
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
            "peak_hour": 10,
            "avoid_hours": [0, 1, 2, 3, 4, 20, 21, 22, 23],
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
            "peak_hour": 10,
            "avoid_hours": [0, 1, 2, 3, 4, 21, 22, 23],
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
            "peak_hour": 10,
            "avoid_hours": [0, 1, 2, 3, 4, 22, 23],
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
            "peak_hour": 20,
            "avoid_hours": [0, 1, 2, 3, 4, 5, 6, 7],
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
            "peak_hour": 20,
            "avoid_hours": [0, 1, 2, 3, 4, 5, 6],
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
            "peak_hour": 20,
            "avoid_hours": [0, 1, 2, 3, 4, 5, 6, 7],
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
            "peak_hour": 9,
            "avoid_hours": [0, 1, 2, 3, 4, 5],
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
            "peak_hour": 9,
            "avoid_hours": [0, 1, 2, 3, 4, 5],
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
            "peak_hour": 9,
            "avoid_hours": [0, 1, 2, 3, 4, 5],
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
            "peak_hour": 20,
            "avoid_hours": [0, 1, 2, 3, 4, 5, 6, 7],
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
            "peak_hour": 20,
            "avoid_hours": [0, 1, 2, 3, 4, 5, 6],
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
            "peak_hour": 20,
            "avoid_hours": [0, 1, 2, 3, 4, 5, 6, 7],
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
    "peak_hour": 10,
    "avoid_hours": [0, 1, 2, 3, 4, 22, 23],
    "human_review_window": [9, 10],
    "rationale": "General best practice: target mid-morning and early afternoon on weekdays for balanced reach and intent.",
}
