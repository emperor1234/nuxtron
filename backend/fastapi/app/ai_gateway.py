"""AI Gateway: Provider configuration, selection, and generation utilities."""

import logging
import os
import time
from typing import Any, cast

import httpx

from .auth_utils import extract_ip_hash, extract_ua_hash
from .deps import AuthContext
from .transparent_encryption import te_decrypt

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]

# ── Multi-provider AI backend with 24/7 failover & cost optimization ──────────
# Tier 1 (Primary): High quality, preferred cost-quality ratio
# Tier 2 (Secondary): Mid-tier backup, acceptable quality, lower cost
# Tier 3 (Tertiary): Last-resort backup, basic quality, minimal cost
# Tier 4 (Emergency): Fallback-of-fallback for extreme reliability

CONTENT_TYPE_JSON = 'application/json'

AI_PROVIDER_TIERS: dict[str, dict[str, list[str]]] = {
    'text_generation': {
        'tier_1': ['anthropic', 'openai'],  # Primary: best quality
        'tier_2': ['google_vertex'],  # Secondary: good quality, cheaper
        'tier_3': ['cohere', 'mistral'],  # Tertiary: acceptable quality, budget-friendly
        'tier_4': ['together_ai'],  # Emergency: always available fallback
    },
    'summarization': {
        'tier_1': ['openai', 'anthropic'],
        'tier_2': ['google_vertex', 'cohere'],
        'tier_3': ['mistral'],
        'tier_4': ['together_ai'],
    },
    'image_generation': {
        'tier_1': ['openai'],  # DALL-E best quality
        'tier_2': ['google_vertex'],  # Imagen fast & good
        'tier_3': ['stability_ai'],  # Stable Diffusion budget
        'tier_4': ['together_ai'],  # Fallback
    },
}

AI_PROVIDERS: tuple[str, ...] = (
    # Tier 1 (Primary)
    'openai', 'anthropic',
    # Tier 2 (Secondary)
    'google_vertex',
    # Tier 3 (Tertiary)  
    'cohere', 'mistral',
    # Tier 4 (Emergency)
    'together_ai', 'stability_ai',
)

# Model name constants
GEMINI_FLASH_MODEL = 'gemini-2.0-flash'
IMAGE_GENERATION_MODEL = 'imagegeneration@006'
LLAMA_70B_MODEL = 'meta-llama/Llama-3-70b'

# MIME type constants
MIME_TYPE_PNG = 'image/png'
MIME_TYPE_MP3 = 'audio/mpeg'
MIME_TYPE_WAV = 'audio/wav'
MIME_TYPE_MP4 = 'video/mp4'

# ISO 8601 timezone offset constant
UTC_OFFSET = '+00:00'

