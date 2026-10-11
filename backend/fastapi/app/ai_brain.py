"""Compatibility import for ``app.domains.ai.brain``."""
from importlib import import_module as _import_module

_implementation = _import_module(f"{__package__}.domains.ai.brain")
for _name in dir(_implementation):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_implementation, _name)

__all__ = [name for name in globals() if not name.startswith("_")]
