"""Compatibility alias; canonical owner is domains.billing.checkout.

Removal gate: all callers migrated and import deprecation complete.
"""
import sys
from importlib import import_module
sys.modules[__name__] = import_module(f"{__package__.rsplit('.',1)[0]}.domains.billing.checkout")
