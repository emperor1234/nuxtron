"""Compatibility facade for brand-management domain imports."""

from ..contexts.brand_management.memory_repository import (
    LegacyBrandHubManager as BrandHubManager,
)
from ..contexts.brand_management.public import (
    Brand,
    BrandAsset,
    BrandGuidelines,
    BrandStatus,
)
from ..contexts.brand_management.wiring import brand_hub_manager

__all__ = [
    "Brand",
    "BrandAsset",
    "BrandGuidelines",
    "BrandHubManager",
    "BrandStatus",
    "brand_hub_manager",
]
