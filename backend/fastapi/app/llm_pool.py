"""
ULTIMATE LLM Pool Service

Manages multi-LLM selection, cost optimization, quality scoring, and fallback logic.
All 50 modules use this service instead of calling LLMs directly.

Usage:
    pool = LLMPool(site_id="acme-com", config=site_config)
    llm = pool.select(task="entity_extraction", constraints={"max_cost_usd": 0.10})
    response = llm.invoke(prompt="Extract entities...", temperature=0.1)
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# LLM Provider Definitions
# ============================================================================

class LLMProviderType(StrEnum):
    """Supported LLM providers"""
    OLLAMA = "ollama"  # Local LLM
    OPENAI = "openai"  # GPT-4, GPT-4o Mini
    ANTHROPIC = "anthropic"  # Claude
    MISTRAL = "mistral"  # Mistral
    DEEPSEEK = "deepseek"  # DeepSeek


@dataclass
class LLMProviderConfig:
    """Configuration for an LLM provider"""
    type: LLMProviderType
    model: str  # "gpt-4o-mini", "claude-3-haiku", "llama-3:latest", etc.
    api_key: str | None = None  # None for local providers
    api_url: str | None = None  # ollama: http://localhost:11434
    cost_per_1k_tokens: float = 0.0  # 0 for local
    latency_ms: float = 500  # typical latency
    quality_score: float = 85  # 0-100, subjective quality
    priority: int = 0  # lower = prefer first
    max_tokens: int = 4096
    temperature_default: float = 0.7
    enabled: bool = True


class LLMResponse(BaseModel):
    """Response from LLM"""
    content: str
    model: str
    provider: LLMProviderType
    tokens_used: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    quality_score: float = 0.0


# ============================================================================
# Abstract LLM Provider
# ============================================================================

class BaseLLMProvider(ABC):
    """Abstract base for all LLM providers"""

    def __init__(self, config: LLMProviderConfig):
        self.config = config
        self.client: httpx.AsyncClient | None = None

    @abstractmethod
    async def initialize(self) -> None:
        """Async initialization (connect to API, etc.)"""

    @abstractmethod
    async def close(self) -> None:
        """Cleanup"""

    @abstractmethod
    async def invoke(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Invoke the LLM and return response"""
        pass

    def _estimate_cost(self, tokens_used: int) -> float:
        """Estimate API cost"""
        if self.config.cost_per_1k_tokens == 0:
            return 0.0
        return (tokens_used / 1000) * self.config.cost_per_1k_tokens


# ============================================================================
# Provider Implementations
# ============================================================================

