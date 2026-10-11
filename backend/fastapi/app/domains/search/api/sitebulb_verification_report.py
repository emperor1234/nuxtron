"""Search HTTP operations beginning with sitebulb verification report."""

from ..constants import AuthDep
from ..operations.sitebulb_remediation_bundle_export import operation_sitebulb_verification_report
from ..runtime import SearchRuntime
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/sitebulb/verification-report")
    def sitebulb_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_sitebulb_verification_report(runtime, auth)
