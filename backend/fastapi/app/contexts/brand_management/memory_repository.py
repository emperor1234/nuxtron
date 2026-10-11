"""Named adapter for the canonical process-local brand store."""

from __future__ import annotations

from collections.abc import MutableMapping
from contextlib import AbstractContextManager
from typing import Any, cast

from ... import memory_stores
from .ports import BrandMutation
from .public import Brand, BrandAsset, BrandStatus, utc_now_naive
from .service import BRAND_UPDATE_FIELDS, BrandManagementService, _analytics_payload


class MemoryBrandRepository:
    """Synchronize atomic access without replacing the canonical store object."""

    def __init__(
        self,
        store: MutableMapping[str, Brand],
        lock: AbstractContextManager[object],
    ) -> None:
        self.store = store
        self._lock = lock

    def add(self, brand: Brand) -> Brand:
        with self._lock:
            self.store[brand.id] = brand
            return brand

    def get_for_tenant(self, tenant_id: str, brand_id: str) -> Brand | None:
        with self._lock:
            brand = self.store.get(brand_id)
            return brand if brand is not None and brand.tenant_id == tenant_id else None

    def list_for_tenant(
        self,
        tenant_id: str,
        status: BrandStatus | None = None,
    ) -> list[Brand]:
        with self._lock:
            brands = [
                brand
                for brand in self.store.values()
                if brand.tenant_id == tenant_id and (status is None or brand.status == status)
            ]
            return sorted(brands, key=lambda brand: brand.created_at, reverse=True)

    def mutate_for_tenant(
        self,
        tenant_id: str,
        brand_id: str,
        mutation: BrandMutation,
    ) -> Brand | None:
        with self._lock:
            brand = self.store.get(brand_id)
            if brand is None or brand.tenant_id != tenant_id:
                return None
            mutation(brand)
            return brand

    def get_any(self, brand_id: str) -> Brand | None:
        """Support the historical manager only; request paths never call this."""
        with self._lock:
            return self.store.get(brand_id)

    def mutate_any(self, brand_id: str, mutation: BrandMutation) -> Brand | None:
        """Support the historical manager only; request paths never call this."""
        with self._lock:
            brand = self.store.get(brand_id)
            if brand is None:
                return None
            mutation(brand)
            return brand

    def clear_for_tests(self) -> None:
        with self._lock:
            self.store.clear()


class LegacyBrandHubManager:
    """Compatibility facade; new request paths use tenant-scoped service calls."""

    def __init__(
        self,
        service: BrandManagementService | None = None,
        repository: MemoryBrandRepository | None = None,
    ) -> None:
        selected_repository = repository or brand_repository
        self._repository = selected_repository
        self._service = service or BrandManagementService(selected_repository)

    @property
    def brands(self) -> MutableMapping[str, Brand]:
        return self._repository.store

    def create_brand(
        self,
        tenant_id: str,
        name: str,
        description: str = "",
        website: str | None = None,
        owner_id: str | None = None,
    ) -> Brand:
        return self._service.create_brand(tenant_id, name, description, website, owner_id)

    def get_brand(self, brand_id: str) -> Brand | None:
        return self._repository.get_any(brand_id)

    def list_brands(
        self,
        tenant_id: str,
        status: BrandStatus | None = None,
    ) -> list[Brand]:
        return self._service.list_brands(tenant_id, status)

    def update_brand(self, brand_id: str, **updates: Any) -> Brand | None:
        def apply_updates(brand: Brand) -> None:
            for field, value in updates.items():
                if field in BRAND_UPDATE_FIELDS:
                    setattr(brand, field, value)
            brand.updated_at = utc_now_naive()

        return self._repository.mutate_any(brand_id, apply_updates)

    def update_guidelines(self, brand_id: str, **updates: Any) -> Brand | None:
        def apply_updates(brand: Brand) -> None:
            for field, value in updates.items():
                if hasattr(brand.guidelines, field):
                    setattr(brand.guidelines, field, value)
            brand.guidelines.updated_at = utc_now_naive()
            brand.updated_at = utc_now_naive()

        return self._repository.mutate_any(brand_id, apply_updates)

    def add_asset(self, brand_id: str, asset: BrandAsset) -> Brand | None:
        def append_asset(brand: Brand) -> None:
            brand.assets.append(asset)
            brand.updated_at = utc_now_naive()

        return self._repository.mutate_any(brand_id, append_asset)

    def remove_asset(self, brand_id: str, asset_id: str) -> Brand | None:
        def remove_matching_asset(brand: Brand) -> None:
            brand.assets[:] = [asset for asset in brand.assets if asset.id != asset_id]
            brand.updated_at = utc_now_naive()

        return self._repository.mutate_any(brand_id, remove_matching_asset)

    def get_assets(
        self,
        brand_id: str,
        asset_type: str | None = None,
        category: str | None = None,
    ) -> list[BrandAsset]:
        brand = self._repository.get_any(brand_id)
        if brand is None:
            return []
        assets = brand.assets
        if asset_type:
            assets = [asset for asset in assets if asset.asset_type == asset_type]
        if category:
            assets = [asset for asset in assets if asset.category == category]
        return sorted(assets, key=lambda asset: asset.uploaded_at, reverse=True)

    def update_asset_usage(self, brand_id: str, asset_id: str) -> BrandAsset | None:
        updated_asset: BrandAsset | None = None

        def record_usage(brand: Brand) -> None:
            nonlocal updated_asset
            updated_asset = next((asset for asset in brand.assets if asset.id == asset_id), None)
            if updated_asset is not None:
                updated_asset.usage_count += 1
                updated_asset.last_used_at = utc_now_naive()
                brand.updated_at = utc_now_naive()

        self._repository.mutate_any(brand_id, record_usage)
        return updated_asset

    def add_contributor(self, brand_id: str, user_id: str) -> Brand | None:
        def append_contributor(brand: Brand) -> None:
            if user_id not in brand.contributors and user_id not in brand.owners:
                brand.contributors.append(user_id)

        return self._repository.mutate_any(brand_id, append_contributor)

    def remove_contributor(self, brand_id: str, user_id: str) -> Brand | None:
        def remove_matching_contributor(brand: Brand) -> None:
            brand.contributors[:] = [
                contributor for contributor in brand.contributors if contributor != user_id
            ]

        return self._repository.mutate_any(brand_id, remove_matching_contributor)

    def get_brand_analytics(self, brand_id: str) -> dict[str, Any]:
        brand = self._repository.get_any(brand_id)
        return _analytics_payload(brand) if brand else {}


brand_repository = MemoryBrandRepository(
    cast(MutableMapping[str, Brand], memory_stores.brand_hub_brands),
    memory_stores.brand_hub_brands_lock,
)
