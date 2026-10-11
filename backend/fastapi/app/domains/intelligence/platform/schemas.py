"""Intelligence/Platform request contracts."""

from __future__ import annotations
from pydantic import BaseModel
from pydantic import Field
from typing import Any


class AIValidateRequest(BaseModel):
    """Module 32 — validate an AI output for hallucination & schema compliance."""

    content: str = Field(..., min_length=1, max_length=50000, description="AI-generated text to audit")
    expected_keys: list[str] = Field(
        default_factory=list, description="Required JSON keys if output should be structured"
    )
    schema_type: str = Field(default="free_text", description="free_text | json | structured_seo")
    module: str = Field(default="unknown", max_length=80, description="Originating SEO module name")


class PromptVersionCreateRequest(BaseModel):
    """Module 33 — register a new prompt version."""

    module: str = Field(..., min_length=1, max_length=80)
    prompt_text: str = Field(..., min_length=10, max_length=20000)
    model: str = Field(default="deepseek-r1:8b", max_length=80)
    author: str = Field(default="system", max_length=80)
    tags: list[str] = Field(default_factory=list)


class AgentToolRegisterRequest(BaseModel):
    """Register a new tool in the agent tool registry."""

    key: str = Field(..., min_length=1, max_length=80, pattern="^[a-z0-9_]+$")
    display_name: str = Field(..., min_length=1, max_length=120)
    group_name: str = Field(..., min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    fn_signature: str = Field(..., min_length=1, max_length=200)
    risk_level: str = Field(default="low")
    requires_confirmation: bool = Field(default=False)
    backend_endpoint: str = Field(default="", max_length=200)
    input_schema: dict[str, Any] = Field(default_factory=dict)


class AgentConfigUpdateRequest(BaseModel):
    """Update agent configuration for this tenant."""

    current_phase: str | None = Field(default=None)
    enabled_models: list[str] | None = Field(default=None)
    max_auto_actions: int | None = Field(default=None, ge=0, le=100)
    allow_high_risk_tools: bool | None = Field(default=None)
    mcp_endpoint: str | None = Field(default=None, max_length=200)
    notes: str = Field(default="", max_length=2000)


class RetryRequest(BaseModel):
    """Module 36 — manually trigger retry for a failed job."""

    job_id: str = Field(..., min_length=1, max_length=128)
    reason: str = Field(default="manual_retry", max_length=200)
