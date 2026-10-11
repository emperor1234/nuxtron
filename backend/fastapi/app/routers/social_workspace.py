"""Compatibility alias; canonical owner is domains.social.bootstrap.

Removal gate: no legacy imports and API migration complete.
"""
import sys
from importlib import import_module
sys.modules[__name__] = import_module(f"{__package__.rsplit('.', 1)[0]}.domains.social.bootstrap")
