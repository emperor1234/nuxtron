import os
import time
from collections.abc import Callable
from typing import Any, Literal, cast

import httpx

BrainProvider = Literal['auto', 'openai', 'anthropic', 'google_deepmind', 'deepseek', 'llama', 'mistral']
APPLICATION_JSON = 'application/json'


def _as_dict(value: Any) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


class AIBrainModelLayer:
    """Reliability-first model orchestration layer for IRA autonomy reasoning."""

    def __init__(self, *, now_iso_fn: Callable[[], str]) -> None:
        self._now_iso_fn = now_iso_fn

    def _provider_catalog(self) -> dict[str, dict[str, Any]]:
        return {
            'openai': {
                'label': 'OpenAI',
                'type': 'api_model',
                'function_calling': True,
                'long_context_tokens': 128000,
                'reliability': 0.97,
                'configured': bool(os.getenv('OPENAI_API_KEY', '').strip()),
                'model': os.getenv('OPENAI_MODEL', '').strip() or 'gpt-4.1-mini',
            },
            'anthropic': {
                'label': 'Anthropic',
                'type': 'api_model',
                'function_calling': True,
                'long_context_tokens': 200000,
                'reliability': 0.96,
                'configured': bool(os.getenv('ANTHROPIC_API_KEY', '').strip()),
                'model': os.getenv('ANTHROPIC_MODEL', '').strip() or 'claude-3-5-sonnet-latest',
            },
            'google_deepmind': {
                'label': 'Google DeepMind (Vertex Gemini)',
                'type': 'api_model',
                'function_calling': True,
                'long_context_tokens': 1000000,
                'reliability': 0.95,
                'configured': bool(os.getenv('GOOGLE_VERTEX_API_KEY', '').strip() and os.getenv('GOOGLE_VERTEX_PROJECT_ID', '').strip()),
                'model': os.getenv('GOOGLE_VERTEX_MODEL', '').strip() or 'gemini-2.0-flash',
            },
            'deepseek': {
                'label': 'DeepSeek R1 (open-source)',
                'type': 'open_source',
                'function_calling': False,
                'long_context_tokens': 32000,
                'reliability': 0.91,
                'configured': True,
                'model': os.getenv('OLLAMA_DEEPSEEK_MODEL', '').strip()
                or os.getenv('SEO_DEFAULT_MODEL', '').strip()
                or os.getenv('OLLAMA_DEFAULT_MODEL', 'deepseek-r1:8b').strip(),
            },
            'llama': {
                'label': 'Meta LLaMA (open-source)',
                'type': 'open_source',
                'function_calling': False,
                'long_context_tokens': 32000,
                'reliability': 0.9,
                'configured': True,
                'model': os.getenv('OLLAMA_LLAMA_MODEL', '').strip() or os.getenv('OLLAMA_DEFAULT_MODEL', 'llama3.2:3b').strip(),
            },
            'mistral': {
                'label': 'Mistral (open-source/API)',
                'type': 'open_source',
                'function_calling': False,
                'long_context_tokens': 32000,
                'reliability': 0.89,
                'configured': True,
                'model': os.getenv('OLLAMA_MISTRAL_MODEL', '').strip() or os.getenv('OLLAMA_DEFAULT_MODEL', 'mistral:7b').strip(),
            },
        }

    def capabilities(self) -> dict[str, Any]:
        catalog = self._provider_catalog()
        return {
            'principles': {
                'function_calling_priority': True,
                'long_context_priority': True,
                'reliability_over_raw_intelligence': True,
                'training_strategy': 'fine_tune_or_prompt_engineering_over_training_from_scratch',
            },
            'providers': catalog,
            'recommended_order_auto': [
                name
                for name in ['openai', 'anthropic', 'google_deepmind', 'llama', 'mistral']
                if bool(catalog[name]['configured'])
            ],
        }

    def _auto_candidates(self, *, require_function_calling: bool) -> list[str]:
        catalog = self._provider_catalog()
        ranked = ['openai', 'anthropic', 'google_deepmind', 'llama', 'mistral']
        candidates: list[str] = []
        for provider in ranked:
            info = _as_dict(catalog.get(provider))
            if not info:
                continue
            if not bool(info['configured']):
                continue
            if require_function_calling and not bool(info['function_calling']):
                continue
            candidates.append(provider)
        if candidates:
            return candidates
        return ['llama', 'mistral']

    def _openai_reason(self, *, prompt: str, model: str, tools: list[dict[str, Any]], temperature: float, max_tokens: int) -> dict[str, Any]:
        api_key = os.getenv('OPENAI_API_KEY', '').strip()
        if not api_key:
            raise RuntimeError('OpenAI is not configured.')

        payload: dict[str, Any] = {
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        if tools:
            payload['tools'] = tools
            payload['tool_choice'] = 'auto'

        started = time.perf_counter()
        with httpx.Client(timeout=25.0) as client:
            response = client.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': APPLICATION_JSON},
                json=payload,
            )
        latency_ms = int((time.perf_counter() - started) * 1000)
        response.raise_for_status()
        data = _as_dict(response.json())

        choices = _as_list(data.get('choices'))
        choice = _as_dict(choices[0]) if choices else {}
        message = _as_dict(choice.get('message'))
        content = str(message.get('content', '')).strip()
        tool_calls = _as_list(message.get('tool_calls'))

        return {
            'provider': 'openai',
            'model': model,
            'output_text': content,
            'tool_calls': tool_calls if isinstance(tool_calls, list) else [],
            'function_calling_used': bool(tool_calls),
            'latency_ms': latency_ms,
        }

    def _anthropic_reason(self, *, prompt: str, model: str, temperature: float, max_tokens: int) -> dict[str, Any]:
        api_key = os.getenv('ANTHROPIC_API_KEY', '').strip()
        if not api_key:
            raise RuntimeError('Anthropic is not configured.')

        started = time.perf_counter()
        with httpx.Client(timeout=25.0) as client:
            response = client.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01',
                    'Content-Type': APPLICATION_JSON,
                },
                json={
                    'model': model,
                    'max_tokens': max_tokens,
                    'temperature': temperature,
                    'messages': [{'role': 'user', 'content': prompt}],
                },
            )
        latency_ms = int((time.perf_counter() - started) * 1000)
        response.raise_for_status()
        data = _as_dict(response.json())
        content = _as_list(data.get('content'))
        texts: list[str] = []
        for item in content:
            item_map = _as_dict(item)
            if str(item_map.get('type', '')) == 'text':
                texts.append(str(item_map.get('text', '')))

        return {
            'provider': 'anthropic',
            'model': model,
            'output_text': '\n'.join(texts).strip(),
            'tool_calls': [],
            'function_calling_used': False,
            'latency_ms': latency_ms,
        }

    def _google_reason(self, *, prompt: str, model: str, temperature: float, max_tokens: int) -> dict[str, Any]:
        token = os.getenv('GOOGLE_VERTEX_API_KEY', '').strip()
        project_id = os.getenv('GOOGLE_VERTEX_PROJECT_ID', '').strip()
        location = os.getenv('GOOGLE_VERTEX_LOCATION', 'us-central1').strip() or 'us-central1'
        if not token or not project_id:
            raise RuntimeError('Google DeepMind (Vertex) is not configured.')

        url = (
            f'https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}'
            f'/locations/{location}/publishers/google/models/{model}:generateContent'
        )

        started = time.perf_counter()
        with httpx.Client(timeout=25.0) as client:
            response = client.post(
                url,
                headers={'Authorization': f'Bearer {token}', 'Content-Type': APPLICATION_JSON},
                json={
                    'contents': [{'role': 'user', 'parts': [{'text': prompt}]}],
                    'generationConfig': {'temperature': temperature, 'maxOutputTokens': max_tokens},
                },
            )
        latency_ms = int((time.perf_counter() - started) * 1000)
        response.raise_for_status()
        data = _as_dict(response.json())

        output_text = ''
        candidates = _as_list(data.get('candidates'))
        if candidates:
            candidate = _as_dict(candidates[0])
            content = _as_dict(candidate.get('content'))
            parts = _as_list(content.get('parts'))
            chunked = [str(_as_dict(item).get('text', '')) for item in parts]
            output_text = '\n'.join(chunked).strip()

        return {
            'provider': 'google_deepmind',
            'model': model,
            'output_text': output_text,
            'tool_calls': [],
            'function_calling_used': False,
            'latency_ms': latency_ms,
        }

    def _ollama_reason(self, *, provider: str, prompt: str, model: str, temperature: float) -> dict[str, Any]:
        base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434').strip() or 'http://localhost:11434'
        ollama_timeout = float(os.getenv('OLLAMA_CHAT_TIMEOUT_SECONDS', '90').strip() or '90')
        started = time.perf_counter()
        with httpx.Client(timeout=ollama_timeout) as client:
            response = client.post(
                f'{base_url}/api/chat',
                json={
                    'model': model,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'stream': False,
                    'options': {'temperature': temperature},
                },
            )
        latency_ms = int((time.perf_counter() - started) * 1000)
        response.raise_for_status()
        data = _as_dict(response.json())
        message = _as_dict(data.get('message'))
        output_text = str(message.get('content', '')).strip()

        return {
            'provider': provider,
            'model': model,
            'output_text': output_text,
            'tool_calls': [],
            'function_calling_used': False,
            'latency_ms': latency_ms,
        }

    def reason(
        self,
        *,
        prompt: str,
        provider: BrainProvider = 'auto',
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> dict[str, Any]:
        tools_list = tools or []
        require_function_calling = bool(tools_list)
        catalog = self._provider_catalog()

        if provider == 'auto':
            candidates = self._auto_candidates(require_function_calling=require_function_calling)
        else:
            candidates = [provider]

        errors: list[str] = []
        for candidate in candidates:
            model = str(catalog.get(candidate, {}).get('model', '')).strip()
            try:
                if candidate == 'openai':
                    result = self._openai_reason(
                        prompt=prompt,
                        model=model,
                        tools=tools_list,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                elif candidate == 'anthropic':
                    result = self._anthropic_reason(prompt=prompt, model=model, temperature=temperature, max_tokens=max_tokens)
                elif candidate == 'google_deepmind':
                    result = self._google_reason(prompt=prompt, model=model, temperature=temperature, max_tokens=max_tokens)
                elif candidate in {'deepseek', 'llama', 'mistral'}:
                    result = self._ollama_reason(provider=candidate, prompt=prompt, model=model, temperature=temperature)
                else:
                    continue

                if str(result.get('output_text', '')).strip():
                    return {
                        'status': 'ok',
                        'reasoning': {
                            **result,
                            'fallback_count': len(errors),
                            'at': self._now_iso_fn(),
                        },
                    }
                errors.append(f'{candidate}:empty_output')
            except Exception as ex:
                errors.append(f'{candidate}:{type(ex).__name__}')

        return {
            'status': 'fallback',
            'reasoning': {
                'provider': 'fallback_stub',
                'model': 'rule_based',
                'output_text': (
                    'IRA fallback reasoning path: use risk-first execution, preserve auditability, '
                    'and require explicit approvals before high-impact actions.'
                ),
                'tool_calls': [],
                'function_calling_used': False,
                'fallback_count': len(errors),
                'errors': errors,
                'at': self._now_iso_fn(),
            },
        }
