"""Performance remediation must never claim an unapplied change succeeded."""

import pytest
from backend.fastapi.app.domains.seo.services.seo_performance_service import (
    PERFORMANCE_UNAVAILABLE_DETAIL,
    raise_performance_unavailable,
)
from fastapi import HTTPException

pytestmark = pytest.mark.no_legacy


def test_performance_auto_fix_boundary_returns_typed_not_implemented() -> None:
    with pytest.raises(HTTPException) as error:
        raise_performance_unavailable()

    assert error.value.status_code == 501
    assert error.value.detail == PERFORMANCE_UNAVAILABLE_DETAIL
    assert "auto-fix" in error.value.detail["message"]
