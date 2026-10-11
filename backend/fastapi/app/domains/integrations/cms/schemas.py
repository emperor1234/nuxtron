"""Integrations/Cms request contracts."""

from __future__ import annotations
from pydantic import BaseModel
from pydantic import Field


class CmsConnectionRequest(BaseModel):
    cms_type: str = Field(min_length=1, max_length=40)
    display_name: str = Field(min_length=1, max_length=120)
    api_url: str = Field(default="", max_length=500)
    api_key: str = Field(default="", max_length=320)
    site_id: str = Field(default="", max_length=120)


class CmsPublishRequest(BaseModel):
    connection_id: int
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=10, max_length=100000)
    slug: str = Field(default="", max_length=240)
    tags: list[str] = Field(default_factory=list, max_length=20)
    inject_schema: bool = True
    status: str = Field(default="publish", max_length=20)


class CmsSyncRequest(BaseModel):
    connection_id: int
    direction: str = Field(default="push", pattern="^(push|pull|bidirectional)$")


class CmsSchemaInjectRequest(BaseModel):
    connection_id: int
    page_id: str = Field(min_length=1, max_length=120)
    schema_type: str = Field(default="Article", max_length=80)


class CmsAttributionLinkRequest(BaseModel):
    connection_id: int
    page_id: int | None = None
    page_slug: str | None = Field(default=None, max_length=240)
    campaign: str = Field(min_length=1, max_length=120)
    source: str = Field(default="direct", max_length=80)
    medium: str = Field(default="organic", max_length=80)
    term: str = Field(default="", max_length=120)
    content: str = Field(default="", max_length=120)
    landing_page_slug: str = Field(default="", max_length=240)
    form_template_name: str = Field(default="", max_length=180)


class CmsAttributionEventRequest(BaseModel):
    attribution_link_id: int
    event_type: str = Field(pattern="^(visit|lead|mql|sql|opportunity|customer)$")
    visitor_id: str = Field(default="", max_length=120)
    contact_email: str = Field(default="", max_length=255)
    value: float = Field(default=0.0, ge=0.0)
    sync_to_crm: bool = True
    contact_first_name: str = Field(default="", max_length=120)
    contact_last_name: str = Field(default="", max_length=120)
    company: str = Field(default="", max_length=180)
    create_deal: bool = False
    deal_title: str = Field(default="CMS Attributed Opportunity", max_length=180)
    deal_stage: str = Field(default="qualified", max_length=40)
    deal_value: float = Field(default=0.0, ge=0.0)


class CmsAttributionAutomationRuleRequest(BaseModel):
    campaign: str = Field(default="", max_length=120, description="Empty means all campaigns")
    trigger_event_type: str = Field(pattern="^(visit|lead|mql|sql|opportunity|customer)$")
    min_value: float = Field(default=0.0, ge=0.0)
    auto_enroll_sequence_id: int | None = None
    create_deal: bool = False
    deal_title: str = Field(default="CMS Attribution Rule Opportunity", max_length=180)
    deal_stage: str = Field(default="qualified", max_length=40)
    transition_deal_stage_to: str | None = Field(default=None, max_length=40)
    create_followup_task: bool = False
    task_title: str = Field(default="CMS Attribution Follow-up", max_length=180)
    task_priority: str = Field(default="medium", max_length=20)
    task_assigned_to: str = Field(default="", max_length=120)
    task_due_in_days: int = Field(default=2, ge=0, le=60)
    enabled: bool = True
