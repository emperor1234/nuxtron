"""Compatibility import for the canonical SEO service module.

New code must import from app.domains.seo.services.seo_programmatic_service.
This adapter remains temporarily for existing clients and tests.
"""
from importlib import import_module as _import_module

_implementation = _import_module("backend.fastapi.app.domains.seo.services.seo_programmatic_service")
for _name in dir(_implementation):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_implementation, _name)

__all__ = [name for name in globals() if not name.startswith("_")]
