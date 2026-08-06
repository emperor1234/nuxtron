"""
Agent Analytics - Real-time AI Bot Traffic Tracking

Detects and tracks:
- ChatGPT bot (OpenAI)
- Google Gemini bot
- Perplexity bot
- Claude bot (Anthropic)
- Brave Search bot
- Other AI search engines

Uses CDN logs and edge computing (Cloudflare Workers) for real-time tracking.
"""

import logging
import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class AIBot(StrEnum):
    """Detected AI search engine bots"""
    CHATGPT = "ChatGPT"
    GEMINI = "Gemini"
    PERPLEXITY = "Perplexity"
    CLAUDE = "Claude"
    BRAVE_SEARCH = "Brave Search"
    GOOGLEBOT = "GoogleBot"
    BINGBOT = "BingBot"
    CCBOT = "CCBot"
    AMAZONBOT = "AmazonBot"

class BotSignature:
    """Signature patterns for identifying AI bots"""
    
    PATTERNS = {
        AIBot.CHATGPT: ["gptbot", "chat gpt"],
        AIBot.GEMINI: ["google-gemini", "gemini"],
        AIBot.PERPLEXITY: ["perplexitybot"],
        AIBot.CLAUDE: ["claude-web"],
        AIBot.BRAVE_SEARCH: ["bravebot"],
        AIBot.GOOGLEBOT: ["googlebot", "google-extended"],
        AIBot.BINGBOT: ["bingbot"],
        AIBot.CCBOT: ["ccbot"],  # Common Crawl
        AIBot.AMAZONBOT: ["amazonbot"],
    }
    
    @staticmethod
    def identify(user_agent: str) -> AIBot | None:
        """Identify bot from user-agent string"""
        ua_lower = user_agent.lower()
        
        for bot, patterns in BotSignature.PATTERNS.items():
            for pattern in patterns:
                if pattern in ua_lower:
                    return bot
        
        return None

