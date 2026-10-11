"""Search HTTP operations beginning with hubspot service list tickets."""

from ..constants import AuthDep
from ..operations.hubspot_route_coverage_chart import operation_hubspot_commerce_list_products
from ..operations.hubspot_route_coverage_chart import operation_hubspot_service_list_knowledge_articles
from ..operations.hubspot_route_coverage_chart import operation_hubspot_service_list_surveys
from ..operations.hubspot_route_coverage_chart import operation_hubspot_service_list_tickets
from ..operations.hubspot_wiring_required_keys import operation_hubspot_commerce_create_document
from ..operations.hubspot_wiring_required_keys import operation_hubspot_commerce_create_product
from ..operations.hubspot_wiring_required_keys import operation_hubspot_service_create_knowledge_article
from ..operations.hubspot_wiring_required_keys import operation_hubspot_service_create_survey
from ..runtime import SearchRuntime
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/hubspot/service/tickets")
    def hubspot_service_list_tickets(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_service_list_tickets(runtime, auth)

    @router.post("/hubspot/service/knowledge-base/articles")
    def hubspot_service_create_knowledge_article(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_service_create_knowledge_article(runtime, payload, auth)

    @router.get("/hubspot/service/knowledge-base/articles")
    def hubspot_service_list_knowledge_articles(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_service_list_knowledge_articles(runtime, auth)

    @router.post("/hubspot/service/surveys")
    def hubspot_service_create_survey(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_service_create_survey(runtime, payload, auth)

    @router.get("/hubspot/service/surveys")
    def hubspot_service_list_surveys(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_service_list_surveys(runtime, auth)

    @router.post("/hubspot/commerce/products")
    def hubspot_commerce_create_product(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_commerce_create_product(runtime, payload, auth)

    @router.get("/hubspot/commerce/products")
    def hubspot_commerce_list_products(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_commerce_list_products(runtime, auth)

    @router.post("/hubspot/commerce/documents")
    def hubspot_commerce_create_document(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_commerce_create_document(runtime, payload, auth)
