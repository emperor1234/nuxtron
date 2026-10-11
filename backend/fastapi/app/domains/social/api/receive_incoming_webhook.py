"""Social HTTP adapters: receive incoming webhook."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import BrowserExtensionCaptureRequest
from ....domains.social.schemas import BrowserExtensionQueueRequest
from ....domains.social.schemas import CanvaImportRequest
from ..constants import AuthDep
from ..operations.create_integration_webhook import operation_create_browser_capture
from ..operations.create_integration_webhook import operation_get_browser_extension_manifest
from ..operations.create_integration_webhook import operation_get_mobile_config
from ..operations.create_integration_webhook import operation_import_from_canva
from ..operations.create_integration_webhook import operation_list_browser_captures
from ..operations.create_integration_webhook import operation_list_canva_imports
from ..operations.create_integration_webhook import operation_queue_browser_capture
from ..operations.create_integration_webhook import operation_receive_incoming_webhook
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.post("/social/integrations/webhooks/incoming/{provider}")
    def receive_incoming_webhook(provider: str, payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_receive_incoming_webhook(st, router, provider, payload, auth)

    @router.post("/social/integrations/canva/import")
    def import_from_canva(payload: CanvaImportRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_import_from_canva(st, router, payload, auth)

    @router.get("/social/integrations/canva/imports")
    def list_canva_imports(auth: AuthDep) -> dict[str, Any]:
        return operation_list_canva_imports(st, router, auth)

    @router.get("/social/extensions/browser/manifest")
    def get_browser_extension_manifest(auth: AuthDep) -> dict[str, Any]:
        return operation_get_browser_extension_manifest(st, router, auth)

    @router.post("/social/extensions/browser/captures")
    def create_browser_capture(payload: BrowserExtensionCaptureRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_browser_capture(st, router, payload, auth)

    @router.get("/social/extensions/browser/captures")
    def list_browser_captures(auth: AuthDep, status: str | None = None, limit: int = 100) -> dict[str, Any]:
        return operation_list_browser_captures(st, router, auth, status, limit)

    @router.post(
        "/social/extensions/browser/captures/{capture_id}/queue",
        responses={404: {"description": "Browser capture not found"}},
    )
    def queue_browser_capture(capture_id: int, payload: BrowserExtensionQueueRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_queue_browser_capture(st, router, capture_id, payload, auth)

    @router.get("/social/mobile/config")
    def get_mobile_config(auth: AuthDep) -> dict[str, Any]:
        return operation_get_mobile_config(st, router, auth)
