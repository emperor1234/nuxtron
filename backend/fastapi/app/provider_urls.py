"""Endpoints for OpenAI- and Anthropic-compatible providers.

Defaults are the public APIs. An operator can point ``OPENAI_BASE_URL`` or
``ANTHROPIC_BASE_URL`` at a compatible gateway or a local server.
"""
import os


def _base(env_name: str, default: str) -> str:
    return (os.getenv(env_name, "").strip() or default).rstrip("/")


def openai_url(path: str) -> str:
    return f"{_base('OPENAI_BASE_URL', 'https://api.openai.com/v1')}{path}"


def anthropic_url(path: str) -> str:
    return f"{_base('ANTHROPIC_BASE_URL', 'https://api.anthropic.com/v1')}{path}"