class AgentLogEvent(BaseModel):
    """Single AI bot visit log"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    
    # Request info
    timestamp: datetime
    method: str  # GET, POST, etc
    path: str
    query_string: str | None = None
    
    # Bot info
    bot_name: AIBot
    user_agent: str
    
    # Network info
    ip_hash: str  # SHA256 hash of IP (for privacy)
    country: str | None = None
    asn: str | None = None
    is_datacenter: bool = False  # Whether from cloud provider
    
    # Response info
    status_code: int
    response_time_ms: int
    response_size_bytes: int

class BotAnalytics(BaseModel):
    """Aggregated analytics for AI bot traffic"""
    tenant_id: str
    
    # Time period
    period_start: datetime
    period_end: datetime
    
    # Summary metrics
    total_requests: int = 0
    unique_bots: int = 0
    total_crawled_pages: int = 0
    
    # Breakdown by bot
    requests_by_bot: dict[AIBot, int] = Field(default_factory=dict)
    
    # Breakdown by status code
    requests_by_status: dict[int, int] = Field(default_factory=dict)
    
    # Geographic distribution
    requests_by_country: dict[str, int] = Field(default_factory=dict)
    
    # Most crawled pages
    top_pages: list[str] = Field(default_factory=list)
    
    # Trends
    avg_response_time_ms: float = 0.0
    total_bandwidth_gb: float = 0.0

class AgentAnalyticsCollector:
    """Collects and aggregates agent analytics data"""
    
    def __init__(self):
        self.logs: list[AgentLogEvent] = []
    
    def add_log(self, event: AgentLogEvent):
        """Add a new log entry"""
        self.logs.append(event)
        logger.info(f"Logged {event.bot_name} visit to {event.path}")
    
    def get_analytics(
        self,
        tenant_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> BotAnalytics:
        """Get aggregated analytics for time period"""
        
        # Filter logs for period and tenant
        relevant_logs = [
            log for log in self.logs
            if log.tenant_id == tenant_id
            and period_start <= log.timestamp <= period_end
        ]
        
        if not relevant_logs:
            return BotAnalytics(
                tenant_id=tenant_id,
                period_start=period_start,
                period_end=period_end,
            )
        
        # Aggregate metrics
        requests_by_bot = {}
        requests_by_status = {}
        requests_by_country = {}
        top_pages_dict = {}
        
        total_response_time = 0
        total_bandwidth = 0
        unique_bots_set = set()
        
        for log in relevant_logs:
            # Bot breakdown
            if log.bot_name not in requests_by_bot:
                requests_by_bot[log.bot_name] = 0
            requests_by_bot[log.bot_name] += 1
            unique_bots_set.add(log.bot_name)
            
            # Status code breakdown
            if log.status_code not in requests_by_status:
                requests_by_status[log.status_code] = 0
            requests_by_status[log.status_code] += 1
            
            # Country breakdown
            if log.country:
                if log.country not in requests_by_country:
                    requests_by_country[log.country] = 0
                requests_by_country[log.country] += 1
            
            # Top pages
            if log.path not in top_pages_dict:
                top_pages_dict[log.path] = 0
            top_pages_dict[log.path] += 1
            
            # Performance metrics
            total_response_time += log.response_time_ms
            total_bandwidth += log.response_size_bytes
        
        # Get top 20 pages
        top_pages = sorted(
            top_pages_dict.items(),
            key=lambda x: x[1],
            reverse=True
        )[:20]
        top_pages_list = [page[0] for page in top_pages]
        
        return BotAnalytics(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            total_requests=len(relevant_logs),
            unique_bots=len(unique_bots_set),
            total_crawled_pages=len({log.path for log in relevant_logs}),
            requests_by_bot=requests_by_bot,
            requests_by_status=requests_by_status,
            requests_by_country=requests_by_country,
            top_pages=top_pages_list,
            avg_response_time_ms=total_response_time / len(relevant_logs),
            total_bandwidth_gb=total_bandwidth / (1024 ** 3),
        )
    
    def get_bot_details(
        self,
        tenant_id: str,
        bot_name: AIBot,
        period_start: datetime,
        period_end: datetime,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Get detailed stats for a specific bot"""
        
        relevant_logs = [
            log for log in self.logs
            if log.tenant_id == tenant_id
            and log.bot_name == bot_name
            and period_start <= log.timestamp <= period_end
        ]
        
        if not relevant_logs:
            return {
                "bot_name": bot_name.value,
                "total_visits": 0,
                "pages": [],
                "hourly_distribution": {},
            }
        
        # Group by hour
        hourly_dist: dict[str, int] = {}
        pages: dict[str, dict[str, Any]] = {}
        
        for log in relevant_logs:
            hour_key = log.timestamp.strftime("%Y-%m-%d %H:00")
            if hour_key not in hourly_dist:
                hourly_dist[hour_key] = 0
            hourly_dist[hour_key] += 1
            
            if log.path not in pages:
                pages[log.path] = {"count": 0, "status_codes": {}}
            pages[log.path]["count"] += 1
            
            status_key = str(log.status_code)
            if status_key not in pages[log.path]["status_codes"]:
                pages[log.path]["status_codes"][status_key] = 0
            pages[log.path]["status_codes"][status_key] += 1
        
        # Get top pages
        top_pages = sorted(
            pages.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:limit]
        
        return {
            "bot_name": bot_name.value,
            "total_visits": len(relevant_logs),
            "pages": [
                {"path": path, **stats}
                for path, stats in top_pages
            ],
            "hourly_distribution": hourly_dist,
            "first_seen": min(log.timestamp for log in relevant_logs),
            "last_seen": max(log.timestamp for log in relevant_logs),
        }

# Global collector instance
agent_analytics_collector = AgentAnalyticsCollector()  # type: ignore[no-untyped-call]
