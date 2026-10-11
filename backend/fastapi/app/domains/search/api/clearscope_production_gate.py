"""Search HTTP operations beginning with clearscope production gate."""

from ..constants import AuthDep
from ..operations.clearscope_client_config import operation_clearscope_production_gate
from ..operations.clearscope_client_config import operation_clearscope_verification_report
from ..operations.hubspot_wiring_required_keys import operation_hubspot_service_create_ticket
from ..operations.seoai_list_runs import operation_seoai_shopify_magic_completion_chart
from ..operations.seoai_list_runs import operation_seoai_shopify_magic_email_campaign
from ..operations.seoai_list_runs import operation_seoai_shopify_magic_image_workflow
from ..operations.seoai_list_runs import operation_seoai_shopify_magic_inbox_reply
from ..operations.seoai_list_runs import operation_seoai_shopify_magic_sidekick
from ..runtime import SearchRuntime
from ..schemas import ShopifyMagicEmailRequest
from ..schemas import ShopifyMagicImageRequest
from ..schemas import ShopifyMagicInboxRequest
from ..schemas import ShopifyMagicSidekickRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/clearscope/production-gate")
    def clearscope_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_clearscope_production_gate(runtime, auth)

    @router.get("/clearscope/verification-report")
    def clearscope_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_clearscope_verification_report(runtime, auth)

    @router.post("/seoai/shopify-magic/sidekick")
    def seoai_shopify_magic_sidekick(payload: ShopifyMagicSidekickRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_shopify_magic_sidekick(runtime, payload, auth)

    @router.post("/seoai/shopify-magic/image-workflow")
    def seoai_shopify_magic_image_workflow(payload: ShopifyMagicImageRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_shopify_magic_image_workflow(runtime, payload, auth)

    @router.post("/seoai/shopify-magic/email-campaign")
    def seoai_shopify_magic_email_campaign(payload: ShopifyMagicEmailRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_shopify_magic_email_campaign(runtime, payload, auth)

    @router.post("/seoai/shopify-magic/inbox-reply")
    def seoai_shopify_magic_inbox_reply(payload: ShopifyMagicInboxRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_shopify_magic_inbox_reply(runtime, payload, auth)

    @router.get("/seoai/shopify-magic/completion-chart")
    def seoai_shopify_magic_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_shopify_magic_completion_chart(runtime, auth)

    @router.post("/hubspot/service/tickets")
    def hubspot_service_create_ticket(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_service_create_ticket(runtime, payload, auth)
