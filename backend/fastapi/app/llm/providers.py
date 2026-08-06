"""
LLM Provider Abstraction Layer

Unified interface for multiple LLM providers:
- OpenAI (GPT-4, GPT-4-turbo, GPT-3.5)
- Anthropic Claude (Claude 3 Opus, Sonnet, Haiku)
- Google Gemini (Pro, Ultra)
- Perplexity (Online search models)

This layer handles:
- Provider selection & routing
- Token counting & cost estimation
- Retry logic & error handling
- Rate limiting
- Caching
"""

import asyncio
import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import StrEnum

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class LLMProvider(StrEnum):
    """Available LLM providers"""
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    PERPLEXITY = "perplexity"

class LLMModel(StrEnum):
    """Available models"""
    # OpenAI
    GPT_4_TURBO = "gpt-4-turbo-preview"
    GPT_4 = "gpt-4"
    GPT_35_TURBO = "gpt-3.5-turbo"
    
    # Claude
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"
    
    # Gemini
    GEMINI_PRO = "gemini-pro"
    GEMINI_PRO_VISION = "gemini-pro-vision"
    
    # Perplexity
    PPLX_7B_ONLINE = "pplx-7b-online"
    PPLX_70B_ONLINE = "pplx-70b-online"

class CompletionMessage(BaseModel):
    """Message in completion request/response"""
    role: str  # "system", "user", "assistant"
    content: str

class CompletionRequest(BaseModel):
    """Request for LLM completion"""
    model: LLMModel
    messages: list[CompletionMessage]
    max_tokens: int = 1024
    temperature: float = Field(default=0.7, ge=0, le=2)
    top_p: float = Field(default=1.0, ge=0, le=1)
    frequency_penalty: float = Field(default=0, ge=-2, le=2)
    presence_penalty: float = Field(default=0, ge=-2, le=2)
    stop: list[str] | None = None
    stream: bool = False

class CompletionResponse(BaseModel):
    """Response from LLM completion"""
    provider: LLMProvider
    model: LLMModel
    content: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    finish_reason: str  # "stop", "length", "content_filter", etc
    cost_usd: float
    latency_ms: int

