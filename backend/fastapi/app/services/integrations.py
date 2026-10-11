"""Compatibility alias; canonical owner is domains.integrations.provider_helpers.

Removal gate: all callers migrated and import deprecation complete.
"""
import sys
from importlib import import_module
sys.modules[__name__] = import_module(f"{__package__.rsplit('.',1)[0]}.domains.integrations.provider_helpers")