AI_MODEL_CATALOG: dict[str, dict[str, dict[str, float]]] = {
    'openai': {
        'gpt-4o-mini': {'cost_per_1k_tokens': 0.0006, 'quality_score': 0.83, 'uptime_percent': 99.95, 'latency_ms': 500},
        'gpt-4.1-mini': {'cost_per_1k_tokens': 0.0009, 'quality_score': 0.87, 'uptime_percent': 99.95, 'latency_ms': 450},
        'gpt-4': {'cost_per_1k_tokens': 0.003, 'quality_score': 0.95, 'uptime_percent': 99.95, 'latency_ms': 800},
    },
    'anthropic': {
        'claude-3-5-haiku-latest': {'cost_per_1k_tokens': 0.0010, 'quality_score': 0.85, 'uptime_percent': 99.9, 'latency_ms': 400},
        'claude-3-5-sonnet-latest': {'cost_per_1k_tokens': 0.0030, 'quality_score': 0.93, 'uptime_percent': 99.9, 'latency_ms': 600},
        'claude-3-opus': {'cost_per_1k_tokens': 0.0075, 'quality_score': 0.97, 'uptime_percent': 99.9, 'latency_ms': 1200},
    },
    'google_vertex': {
        GEMINI_FLASH_MODEL: {'cost_per_1k_tokens': 0.00015, 'quality_score': 0.85, 'uptime_percent': 99.8, 'latency_ms': 350},
        'gemini-2.0-pro': {'cost_per_1k_tokens': 0.0010, 'quality_score': 0.92, 'uptime_percent': 99.8, 'latency_ms': 700},
        IMAGE_GENERATION_MODEL: {'cost_per_1k_tokens': 0.0005, 'quality_score': 0.90, 'uptime_percent': 99.8, 'latency_ms': 800},
    },
    'cohere': {
        'command-r': {'cost_per_1k_tokens': 0.0005, 'quality_score': 0.78, 'uptime_percent': 99.5, 'latency_ms': 300},
        'command-r-plus': {'cost_per_1k_tokens': 0.001, 'quality_score': 0.82, 'uptime_percent': 99.5, 'latency_ms': 400},
    },
    'mistral': {
        'mistral-large': {'cost_per_1k_tokens': 0.0008, 'quality_score': 0.80, 'uptime_percent': 99.7, 'latency_ms': 350},
        'mistral-small': {'cost_per_1k_tokens': 0.0002, 'quality_score': 0.70, 'uptime_percent': 99.7, 'latency_ms': 250},
    },
    'together_ai': {
        LLAMA_70B_MODEL: {'cost_per_1k_tokens': 0.0008, 'quality_score': 0.75, 'uptime_percent': 99.99, 'latency_ms': 400},
        'NousResearch/Nous-Hermes-2-Mixtral-8x7B': {'cost_per_1k_tokens': 0.0006, 'quality_score': 0.72, 'uptime_percent': 99.99, 'latency_ms': 350},
    },
    'stability_ai': {
        'stable-diffusion-3': {'cost_per_1k_tokens': 0.002, 'quality_score': 0.85, 'uptime_percent': 99.6, 'latency_ms': 5000},
        'stable-diffusion-ultra': {'cost_per_1k_tokens': 0.004, 'quality_score': 0.92, 'uptime_percent': 99.6, 'latency_ms': 8000},
    },
}

# Provider health tracking (in-memory, reset on restart)
_provider_health_metrics: dict[str, dict[str, float]] = {
    provider: {
        'success_rate': 1.0,
        'avg_latency_ms': 0.0,
        'last_error_at': 0,
        'consecutive_errors': 0,
        'requests_total': 0,
        'requests_success': 0,
        'updated_at': time.time(),
    }
    for provider in AI_PROVIDERS
}


def provider_env_key(provider: str) -> str:
    """Get the environment variable key for a provider's API key."""
    env_keys = {
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
        'google_vertex': 'GOOGLE_VERTEX_API_KEY',
        'cohere': 'COHERE_API_KEY',
        'mistral': 'MISTRAL_API_KEY',
        'together_ai': 'TOGETHER_AI_API_KEY',
        'stability_ai': 'STABILITY_AI_API_KEY',
    }
    return os.getenv(env_keys.get(provider, ''), '').strip()


def provider_default_model(provider: str) -> str:
    """Get the default model for a provider."""
    defaults = {
        'openai': os.getenv('OPENAI_MODEL', 'gpt-4o-mini').strip() or 'gpt-4o-mini',
        'anthropic': os.getenv('ANTHROPIC_MODEL', 'claude-3-5-haiku-latest').strip() or 'claude-3-5-haiku-latest',
        'google_vertex': os.getenv('GOOGLE_VERTEX_MODEL', GEMINI_FLASH_MODEL).strip() or GEMINI_FLASH_MODEL,
        'cohere': os.getenv('COHERE_MODEL', 'command-r').strip() or 'command-r',
        'mistral': os.getenv('MISTRAL_MODEL', 'mistral-large').strip() or 'mistral-large',
        'together_ai': os.getenv('TOGETHER_AI_MODEL', LLAMA_70B_MODEL).strip() or LLAMA_70B_MODEL,
        'stability_ai': os.getenv('STABILITY_AI_MODEL', 'stable-diffusion-3').strip() or 'stable-diffusion-3',
    }
    return defaults.get(provider, '')


