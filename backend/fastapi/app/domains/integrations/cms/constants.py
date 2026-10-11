"""Integrations/Cms constants and configuration vocabulary."""

from __future__ import annotations
from ....deps import AuthContext
from ....deps import require_auth
from fastapi import Depends
from typing import Annotated

AuthDep = Annotated[AuthContext, Depends(require_auth)]

CMS_CONNECTION_NOT_FOUND = "CMS connection not found."

SUPPORTED_CMS = [
    "wordpress",
    "webflow",
    "contentful",
    "sanity",
    "ghost",
    "hubspot_cms",
    "shopify",
    "notion",
    "confluence",
    "wix",
    "squarespace",
    "drupal",
    "strapi",
    "medium",
    "custom",
]
