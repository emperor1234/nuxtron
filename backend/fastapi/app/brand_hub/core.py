"""
Brand Hub - Multi-brand Management System

Manages:
- Brand creation and configuration
- Brand guidelines and rules
- Asset library per brand
- Cross-brand analytics and reporting
- Brand permission/access control
"""

import logging
import uuid as uuid_lib
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class BrandStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"

class BrandGuidelines(BaseModel):
    """Brand guidelines and rules"""
    id: str = Field(default_factory=lambda: str(uuid_lib.uuid4()))
    
    # Visual guidelines
    primary_color: str = "#000000"
    secondary_color: str = "#FFFFFF"
    logo_url: str | None = None
    brand_font: str = "Arial"
    
    # Voice and tone
    tone: str = "professional"  # professional, friendly, casual, etc.
    voice_description: str = ""
    
    # Content rules
    content_policy: str = ""  # Guidelines for generated content
    restricted_topics: list[str] = Field(default_factory=list)
    
    # Keywords to always include
    required_keywords: list[str] = Field(default_factory=list)
    
    # Keywords to avoid
    restricted_keywords: list[str] = Field(default_factory=list)
    
    # Compliance
    compliance_rules: list[str] = Field(default_factory=list)
    
    # Version tracking
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class BrandAsset(BaseModel):
    """Asset in brand library"""
    id: str = Field(default_factory=lambda: str(uuid_lib.uuid4()))
    
    # Metadata
    name: str
    asset_type: str  # image, video, template, copy_template, etc.
    url: str
    
    # Classification
    category: str  # header, footer, product, lifestyle, etc.
    tags: list[str] = Field(default_factory=list)
    
    # Usage rights
    rights_holder: str  # Who holds rights (internal team, UGC, etc.)
    usage_rights: str  # Full, limited, one-time, etc.
    expiration_date: datetime | None = None
    
    # Performance
    usage_count: int = 0
    engagement_rate: float | None = None
    
    # Timestamps
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: datetime | None = None

