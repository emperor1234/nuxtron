"""Compatibility alias; canonical owner is domains.seo.platform.bootstrap.

Removal gate: no legacy imports and contract migration complete.
"""
import sys
from importlib import import_module
sys.modules[__name__] = import_module(f"{__package__.rsplit('.', 1)[0]}.domains.seo.platform.bootstrap")
