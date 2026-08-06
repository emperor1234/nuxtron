from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock

os.environ.setdefault('NUXTRON_SKIP_STARTUP_DB_INIT', '1')
os.environ.setdefault('FASTAPI_API_KEY', 'test-api-key')

from backend.fastapi.app.llm_pool import (
    AnthropicProvider,
    LLMConstraints,
    LLMPool,
    LLMProviderConfig,
    LLMProviderType,
    LLMResponse,
    OllamaProvider,
    OpenAIProvider,
    invoke_with_pool,
)


def test_ollama_invoke_success_path_with_system_prompt() -> None:
    provider = OllamaProvider(LLMProviderConfig(type=LLMProviderType.OLLAMA, model='llama-3:latest', api_url='http://localhost:11434'))

    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {'message': {'content': 'local answer'}, 'prompt_eval_count': 11, 'eval_count': 7}

    post_mock = AsyncMock(return_value=response)
    provider.client = MagicMock()
    provider.client.post = post_mock

    result = asyncio.run(provider.invoke('hello', temperature=0.2, system_prompt='be concise'))
    assert result.provider == LLMProviderType.OLLAMA
    assert result.content == 'local answer'
    assert result.tokens_used == 18
    assert result.cost_usd == 0.0
    assert result.latency_ms >= 0


def test_openai_and_anthropic_invoke_success_paths() -> None:
    openai = OpenAIProvider(
        LLMProviderConfig(type=LLMProviderType.OPENAI, model='gpt-4o-mini', api_key='sk-test', cost_per_1k_tokens=0.0015)
    )
    openai_response = MagicMock()
    openai_response.raise_for_status.return_value = None
    openai_response.json.return_value = {
        'choices': [{'message': {'content': 'openai answer'}}],
        'usage': {'total_tokens': 1200},
    }
    openai.client = MagicMock()
    openai.client.post = AsyncMock(return_value=openai_response)

    openai_result = asyncio.run(openai.invoke('prompt', temperature=0.3, max_tokens=512))
    assert openai_result.provider == LLMProviderType.OPENAI
    assert openai_result.tokens_used == 1200
    assert openai_result.cost_usd > 0

    anthropic = AnthropicProvider(
        LLMProviderConfig(type=LLMProviderType.ANTHROPIC, model='claude-3-haiku', api_key='ak-test', cost_per_1k_tokens=0.0008)
    )
    anthropic_response = MagicMock()
    anthropic_response.raise_for_status.return_value = None
    anthropic_response.json.return_value = {
        'content': [{'text': 'anthropic answer'}],
        'usage': {'input_tokens': 400, 'output_tokens': 200},
    }
    anthropic.client = MagicMock()
    anthropic.client.post = AsyncMock(return_value=anthropic_response)

    anthropic_result = asyncio.run(anthropic.invoke('prompt', system_prompt='sys'))
    assert anthropic_result.provider == LLMProviderType.ANTHROPIC
    assert anthropic_result.tokens_used == 600
    assert anthropic_result.cost_usd > 0


def test_pool_initialize_close_and_invoke_with_pool_records_history() -> None:
    pool = LLMPool(site_id='llm-branch-site')

    for provider in pool.providers.values():
        provider.initialize = AsyncMock(return_value=None)
        provider.close = AsyncMock(return_value=None)

    asyncio.run(pool.initialize_all())
    asyncio.run(pool.close_all())

    fake_provider = MagicMock()
    fake_provider.config.type = LLMProviderType.OLLAMA
    fake_provider.config.model = 'llama-3:latest'
    fake_provider.config.temperature_default = 0.7
    fake_provider.invoke = AsyncMock(
        return_value=LLMResponse(
            content='pooled response',
            model='llama-3:latest',
            provider=LLMProviderType.OLLAMA,
            tokens_used=123,
            cost_usd=0.0,
            latency_ms=50.0,
            quality_score=85.0,
        )
    )
    pool.select = MagicMock(return_value=fake_provider)

    content, cost = asyncio.run(
        invoke_with_pool(
            pool,
            task='content_generation',
            prompt='Draft a short post',
            constraints=LLMConstraints(max_cost_usd=0.1, max_latency_ms=1000),
        )
    )
    assert content == 'pooled response'
    assert cost == 0.0
    assert 'content_generation' in pool.performance_history
    assert pool.performance_history['content_generation'][-1]['success'] is True


def test_select_filters_and_fallback_branch() -> None:
    pool = LLMPool(
        site_id='llm-fallback-site',
        config={
            'llm_pool': [
                {
                    'provider': 'openai',
                    'model': 'gpt-4o-mini',
                    'api_key': 'sk-test',
                    'cost_per_1k_tokens': 2.0,
                    'latency_ms': 15000,
                    'quality_score': 99,
                    'priority': 0,
                }
            ]
        },
    )
    selected = pool.select(task='analysis_finance', constraints=LLMConstraints(max_cost_usd=0.0001, max_latency_ms=10, prefer_local=False))
    assert selected is not None