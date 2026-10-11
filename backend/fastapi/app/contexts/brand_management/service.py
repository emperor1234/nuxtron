"""Framework-independent brand operations and tenant invariants."""

from __future__ import annotations

from typing import Any

from .ports import BrandRepository
from .public import Brand, BrandAsset, BrandStatus, utc_now_naive

BRAND_UPDATE_FIELDS = frozenset(
    {
        "name",
        "description",
        "website",
        "status",
        "primary_audience",
        "primary_channels",
    }
)


class BrandManagementService:
    """Operate on brands without allowing cross-tenant ID access."""

    def __init__(self, repository: BrandRepository) -> None:
        self._repository = repository

    def create_brand(
        self,
        tenant_id: str,
        name: str,
        description: str = "",
        website: str | None = None,
        owner_id: str | None = None,
    ) -> Brand:
        self._require_tenant(tenant_id)
        if not name or not name.strip():
            raise ValueError("name is required")
        return self._repository.add(
            Brand(
                tenant_id=tenant_id,
                name=name,
                description=description,
                website=website,
                owners=[owner_id] if owner_id else [],
            )
        )

    def get_brand(self, tenant_id: str, brand_id: str) -> Brand | None:
        self._require_tenant(tenant_id)
        return self._repository.get_for_tenant(tenant_id, brand_id)

    def list_brands(
        self,
        tenant_id: str,
        status: BrandStatus | None = None,
    ) -> list[Brand]:
        self._require_tenant(tenant_id)
        return self._repository.list_for_tenant(tenant_id, status)

    def update_brand(
        self,
        tenant_id: str,
        brand_id: str,
        updates: dict[str, Any],
    ) -> Brand | None:
        self._require_tenant(tenant_id)

        def apply_updates(brand: Brand) -> None:
            for field, value in updates.items():
                if field in BRAND_UPDATE_FIELDS:
                    setattr(brand, field, value)
            brand.updated_at = utc_now_naive()

        return self._repository.mutate_for_tenant(tenant_id, brand_id, apply_updates)

    def update_guidelines(
        self,
        tenant_id: str,
        brand_id: str,
        updates: dict[str, Any],
    ) -> Brand | None:
        self._require_tenant(tenant_id)

        def apply_updates(brand: Brand) -> None:
            for field, value in updates.items():
                if hasattr(brand.guidelines, field):
                    setattr(brand.guidelines, field, value)
            brand.guidelines.updated_at = utc_now_naive()
            brand.updated_at = utc_now_naive()

        return self._repository.mutate_for_tenant(tenant_id, brand_id, apply_updates)

    def add_asset(
        self,
        tenant_id: str,
        brand_id: str,
        asset: BrandAsset,
    ) -> BrandAsset | None:
        self._require_tenant(tenant_id)

        def append_asset(brand: Brand) -> None:
            brand.assets.append(asset)
            brand.updated_at = utc_now_naive()

        brand = self._repository.mutate_for_tenant(tenant_id, brand_id, append_asset)
        return asset if brand else None

    def list_assets(
        self,
        tenant_id: str,
        brand_id: str,
        asset_type: str | None = None,
        category: str | None = None,
    ) -> list[BrandAsset] | None:
        brand = self.get_brand(tenant_id, brand_id)
        if brand is None:
            return None
        assets = brand.assets
        if asset_type:
            assets = [asset for asset in assets if asset.asset_type == asset_type]
        if category:
            assets = [asset for asset in assets if asset.category == category]
        return sorted(assets, key=lambda asset: asset.uploaded_at, reverse=True)

    def remove_asset(
        self,
        tenant_id: str,
        brand_id: str,
        asset_id: str,
    ) -> Brand | None:
        self._require_tenant(tenant_id)

        def remove_matching_asset(brand: Brand) -> None:
            brand.assets[:] = [asset for asset in brand.assets if asset.id != asset_id]
            brand.updated_at = utc_now_naive()

        return self._repository.mutate_for_tenant(tenant_id, brand_id, remove_matching_asset)

    def add_contributor(
        self,
        tenant_id: str,
        brand_id: str,
        user_id: str,
    ) -> Brand | None:
        self._require_tenant(tenant_id)

        def append_contributor(brand: Brand) -> None:
            if user_id not in brand.contributors and user_id not in brand.owners:
                brand.contributors.append(user_id)

        return self._repository.mutate_for_tenant(tenant_id, brand_id, append_contributor)

    def get_brand_analytics(
        self,
        tenant_id: str,
        brand_id: str,
    ) -> dict[str, Any] | None:
        brand = self.get_brand(tenant_id, brand_id)
        if brand is None:
            return None
        return _analytics_payload(brand)

    @staticmethod
    def _require_tenant(tenant_id: str) -> None:
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id is required")


def _analytics_payload(brand: Brand) -> dict[str, Any]:
    return {
        "brand_id": brand.id,
        "name": brand.name,
        "status": brand.status.value,
        "total_assets": len(brand.assets),
        "most_used_assets": sorted(
            brand.assets,
            key=lambda asset: asset.usage_count,
            reverse=True,
        )[:5],
        "monthly_reach": brand.monthly_reach,
        "monthly_engagement": brand.monthly_engagement,
        "team_size": len(brand.owners) + len(brand.contributors),
        "created_at": brand.created_at,
        "updated_at": brand.updated_at,
    }
