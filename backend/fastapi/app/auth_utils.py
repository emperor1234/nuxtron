"""Compatibility alias for ``app.domains.identity.auth_utils``."""
import sys as _sys
from importlib import import_module as _import_module

_implementation = _import_module(f"{__package__}.domains.identity.auth_utils")
_sys.modules[__name__] = _implementation
