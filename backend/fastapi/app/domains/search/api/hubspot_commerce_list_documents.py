"""Search HTTP operations beginning with hubspot commerce list documents."""

from ..constants import AuthDep
from ..operations.hubspot_route_coverage_chart import operation_hubspot_commerce_list_documents
from ..operations.hubspot_route_coverage_chart import operation_hubspot_crm_list_companies
from ..operations.hubspot_route_coverage_chart import operation_hubspot_crm_list_contacts
from ..operations.hubspot_route_coverage_chart import operation_hubspot_crm_list_deals
from ..operations.hubspot_wiring_required_keys import operation_hubspot_content_create_landing_page
from ..operations.hubspot_wiring_required_keys import operation_hubspot_crm_create_company
from ..operations.hubspot_wiring_required_keys import operation_hubspot_crm_create_contact
from ..operations.hubspot_wiring_required_keys import operation_hubspot_crm_create_deal
from ..runtime import SearchRuntime
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/hubspot/commerce/documents")
    def hubspot_commerce_list_documents(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_commerce_list_documents(runtime, auth)

    @router.post("/hubspot/crm/contacts")
    def hubspot_crm_create_contact(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_crm_create_contact(runtime, payload, auth)

    @router.get("/hubspot/crm/contacts")
    def hubspot_crm_list_contacts(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_crm_list_contacts(runtime, auth)

    @router.post("/hubspot/crm/companies")
    def hubspot_crm_create_company(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_crm_create_company(runtime, payload, auth)

    @router.get("/hubspot/crm/companies")
    def hubspot_crm_list_companies(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_crm_list_companies(runtime, auth)

    @router.post("/hubspot/crm/deals")
    def hubspot_crm_create_deal(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_crm_create_deal(runtime, payload, auth)

    @router.get("/hubspot/crm/deals")
    def hubspot_crm_list_deals(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_crm_list_deals(runtime, auth)

    @router.post("/hubspot/content/landing-pages")
    def hubspot_content_create_landing_page(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_content_create_landing_page(runtime, payload, auth)
