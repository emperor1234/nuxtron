"""
Domain models for the Intelligence app.

`IntelligenceProbe` is intentionally minimal: it is the bootstrap row we write
during deploy-time readiness checks to prove the DB connection round-trips.
Remove it once a real intelligence domain model lands.
"""
from __future__ import annotations

from django.db import models


class IntelligenceProbe(models.Model):
    """Smoke-test row used only by the readiness probe to verify DB write."""

    created_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=64, default='bootstrap')

    class Meta:
        db_table = 'intelligence_probe'

    def __str__(self) -> str:
        return f'IntelligenceProbe(id={self.pk}, source={self.source!r})'
