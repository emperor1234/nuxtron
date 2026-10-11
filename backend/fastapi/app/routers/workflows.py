"""Compatibility alias; new callers use domains.workflows.bootstrap.

Removal gate: no legacy imports and route-contract migration complete.
"""
import sys
from importlib import import_module

sys.modules[__name__] = import_module(f"{__package__.rsplit('.', 1)[0]}.domains.workflows.bootstrap")