class BaseLLMProvider(ABC):
    """Abstract base for LLM providers"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient()
        self.cache: dict[str, CompletionResponse] = {}
        self.rate_limit_reset: float = 0.0
        self.requests_this_minute: int = 0
    
    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Generate completion"""
        pass
    
    @abstractmethod
    def estimate_tokens(self, text: str, model: LLMModel) -> int:
        """Estimate token count"""
        pass
    
    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int, model: LLMModel) -> float:
        """Estimate completion cost in USD"""
        pass
    
    def _get_cache_key(self, request: CompletionRequest) -> str:
        """Generate cache key for request"""
        msg_hash = hashlib.md5(
            json.dumps([m.dict() for m in request.messages]).encode(), usedforsecurity=False,
        ).hexdigest()
        return f"{request.model}:{msg_hash}"
    
    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting"""
        now = datetime.utcnow()
        if now > datetime.utcfromtimestamp(self.rate_limit_reset):
            self.requests_this_minute = 0
            self.rate_limit_reset = (now + timedelta(minutes=1)).timestamp()
        
        if self.requests_this_minute >= 60:  # 60 requests/min per API
            wait_time = self.rate_limit_reset - now.timestamp()
            logger.warning(f"Rate limit reached, waiting {wait_time}s")
            await asyncio.sleep(wait_time)
            self.requests_this_minute = 0
        
        self.requests_this_minute += 1

class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider"""
    
    PRICING = {
        LLMModel.GPT_4_TURBO: {"input": 0.01, "output": 0.03},  # per 1K tokens
        LLMModel.GPT_4: {"input": 0.03, "output": 0.06},
        LLMModel.GPT_35_TURBO: {"input": 0.0005, "output": 0.0015},
    }
    
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Complete using OpenAI API"""
        import time
        start = time.time()
        
        # Check cache
        cache_key = self._get_cache_key(request)
        if cache_key in self.cache and not request.stream:
            logger.info(f"Cache hit for {request.model}")
            return self.cache[cache_key]
        
        try:
            await self._check_rate_limit()
            
            response = await self.client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": request.model.value,
                    "messages": [m.dict() for m in request.messages],
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "top_p": request.top_p,
                    "frequency_penalty": request.frequency_penalty,
                    "presence_penalty": request.presence_penalty,
                    "stop": request.stop,
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            input_tokens = data["usage"]["prompt_tokens"]
            output_tokens = data["usage"]["completion_tokens"]
            
            result = CompletionResponse(
                provider=LLMProvider.OPENAI,
                model=request.model,
                content=data["choices"][0]["message"]["content"],
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=data["usage"]["total_tokens"],
                finish_reason=data["choices"][0]["finish_reason"],
                cost_usd=self.estimate_cost(input_tokens, output_tokens, request.model),
                latency_ms=int((time.time() - start) * 1000)
            )
            
            # Cache result
            if not request.stream:
                self.cache[cache_key] = result
            
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def estimate_tokens(self, text: str, model: LLMModel) -> int:
        """Rough token estimation (4 chars ≈ 1 token)"""
        return len(text) // 4

    def estimate_cost(self, input_tokens: int, output_tokens: int, model: LLMModel) -> float:
        """Calculate cost for completion"""
        pricing = self.PRICING.get(model, {"input": 0, "output": 0})
        return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000

class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude provider"""
    
    PRICING = {
        LLMModel.CLAUDE_3_OPUS: {"input": 0.015, "output": 0.075},  # per 1K tokens
        LLMModel.CLAUDE_3_SONNET: {"input": 0.003, "output": 0.015},
        LLMModel.CLAUDE_3_HAIKU: {"input": 0.00025, "output": 0.00125},
    }
    
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Complete using Claude API"""
        import time
        start = time.time()
        
        cache_key = self._get_cache_key(request)
        if cache_key in self.cache and not request.stream:
            return self.cache[cache_key]
        
        try:
            await self._check_rate_limit()
            
            response = await self.client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": request.model.value,
                    "max_tokens": request.max_tokens,
                    "messages": [m.dict() for m in request.messages],
                    "temperature": request.temperature,
                    "top_p": request.top_p,
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            input_tokens = data["usage"]["input_tokens"]
            output_tokens = data["usage"]["output_tokens"]
            
            result = CompletionResponse(
                provider=LLMProvider.CLAUDE,
                model=request.model,
                content=data["content"][0]["text"],
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                finish_reason=data["stop_reason"],
                cost_usd=self.estimate_cost(input_tokens, output_tokens, request.model),
                latency_ms=int((time.time() - start) * 1000)
            )
            
            if not request.stream:
                self.cache[cache_key] = result
            
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"Claude API error: {e}")
            raise

    def estimate_tokens(self, text: str, model: LLMModel) -> int:
        """Rough token estimation"""
        return len(text) // 4

    def estimate_cost(self, input_tokens: int, output_tokens: int, model: LLMModel) -> float:
        """Calculate cost for completion"""
        pricing = self.PRICING.get(model, {"input": 0, "output": 0})
        return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000

class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider"""
    
    PRICING = {
        LLMModel.GEMINI_PRO: {"input": 0.0005, "output": 0.0015},  # per 1K tokens
        LLMModel.GEMINI_PRO_VISION: {"input": 0.0005, "output": 0.0015},
    }
    
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Complete using Gemini API"""
        import time
        start = time.time()
        
        cache_key = self._get_cache_key(request)
        if cache_key in self.cache and not request.stream:
            return self.cache[cache_key]
        
        try:
            await self._check_rate_limit()
            
            response = await self.client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{request.model.value}:generateContent",
                params={"key": self.api_key},
                json={
                    "contents": [
                        {
                            "parts": [{"text": request.messages[-1].content}]  # Use last message
                        }
                    ],
                    "generationConfig": {
                        "maxOutputTokens": request.max_tokens,
                        "temperature": request.temperature,
                        "topP": request.top_p,
                    }
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # Gemini doesn't return exact token counts, estimate them
            input_text = "\n".join([m.content for m in request.messages])
            output_text = data["candidates"][0]["content"]["parts"][0]["text"]
            
            input_tokens = self.estimate_tokens(input_text, request.model)
            output_tokens = self.estimate_tokens(output_text, request.model)
            
            result = CompletionResponse(
                provider=LLMProvider.GEMINI,
                model=request.model,
                content=output_text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                finish_reason=data["candidates"][0].get("finishReason", "STOP"),
                cost_usd=self.estimate_cost(input_tokens, output_tokens, request.model),
                latency_ms=int((time.time() - start) * 1000)
            )
            
            if not request.stream:
                self.cache[cache_key] = result
            
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"Gemini API error: {e}")
            raise

    def estimate_tokens(self, text: str, model: LLMModel) -> int:
        """Rough token estimation"""
        return len(text) // 4

    def estimate_cost(self, input_tokens: int, output_tokens: int, model: LLMModel) -> float:
        """Calculate cost for completion"""
        pricing = self.PRICING.get(model, {"input": 0, "output": 0})
        return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000

class PerplexityProvider(BaseLLMProvider):
    """Perplexity API provider (online search models)"""
    
    PRICING = {
        LLMModel.PPLX_7B_ONLINE: {"input": 0.0007, "output": 0.0028},
        LLMModel.PPLX_70B_ONLINE: {"input": 0.007, "output": 0.028},
    }
    
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Complete using Perplexity API (with live web search)"""
        import time
        start = time.time()
        
        try:
            await self._check_rate_limit()
            
            response = await self.client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": request.model.value,
                    "messages": [m.dict() for m in request.messages],
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "top_p": request.top_p,
                    "return_citations": True,
                    "search_domain_filter": [],
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            input_tokens = data["usage"].get("prompt_tokens", 0)
            output_tokens = data["usage"].get("completion_tokens", 0)
            
            result = CompletionResponse(
                provider=LLMProvider.PERPLEXITY,
                model=request.model,
                content=data["choices"][0]["message"]["content"],
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                finish_reason=data["choices"][0].get("finish_reason", "stop"),
                cost_usd=self.estimate_cost(input_tokens, output_tokens, request.model),
                latency_ms=int((time.time() - start) * 1000)
            )
            
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"Perplexity API error: {e}")
            raise

    def estimate_tokens(self, text: str, model: LLMModel) -> int:
        """Rough token estimation"""
        return len(text) // 4

    def estimate_cost(self, input_tokens: int, output_tokens: int, model: LLMModel) -> float:
        """Calculate cost for completion"""
        pricing = self.PRICING.get(model, {"input": 0, "output": 0})
        return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000

