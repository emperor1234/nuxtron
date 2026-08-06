"""
Prompt Volumes - Track search keywords used by AI engines

Monitors:
- Question keywords (What, How, Why, Where, When)
- Search terms used by AI engines to find content
- Trending questions in your industry
- Long-tail keyword opportunities
- Competitor keyword usage
"""

import logging
import re
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class KeywordType(StrEnum):
    """Type of keyword"""
    QUESTION = "question"  # What, How, Why, etc.
    LONG_TAIL = "long_tail"  # 4+ words
    BRANDED = "branded"  # Mentions brand
    COMPETITOR = "competitor"  # Mentions competitor
    INDUSTRY = "industry"  # Industry term

class PromptVolume(BaseModel):
    """Single prompt/keyword volume record"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    
    # Keyword info
    keyword: str  # The actual search query
    keyword_type: KeywordType
    
    # Volume metrics
    search_count: int = 1  # How many times searched
    impression_count: int = 0  # How many impressions/results
    
    # Source tracking
    sources: list[str] = Field(default_factory=list)  # e.g., ["ChatGPT", "Gemini", "Perplexity"]
    
    # Context
    context: str | None = None  # Longer context if available
    
    # Timing
    first_seen: datetime
    last_seen: datetime
    trending: bool = False  # Is trending?
    
    # Relevance
    relevance_score: float = 0.5  # 0-1, how relevant to brand

class PromptVolumeAnalysis(BaseModel):
    """Aggregated prompt volume analysis"""
    tenant_id: str
    brand_name: str | None = None
    
    period_start: datetime
    period_end: datetime
    
    # Summary metrics
    total_unique_keywords: int = 0
    total_prompt_volume: int = 0
    trending_keywords_count: int = 0
    
    # By keyword type
    question_keywords: list[dict[str, Any]] = Field(default_factory=list)  # Top 20
    long_tail_keywords: list[dict[str, Any]] = Field(default_factory=list)  # Top 20
    branded_keywords: list[dict[str, Any]] = Field(default_factory=list)  # Top 20
    competitor_keywords: list[dict[str, Any]] = Field(default_factory=list)  # Top 20
    
    # Trending
    trending_keywords: list[dict[str, Any]] = Field(default_factory=list)
    emerging_keywords: list[dict[str, Any]] = Field(default_factory=list)
    
    # By source
    keywords_by_source: dict[str, int] = Field(default_factory=dict)
    
    # Word frequency (individual words)
    top_words: list[dict[str, Any]] = Field(default_factory=list)

class KeywordProcessor:
    """Process and categorize keywords"""
    
    QUESTION_WORDS = {"what", "how", "why", "where", "when", "who", "which"}
    
    BRAND_KEYWORDS: list[str] = []  # Set during init with tenant brand names
    COMPETITOR_KEYWORDS: list[str] = []  # Configured per tenant
    INDUSTRY_KEYWORDS: list[str] = []  # Domain-specific terms
    
    @staticmethod
    def classify_keyword(keyword: str, brand_name: str = "") -> KeywordType:
        """Classify keyword into type"""
        words = keyword.lower().split()
        
        # Check if question
        if any(word in KeywordProcessor.QUESTION_WORDS for word in words):
            return KeywordType.QUESTION
        
        # Check if branded
        if brand_name.lower() in keyword.lower():
            return KeywordType.BRANDED
        
        # Check if long-tail (4+ words)
        if len(words) >= 4:
            return KeywordType.LONG_TAIL
        
        return KeywordType.INDUSTRY

class PromptVolumesCollector:
    """Collects and aggregates prompt volume data"""
    
    def __init__(self):
        self.volumes: dict[str, PromptVolume] = {}  # keyword -> volume
        self.history: list[PromptVolume] = []  # Full history for trends
    
    def record_prompt(
        self,
        tenant_id: str,
        keyword: str,
        sources: list[str],
        brand_name: str = "",
        context: str | None = None,
        observed_at: datetime | None = None,
    ):
        """Record a prompt/keyword search"""
        
        key = f"{tenant_id}:{keyword}"
        now = observed_at or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        
        if key in self.volumes:
            # Update existing
            volume = self.volumes[key]
            volume.search_count += 1
            volume.last_seen = now
            
            # Add new sources
            for source in sources:
                if source not in volume.sources:
                    volume.sources.append(source)
        else:
            # Create new
            keyword_type = KeywordProcessor.classify_keyword(keyword, brand_name)
            relevance = self._calculate_relevance(keyword, brand_name)
            
            volume = PromptVolume(
                tenant_id=tenant_id,
                keyword=keyword,
                keyword_type=keyword_type,
                search_count=1,
                sources=sources,
                context=context,
                first_seen=now,
                last_seen=now,
                relevance_score=relevance,
            )
            
            self.volumes[key] = volume
        
        self.history.append(self.volumes[key])
        logger.info(f"Recorded prompt: {keyword} from {sources}")
    
    def _calculate_relevance(self, keyword: str, brand_name: str) -> float:
        """Calculate relevance score (0-1)"""
        score = 0.5
        
        # Boost for branded keywords
        if brand_name and brand_name.lower() in keyword.lower():
            score += 0.3
        
        # Boost for question words (questions are usually intent-rich)
        if any(word in keyword.lower() for word in KeywordProcessor.QUESTION_WORDS):
            score += 0.1
        
        # Cap at 1.0
        return min(score, 1.0)
    
    def get_analysis(
        self,
        tenant_id: str,
        period_start: datetime,
        period_end: datetime,
        brand_name: str = "",
        top_n: int = 20,
    ) -> PromptVolumeAnalysis:
        """Get aggregated analysis for period"""
        
        # Filter volumes for period
        relevant_volumes = [
            v for v in self.volumes.values()
            if v.tenant_id == tenant_id
            and period_start <= v.last_seen <= period_end
        ]
        
        if not relevant_volumes:
            return PromptVolumeAnalysis(
                tenant_id=tenant_id,
                brand_name=brand_name,
                period_start=period_start,
                period_end=period_end,
            )
        
        # Group by type
        by_type = defaultdict(list)
        for volume in relevant_volumes:
            by_type[volume.keyword_type].append(volume)
        
        # Sort each group by search count
        for ktype in by_type:
            by_type[ktype].sort(key=lambda v: v.search_count, reverse=True)
        
        # Get trending (higher velocity)
        trending = self._identify_trending(relevant_volumes, period_start, period_end)
        emerging = self._identify_emerging(relevant_volumes)
        
        # Count by source
        by_source: defaultdict[str, int] = defaultdict(int)
        for volume in relevant_volumes:
            for source in volume.sources:
                by_source[source] += volume.search_count
        
        # Extract words
        top_words = self._extract_top_words(relevant_volumes, top_n)
        
        return PromptVolumeAnalysis(
            tenant_id=tenant_id,
            brand_name=brand_name,
            period_start=period_start,
            period_end=period_end,
            total_unique_keywords=len(relevant_volumes),
            total_prompt_volume=sum(v.search_count for v in relevant_volumes),
            trending_keywords_count=len(trending),
            question_keywords=[
                {
                    "keyword": v.keyword,
                    "volume": v.search_count,
                    "sources": v.sources,
                    "relevance": v.relevance_score,
                }
                for v in by_type[KeywordType.QUESTION][:top_n]
            ],
            long_tail_keywords=[
                {
                    "keyword": v.keyword,
                    "volume": v.search_count,
                    "sources": v.sources,
                }
                for v in by_type[KeywordType.LONG_TAIL][:top_n]
            ],
            branded_keywords=[
                {
                    "keyword": v.keyword,
                    "volume": v.search_count,
                    "sources": v.sources,
                }
                for v in by_type[KeywordType.BRANDED][:top_n]
            ],
            competitor_keywords=[
                {
                    "keyword": v.keyword,
                    "volume": v.search_count,
                    "sources": v.sources,
                }
                for v in by_type[KeywordType.COMPETITOR][:top_n]
            ],
            trending_keywords=[
                {
                    "keyword": v.keyword,
                    "volume": v.search_count,
                    "velocity": v.search_count / max(1, (datetime.now(UTC) - (v.first_seen if v.first_seen.tzinfo else v.first_seen.replace(tzinfo=UTC))).days),
                    "sources": v.sources,
                }
                for v in trending[:top_n]
            ],
            emerging_keywords=[
                {
                    "keyword": v.keyword,
                    "volume": v.search_count,
                    "first_seen": v.first_seen.isoformat(),
                    "sources": v.sources,
                }
                for v in emerging[:top_n]
            ],
            keywords_by_source=dict(by_source),
            top_words=top_words,
        )
    
    def _identify_trending(
        self,
        volumes: list[PromptVolume],
        period_start: datetime,
        period_end: datetime,
    ) -> list[PromptVolume]:
        """Identify keywords with high velocity (trending up)"""
        
        # Calculate velocity (searches per day since first seen)
        trending = []
        for volume in volumes:
            days_old = max(1, (volume.last_seen - volume.first_seen).days)
            velocity = volume.search_count / days_old
            
            # Trending if velocity > 1 search/day
            if velocity > 1:
                trending.append(volume)
        
        trending.sort(key=lambda v: v.search_count / max(1, (v.last_seen - v.first_seen).days), reverse=True)
        return trending
    
    def _identify_emerging(self, volumes: list[PromptVolume]) -> list[PromptVolume]:
        """Identify emerging keywords (new in last 48 hours)"""
        
        cutoff = datetime.now(UTC) - timedelta(hours=48)
        emerging = [
            v
            for v in volumes
            if (v.first_seen if v.first_seen.tzinfo else v.first_seen.replace(tzinfo=UTC)) >= cutoff
        ]
        emerging.sort(key=lambda v: v.search_count, reverse=True)
        return emerging
    
    def _extract_top_words(self, volumes: list[PromptVolume], top_n: int = 50) -> list[dict[str, Any]]:
        """Extract top individual words from keywords"""
        
        word_count: defaultdict[str, int] = defaultdict(int)
        
        for volume in volumes:
            words = re.split(r'\s+', volume.keyword.lower())
            for word in words:
                if len(word) > 3:  # Filter short words
                    word_count[word] += volume.search_count
        
        top_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        return [
            {"word": word, "count": count}
            for word, count in top_words
        ]
    
    def get_opportunities(
        self,
        tenant_id: str,
        brand_name: str = "",
        min_volume: int = 10,
        max_cpc_estimate: float = 1.0,
    ) -> list[dict[str, Any]]:
        """Find keyword opportunities (trending, not yet covered)"""
        
        relevant = [
            v for v in self.volumes.values()
            if v.tenant_id == tenant_id
            and v.search_count >= min_volume
            and v.relevance_score > 0.5
        ]
        
        # Sort by potential (volume * relevance)
        relevant.sort(
            key=lambda v: v.search_count * v.relevance_score,
            reverse=True
        )
        
        return [
            {
                "keyword": v.keyword,
                "volume": v.search_count,
                "relevance": v.relevance_score,
                "type": v.keyword_type.value,
                "sources": v.sources,
                "potential_score": v.search_count * v.relevance_score,
            }
            for v in relevant[:50]
        ]

# Global collector
prompt_volumes_collector = PromptVolumesCollector()  # type: ignore[no-untyped-call]
