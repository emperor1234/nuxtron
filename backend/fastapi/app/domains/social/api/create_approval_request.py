"""Social HTTP adapters: create approval request."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import ApprovalCreateRequest
from ....domains.social.schemas import ApprovalRejectRequest
from ....domains.social.schemas import IntegrationWebhookCreateRequest
from ....domains.social.schemas import IntegrationWebhookTestRequest
from ....domains.social.schemas import IntegrationWebhookUpdateRequest
from ..constants import AuthDep
from ..operations.create_integration_webhook import operation_create_integration_webhook
from ..operations.create_integration_webhook import operation_test_integration_webhook
from ..operations.create_integration_webhook import operation_update_integration_webhook
from ..operations.list_hashtag_groups import operation_approve_request
from ..operations.list_hashtag_groups import operation_create_approval_request
from ..operations.list_hashtag_groups import operation_list_integration_webhooks
from ..operations.list_hashtag_groups import operation_list_pending_approvals
from ..operations.list_hashtag_groups import operation_reject_request
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.post("/social/approvals")
    def create_approval_request(payload: ApprovalCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_approval_request(st, router, payload, auth)

    @router.get("/social/approvals/pending")
    def list_pending_approvals(auth: AuthDep) -> dict[str, Any]:
        return operation_list_pending_approvals(st, router, auth)

    @router.post(
        "/social/approvals/{request_id}/approve", responses={404: {"description": "Approval request not found"}}
    )
    def approve_request(request_id: str, auth: AuthDep, approver: str = "approver") -> dict[str, Any]:
        return operation_approve_request(st, router, request_id, auth, approver)

    @router.post(
        "/social/approvals/{request_id}/reject", responses={404: {"description": "Approval request not found"}}
    )
    def reject_request(request_id: str, payload: ApprovalRejectRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_reject_request(st, router, request_id, payload, auth)

    @router.get("/social/integrations/webhooks")
    def list_integration_webhooks(auth: AuthDep) -> dict[str, Any]:
        return operation_list_integration_webhooks(st, router, auth)

    @router.post("/social/integrations/webhooks")
    def create_integration_webhook(payload: IntegrationWebhookCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_integration_webhook(st, router, payload, auth)

    @router.patch(
        "/social/integrations/webhooks/{webhook_id}", responses={404: {"description": "Webhook integration not found"}}
    )
    def update_integration_webhook(
        webhook_id: int, payload: IntegrationWebhookUpdateRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return operation_update_integration_webhook(st, router, webhook_id, payload, auth)

    @router.post(
        "/social/integrations/webhooks/{webhook_id}/test",
        responses={404: {"description": "Webhook integration not found"}},
    )
    def test_integration_webhook(
        webhook_id: int, payload: IntegrationWebhookTestRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return operation_test_integration_webhook(st, router, webhook_id, payload, auth)