class LLMRouter:
    """Route requests to appropriate LLM provider"""
    
    def __init__(self):
        self.providers = {
            LLMProvider.OPENAI: OpenAIProvider(os.getenv("OPENAI_API_KEY", "")),
            LLMProvider.CLAUDE: ClaudeProvider(os.getenv("ANTHROPIC_API_KEY", "")),
            LLMProvider.GEMINI: GeminiProvider(os.getenv("GOOGLE_AI_API_KEY", "")),
            LLMProvider.PERPLEXITY: PerplexityProvider(os.getenv("PERPLEXITY_API_KEY", "")),
        }
    
    def get_provider_for_model(self, model: LLMModel) -> BaseLLMProvider:
        """Get appropriate provider for model"""
        if "gpt" in model.value:
            return self.providers[LLMProvider.OPENAI]
        elif "claude" in model.value:
            return self.providers[LLMProvider.CLAUDE]
        elif "gemini" in model.value:
            return self.providers[LLMProvider.GEMINI]
        elif "pplx" in model.value:
            return self.providers[LLMProvider.PERPLEXITY]
        else:
            return self.providers[LLMProvider.OPENAI]  # Default
    
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Route completion request to appropriate provider"""
        provider = self.get_provider_for_model(request.model)
        return await provider.complete(request)

# Global router instance
llm_router = LLMRouter()  # type: ignore[no-untyped-call]

async def get_completion(
    messages: list[dict[str, str]],
    model: LLMModel = LLMModel.GPT_4_TURBO,
    max_tokens: int = 1024,
    temperature: float = 0.7,
) -> CompletionResponse:
    """Convenience function for getting LLM completion"""
    request = CompletionRequest(
        model=model,
        messages=[CompletionMessage(**m) for m in messages],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return await llm_router.complete(request)