class OllamaProvider(BaseLLMProvider):
    """Local Ollama provider (free, no API key needed)"""

    async def initialize(self) -> None:
        self.client = httpx.AsyncClient(
            base_url=self.config.api_url or "http://localhost:11434"
        )

    async def close(self) -> None:
        if self.client:
            await self.client.aclose()

    async def invoke(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Call local Ollama instance"""
        try:
            start_time = time.time()

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await self.client.post(
                "/api/chat",
                json={
                    "model": self.config.model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": False,
                },
            )
            response.raise_for_status()

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            return LLMResponse(
                content=data.get("message", {}).get("content", ""),
                model=self.config.model,
                provider=LLMProviderType.OLLAMA,
                tokens_used=data.get("prompt_eval_count", 0)
                + data.get("eval_count", 0),
                cost_usd=0.0,  # Local model
                latency_ms=latency_ms,
                quality_score=self.config.quality_score,
            )

        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT-4o Mini provider"""

    async def initialize(self):
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.config.api_key}"}
        )

    async def close(self):
        if self.client:
            await self.client.aclose()

    async def invoke(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Call OpenAI API"""
        try:
            start_time = time.time()

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await self.client.post(
                "https://api.openai.com/v1/chat/completions",
                json={
                    "model": self.config.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=self.config.model,
                provider=LLMProviderType.OPENAI,
                tokens_used=data["usage"]["total_tokens"],
                cost_usd=self._estimate_cost(data["usage"]["total_tokens"]),
                latency_ms=latency_ms,
                quality_score=self.config.quality_score,
            )

        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            raise


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider"""

    async def initialize(self):
        self.client = httpx.AsyncClient(
            headers={
                "x-api-key": self.config.api_key,
                "anthropic-version": "2023-06-01",
            }
        )

    async def close(self):
        if self.client:
            await self.client.aclose()

    async def invoke(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Call Anthropic API"""
        try:
            start_time = time.time()

            response = await self.client.post(
                "https://api.anthropic.com/v1/messages",
                json={
                    "model": self.config.model,
                    "max_tokens": max_tokens,
                    "system": system_prompt or "",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                },
            )
            response.raise_for_status()

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            return LLMResponse(
                content=data["content"][0]["text"],
                model=self.config.model,
                provider=LLMProviderType.ANTHROPIC,
                tokens_used=data["usage"]["input_tokens"]
                + data["usage"]["output_tokens"],
                cost_usd=self._estimate_cost(
                    data["usage"]["input_tokens"] + data["usage"]["output_tokens"]
                ),
                latency_ms=latency_ms,
                quality_score=self.config.quality_score,
            )

        except Exception as e:
            logger.error(f"Anthropic error: {e}")
            raise


# ============================================================================
# LLM Pool (selector)
# ============================================================================

@dataclass
class LLMConstraints:
    """Constraints for LLM selection"""
    max_cost_usd: float = 1.0
    max_latency_ms: float = 10000
    preferred_providers: list[LLMProviderType] = Field(default_factory=list)
    prefer_local: bool = True


class LLMPool:
    """
    Multi-LLM pool selector.
    Intelligently chooses which LLM to use based on task, cost, quality, and latency.
    """

    def __init__(self, site_id: str, config: dict[str, Any] | None = None):
        self.site_id = site_id
        self.config = config or {}
        self.providers: dict[str, BaseLLMProvider] = {}
        self.performance_history: dict[str, list[dict[str, Any]]] = {}

        # Initialize default providers
        self._init_default_providers()

    def _init_default_providers(self) -> None:
        """Initialize default LLM providers from config"""
        providers_config: list[dict[str, Any]] = self.config.get("llm_pool", [])

        # Always add Ollama if not already configured
        if not any(p.get("provider") == "ollama" for p in providers_config):
            providers_config.insert(0, {
                "provider": "ollama",
                "model": "llama-3:latest",
                "api_url": "http://localhost:11434",
                "cost": 0,
                "latency_ms": 800,
                "quality_score": 85,
                "priority": 1,
            })

        # Add OpenAI GPT-4o Mini (fallback)
        if not any(p.get("provider") == "openai" for p in providers_config):
            providers_config.append({
                "provider": "openai",
                "model": "gpt-4o-mini",
                "api_key": self.config.get("openai_api_key"),
                "cost_per_1k_tokens": 0.0015,
                "latency_ms": 300,
                "quality_score": 88,
                "priority": 2,
            })

        # Create provider instances
        for pc in providers_config:
            provider_type = pc.get("provider", "ollama")
            config = LLMProviderConfig(
                type=LLMProviderType(provider_type),
                model=pc.get("model"),
                api_key=pc.get("api_key"),
                api_url=pc.get("api_url"),
                cost_per_1k_tokens=pc.get("cost_per_1k_tokens", 0),
                latency_ms=pc.get("latency_ms", 500),
                quality_score=pc.get("quality_score", 85),
                priority=pc.get("priority", 0),
            )

            if provider_type == "ollama":
                self.providers[f"ollama-{config.model}"] = OllamaProvider(config)
            elif provider_type == "openai":
                self.providers[f"openai-{config.model}"] = OpenAIProvider(config)
            elif provider_type == "anthropic":
                self.providers[f"anthropic-{config.model}"] = AnthropicProvider(config)

    def select(
        self,
        task: str,
        constraints: LLMConstraints | None = None,
    ) -> BaseLLMProvider:
        """
        Select the best LLM for the given task.

        Scoring algorithm:
            base_score = (quality_score / 100) * 0.5 + (1 - cost_penalty) * 0.3 + (1 - latency_penalty) * 0.2
            base_score -= priority_offset

        Args:
            task: e.g., "entity_extraction", "content_generation", "anomaly_detection"
            constraints: max cost, latency, preferred providers

        Returns:
            Selected LLMProvider instance
        """
        constraints = constraints or LLMConstraints()

        best_provider: BaseLLMProvider | None = None
        best_score = -999.0

        for provider_key, provider in self.providers.items():
            if not provider.config.enabled:
                continue

            # Check constraints
            if provider.config.cost_per_1k_tokens > constraints.max_cost_usd:
                continue

            if provider.config.latency_ms > constraints.max_latency_ms:
                continue

            # Compute score
            quality_factor = provider.config.quality_score / 100
            cost_factor = 1 - (
                provider.config.cost_per_1k_tokens / constraints.max_cost_usd
                if constraints.max_cost_usd > 0
                else 0
            )
            latency_factor = 1 - (
                provider.config.latency_ms / constraints.max_latency_ms
            )

            # Task-specific weights
            if task.startswith("content_"):
                quality_weight = 0.6
                cost_weight = 0.2
                latency_weight = 0.2
            elif task.startswith("analysis_"):
                quality_weight = 0.4
                cost_weight = 0.4
                latency_weight = 0.2
            else:  # balanced
                quality_weight = 0.5
                cost_weight = 0.3
                latency_weight = 0.2

            score = (
                quality_factor * quality_weight
                + cost_factor * cost_weight
                + latency_factor * latency_weight
                - (provider.config.priority * 0.05)  # priority offset
            )

            # Prefer local providers
            if (
                constraints.prefer_local
                and provider.config.type == LLMProviderType.OLLAMA
            ):
                score += 0.2

            logger.info(
                f"Task: {task}, Provider: {provider_key}, Score: {score:.3f}"
            )

            if score > best_score:
                best_score = score
                best_provider = provider

        if not best_provider:
            # Fallback to first available provider
            best_provider = next(iter(self.providers.values()))
            logger.warning(
                f"No provider matched constraints for task {task}, using fallback: {best_provider.config.model}"
            )

        logger.info(f"Selected {best_provider.config.model} for task {task}")
        return best_provider

    def record_performance(
        self,
        task: str,
        provider_key: str,
        success: bool,
        latency_ms: float,
        cost_usd: float,
        quality_rating: float = 0.0,
    ) -> None:
        """Record performance metrics for optimization"""
        if task not in self.performance_history:
            self.performance_history[task] = []

        self.performance_history[task].append({
            "provider": provider_key,
            "success": success,
            "latency_ms": latency_ms,
            "cost_usd": cost_usd,
            "quality_rating": quality_rating,
            "timestamp": datetime.now().isoformat(),
        })

        # Keep last 100 runs per task
        if len(self.performance_history[task]) > 100:
            self.performance_history[task] = self.performance_history[task][-100:]

    async def initialize_all(self) -> None:
        """Initialize all providers (for async setup)"""
        await asyncio.gather(
            *[provider.initialize() for provider in self.providers.values()]
        )

    async def close_all(self) -> None:
        """Close all provider connections"""
        await asyncio.gather(
            *[provider.close() for provider in self.providers.values()]
        )


# ============================================================================
# Utility Functions
# ============================================================================

def get_llm_pool_factory(site_config: dict[str, Any]) -> LLMPool:
    """Factory function to create LLM pool for a site"""
    return LLMPool(site_id=str(site_config.get("id", "default")), config=site_config)


async def invoke_with_pool(
    pool: LLMPool,
    task: str,
    prompt: str,
    system_prompt: str | None = None,
    constraints: LLMConstraints | None = None,
) -> tuple[str, float]:
    """
    Helper to invoke an LLM via the pool.

    Returns:
        (response_content, cost_usd)
    """
    llm = pool.select(task=task, constraints=constraints)

    start = time.time()
    response = await llm.invoke(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=llm.config.temperature_default,
    )
    latency = (time.time() - start) * 1000

    pool.record_performance(
        task=task,
        provider_key=f"{llm.config.type.value}-{llm.config.model}",
        success=True,
        latency_ms=latency,
        cost_usd=response.cost_usd,
    )

    logger.info(
        f"Task: {task}, LLM: {llm.config.model}, Cost: ${response.cost_usd:.4f}, Latency: {latency:.0f}ms"
    )

    return response.content, response.cost_usd
