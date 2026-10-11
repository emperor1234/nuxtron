"""Marketing/Growth HTTP adapters beginning with list ab tests."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.generate_advanced_report import execute_create_child_brand
from ..operations.generate_advanced_report import execute_export_analytics_csv
from ..operations.generate_advanced_report import execute_keyword_top_insights
from ..operations.generate_advanced_report import execute_list_ab_tests
from ..operations.generate_advanced_report import execute_list_brand_hierarchy
from ..operations.generate_advanced_report import execute_track_keyword
from ..runtime import ContextRuntime
from ..schemas import BrandHierarchyRequest
from ..schemas import KeywordTrackRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/experiments/ab-tests")
    def list_ab_tests(auth: AuthDep) -> dict[str, Any]:
        return execute_list_ab_tests(runtime, auth)

    @router.get("/analytics/keywords/top")
    def keyword_top_insights(auth: AuthDep) -> dict[str, Any]:
        return execute_keyword_top_insights(runtime, auth)

    @router.post("/analytics/keywords/track")
    def track_keyword(payload: KeywordTrackRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_track_keyword(runtime, payload, auth)

    @router.get("/brand-hierarchy")
    def list_brand_hierarchy(auth: AuthDep) -> dict[str, Any]:
        return execute_list_brand_hierarchy(runtime, auth)

    @router.post("/brand-hierarchy")
    def create_child_brand(payload: BrandHierarchyRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_child_brand(runtime, payload, auth)

    @router.get("/analytics/export")
    def export_analytics_csv(auth: AuthDep) -> dict[str, Any]:
        return execute_export_analytics_csv(runtime, auth)
