"""Compatibility alias for ``app.domains.identity.oidc``."""
import sys as _sys
from importlib import import_module as _import_module

_implementation = _import_module(f"{__package__}.domains.identity.oidc")
_sys.modules[__name__] = _implementation