def model_unit_cost(provider: str, model: str) -> float:
    """Get the cost per 1k tokens for a model."""
    provider_models = AI_MODEL_CATALOG.get(provider, {})
    model_meta = provider_models.get(model, {})
    value = model_meta.get('cost_per_1k_tokens', 0.002)
    return float(value if value > 0 else 0.002)


def model_quality(provider: str, model: str) -> float:
    """Get the quality score for a model."""
    provider_models = AI_MODEL_CATALOG.get(provider, {})
    model_meta = provider_models.get(model, {})
    value = model_meta.get('quality_score', 0.8)
    return float(value if value > 0 else 0.8)


def coerce_int(value: object, default: int = 0) -> int:
    """Coerce a value to int safely."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def coerce_float(value: object, default: float = 0.0) -> float:
    """Coerce a value to float safely."""
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def usage_to_tokens(usage: object) -> tuple[int, int, int]:
    """Extract token counts from usage object."""
    usage_obj = cast(JsonObject, usage) if isinstance(usage, dict) else {}
    prompt_tokens = coerce_int(usage_obj.get('prompt_tokens', 0), 0) + coerce_int(usage_obj.get('input_tokens', 0), 0)
    completion_tokens = coerce_int(usage_obj.get('completion_tokens', 0), 0) + coerce_int(usage_obj.get('output_tokens', 0), 0)
    total_tokens = coerce_int(usage_obj.get('total_tokens', 0), 0)
    if total_tokens <= 0:
        total_tokens = prompt_tokens + completion_tokens
    return prompt_tokens, completion_tokens, max(total_tokens, 0)


def compute_roi(total_tokens: int, value_per_1k_tokens: float, cost_per_1k_tokens: float, quality_score: float) -> tuple[float, float, float]:
    """Compute ROI metrics for AI usage."""
    token_units = max(total_tokens, 0) / 1000.0
    estimated_cost = token_units * max(cost_per_1k_tokens, 0.000001)
    estimated_value = token_units * max(value_per_1k_tokens, 0.000001) * max(quality_score, 0.01)
    if estimated_cost <= 0:
        return 0.0, estimated_cost, estimated_value
    roi = (estimated_value - estimated_cost) / estimated_cost
    return round(roi, 6), round(estimated_cost, 8), round(estimated_value, 8)


def resolve_provider_api_key(provider: str, ai_provider_keys_memory: list[JsonObject]) -> str:
    """Resolve the API key for a provider, checking stored keys first."""
    # Check stored keys first
    with _ai_security_lock:
        for item in reversed(ai_provider_keys_memory):
            if item.get('provider') == provider and item.get('enabled') is True:
                cipher = str(item.get('api_key_cipher', '') or '')
                secret = te_decrypt(cipher) or ''
                if secret:
                    return secret
    # Fall back to environment variable
    return provider_env_key(provider)


def is_provider_disabled(provider: str, ai_provider_keys_memory: list[JsonObject]) -> bool:
    """Check if a provider is disabled."""
    with _ai_security_lock:
        for item in reversed(ai_provider_keys_memory):
            if item.get('provider') == provider:
                enabled = bool(item.get('enabled'))
                return not enabled
    return False


def get_provider_health(provider: str) -> dict[str, float]:
    """Get provider health metrics for intelligent selection."""
    with _ai_security_lock:
        return _provider_health_metrics.get(provider, {
            'success_rate': 1.0,
            'avg_latency_ms': 0.0,
            'consecutive_errors': 0,
        })


# Thread lock for AI security operations
import threading
_ai_security_lock = threading.Lock()
