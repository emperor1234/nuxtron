"""Storage boundary used by the framework-independent brand service."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from .public import Brand, BrandStatus

BrandMutation = Callable[[Brand], None]


class BrandRepository(Protocol):
    """Atomic, tenant-scoped access to brand aggregates."""

    def add(self, brand: Brand) -> Brand: ...

    def get_for_tenant(self, tenant_id: str, brand_id: str) -> Brand | None: ...

    def list_for_tenant(
        self,
        tenant_id: str,
        status: BrandStatus | None = None,
    ) -> list[Brand]: ...

    def mutate_for_tenant(
        self,
        tenant_id: str,
        brand_id: str,
        mutation: BrandMutation,
    ) -> Brand | None: ...


class LegacyBrandRepository(BrandRepository, Protocol):
    """Unscoped access retained only for the pre-context manager facade."""

    @property
    def store(self) -> dict[str, Brand]: ...

    def get_any(self, brand_id: str) -> Brand | None: ...

    def mutate_any(self, brand_id: str, mutation: BrandMutation) -> Brand | None: ...
