"""Social/Inbox request contracts."""

from __future__ import annotations
from pydantic import BaseModel
from pydantic import Field


class InboxMessageIngestRequest(BaseModel):
    """ADDED: Ingest an inbound message into the Smart Inbox."""

    network: str = Field(min_length=2, max_length=40)
    source_type: str = Field(
        default="dm", min_length=2, max_length=40, description="dm/comment/mention/review/story_reply"
    )
    author_handle: str = Field(min_length=1, max_length=120)
    author_display_name: str | None = Field(default=None, max_length=160)
    author_follower_count: int = Field(default=0, ge=0, le=50000000)
    text: str = Field(min_length=1, max_length=5000)
    external_message_id: str | None = Field(
        default=None, max_length=200, description="Original platform message ID for dedup."
    )
    parent_message_id: str | None = Field(
        default=None, max_length=200, description="Thread parent ID for threaded view."
    )
    crm_contact_id: str | None = Field(default=None, max_length=200)


class MessageUpdateRequest(BaseModel):
    """ADDED: Update message assignment, status, or tags."""

    assigned_to: str | None = Field(
        default=None, max_length=160, description="Team member handle to assign message to."
    )
    status: str | None = Field(
        default=None, max_length=40, description="pending/in_progress/complete/flagged/requires_approval"
    )
    tags: list[str] | None = Field(
        default=None, max_length=20, description="Custom labels e.g. Product Feedback, Shipping Issue"
    )
    due_at: str | None = Field(default=None, max_length=40, description="ISO datetime for assignment due date.")


class InternalNoteRequest(BaseModel):
    """ADDED: Add an internal team note to a message (never sent to the customer)."""

    author: str = Field(min_length=1, max_length=160)
    note: str = Field(min_length=1, max_length=2000)


class LockRequest(BaseModel):
    """ADDED: Acquire collision-prevention lock before composing a reply."""

    locked_by: str = Field(min_length=1, max_length=160, description="Team member handle acquiring the lock.")


class SavedReplyRequest(BaseModel):
    """ADDED: Create a pre-approved reply template for the saved replies library."""

    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=4000)
    tags: list[str] = Field(default_factory=list, max_length=10)
    networks: list[str] = Field(default_factory=list, max_length=10, description="Applicable networks; empty = all.")


class SavedReplyUpdateRequest(BaseModel):
    """ADDED: Update a saved reply."""

    title: str | None = Field(default=None, max_length=120)
    body: str | None = Field(default=None, max_length=4000)
    tags: list[str] | None = Field(default=None, max_length=10)
    networks: list[str] | None = Field(default=None, max_length=10)


class AutoResponseRequest(BaseModel):
    """Execute an auto-response using a saved reply or suggested reply."""

    saved_reply_id: int | None = Field(default=None, ge=1)
    suggestion_index: int | None = Field(default=None, ge=0, le=2)
    responder: str = Field(min_length=1, max_length=160)
    require_approval: bool = Field(default=False)


class ResponseApprovalRequest(BaseModel):
    """Approve and deliver a previously staged auto-response."""

    approver: str = Field(min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=500)


class ResponseRejectionRequest(BaseModel):
    """Reject a previously staged auto-response."""

    reviewer: str = Field(min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=500)


class ResponseReplayRequest(BaseModel):
    """Retry a failed outbound auto-response delivery from the inbox DLQ."""

    operator: str = Field(min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=500)


class DeliveryFailureResolveRequest(BaseModel):
    """Resolve a failed outbound inbox delivery for manual follow-up."""

    operator: str = Field(min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=500)


class DeliveryFailureBulkResolveRequest(BaseModel):
    """Resolve multiple failed outbound deliveries for manual follow-up."""

    failure_ids: list[int] = Field(min_length=1, max_length=100)
    operator: str = Field(min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=500)


class DeliveryFailureBulkReplayRequest(BaseModel):
    """Replay multiple failed outbound deliveries in one operation."""

    failure_ids: list[int] = Field(min_length=1, max_length=50)
    operator: str = Field(min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=500)


class DeliveryFailureReplayPendingRequest(BaseModel):
    """Replay a limited batch of pending delivery failures."""

    operator: str = Field(min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=500)
    limit: int = Field(default=25, ge=1, le=50)
    network: str | None = Field(default=None, max_length=40)
