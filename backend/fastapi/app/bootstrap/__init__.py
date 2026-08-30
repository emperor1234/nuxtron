"""Application bootstrap package: composition root, edge policy and lifespan.

Attribute access is deferred so that importing a single bootstrap module (for
example ``bootstrap.middleware`` from ``legacy_main``) does not build the
application as a side effect.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ['app', 'create_app']

if TYPE_CHECKING:
    from .application import app, create_app


def __getattr__(name: str) -> Any:
    if name in __all__:
        from . import application

        return getattr(application, name)
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