class Brand(BaseModel):
    """Brand configuration and metadata"""
    id: str = Field(default_factory=lambda: str(uuid_lib.uuid4()))
    tenant_id: str
    
    # Identity
    name: str
    description: str = ""
    website: str | None = None
    
    # Configuration
    status: BrandStatus = BrandStatus.ACTIVE
    guidelines: BrandGuidelines = Field(default_factory=BrandGuidelines)
    
    # Assets
    assets: list[BrandAsset] = Field(default_factory=list)
    
    # Distribution
    primary_audience: str = ""
    primary_channels: list[str] = Field(default_factory=list)  # twitter, linkedin, blog, email, etc.
    
    # Analytics
    monthly_reach: int = 0
    monthly_engagement: float = 0.0
    
    # Team
    owners: list[str] = Field(default_factory=list)  # User IDs
    contributors: list[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class BrandHubManager:
    """Manages all brands for a tenant"""
    
    def __init__(self):
        self.brands: dict[str, Brand] = {}
    
    def create_brand(
        self,
        tenant_id: str,
        name: str,
        description: str = "",
        website: str | None = None,
        owner_id: str | None = None,
    ) -> Brand:
        """Create new brand"""
        
        brand = Brand(
            tenant_id=tenant_id,
            name=name,
            description=description,
            website=website,
            owners=[owner_id] if owner_id else [],
        )
        
        self.brands[brand.id] = brand
        logger.info(f"Created brand: {brand.id} - {name}")
        
        return brand
    
    def get_brand(self, brand_id: str) -> Brand | None:
        """Get brand by ID"""
        return self.brands.get(brand_id)
    
    def list_brands(self, tenant_id: str, status: BrandStatus | None = None) -> list[Brand]:
        """List all brands for tenant"""
        
        brands = [
            b for b in self.brands.values()
            if b.tenant_id == tenant_id
        ]
        
        if status:
            brands = [b for b in brands if b.status == status]
        
        return sorted(brands, key=lambda b: b.created_at, reverse=True)
    
    def update_brand(self, brand_id: str, **updates) -> Brand | None:
        """Update brand"""
        
        brand = self.brands.get(brand_id)
        if not brand:
            return None
        
        # Update allowed fields
        allowed_fields = {"name", "description", "website", "status", "primary_audience", "primary_channels"}
        
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(brand, field, value)
        
        brand.updated_at = datetime.utcnow()
        logger.info(f"Updated brand: {brand_id}")
        
        return brand
    
    def update_guidelines(self, brand_id: str, **updates) -> Brand | None:
        """Update brand guidelines"""
        
        brand = self.brands.get(brand_id)
        if not brand:
            return None
        
        # Update guidelines
        for field, value in updates.items():
            if hasattr(brand.guidelines, field):
                setattr(brand.guidelines, field, value)
        
        brand.guidelines.updated_at = datetime.utcnow()
        brand.updated_at = datetime.utcnow()
        logger.info(f"Updated guidelines for brand: {brand_id}")
        
        return brand
    
    def add_asset(
        self,
        brand_id: str,
        asset: BrandAsset,
    ) -> Brand | None:
        """Add asset to brand library"""
        
        brand = self.brands.get(brand_id)
        if not brand:
            return None
        
        brand.assets.append(asset)
        brand.updated_at = datetime.utcnow()
        logger.info(f"Added asset to brand {brand_id}: {asset.id}")
        
        return brand
    
    def remove_asset(self, brand_id: str, asset_id: str) -> Brand | None:
        """Remove asset from brand library"""
        
        brand = self.brands.get(brand_id)
        if not brand:
            return None
        
        brand.assets = [a for a in brand.assets if a.id != asset_id]
        brand.updated_at = datetime.utcnow()
        logger.info(f"Removed asset from brand {brand_id}: {asset_id}")
        
        return brand
    
    def get_assets(
        self,
        brand_id: str,
        asset_type: str | None = None,
        category: str | None = None,
    ) -> list[BrandAsset]:
        """Get brand assets with optional filters"""
        
        brand = self.brands.get(brand_id)
        if not brand:
            return []
        
        assets = brand.assets
        
        if asset_type:
            assets = [a for a in assets if a.asset_type == asset_type]
        
        if category:
            assets = [a for a in assets if a.category == category]
        
        return sorted(assets, key=lambda a: a.uploaded_at, reverse=True)
    
    def update_asset_usage(self, brand_id: str, asset_id: str) -> BrandAsset | None:
        """Update asset usage tracking"""
        
        brand = self.brands.get(brand_id)
        if not brand:
            return None
        
        asset = next((a for a in brand.assets if a.id == asset_id), None)
        if not asset:
            return None
        
        asset.usage_count += 1
        asset.last_used_at = datetime.utcnow()
        brand.updated_at = datetime.utcnow()
        
        return asset
    
    def add_contributor(self, brand_id: str, user_id: str) -> Brand | None:
        """Add contributor to brand"""
        
        brand = self.brands.get(brand_id)
        if not brand:
            return None
        
        if user_id not in brand.contributors and user_id not in brand.owners:
            brand.contributors.append(user_id)
        
        return brand
    
    def remove_contributor(self, brand_id: str, user_id: str) -> Brand | None:
        """Remove contributor from brand"""
        
        brand = self.brands.get(brand_id)
        if not brand:
            return None
        
        brand.contributors = [u for u in brand.contributors if u != user_id]
        
        return brand
    
    def get_brand_analytics(self, brand_id: str) -> dict[str, Any]:
        """Get aggregated analytics for brand"""
        
        brand = self.brands.get(brand_id)
        if not brand:
            return {}
        
        return {
            "brand_id": brand_id,
            "name": brand.name,
            "status": brand.status.value,
            "total_assets": len(brand.assets),
            "most_used_assets": sorted(
                brand.assets,
                key=lambda a: a.usage_count,
                reverse=True
            )[:5],
            "monthly_reach": brand.monthly_reach,
            "monthly_engagement": brand.monthly_engagement,
            "team_size": len(brand.owners) + len(brand.contributors),
            "created_at": brand.created_at,
            "updated_at": brand.updated_at,
        }

# Global manager
brand_hub_manager = BrandHubManager()  # type: ignore[no-untyped-call]
