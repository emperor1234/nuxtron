"""Custom user model for the Nuxtron backend.

Deliberately a bare `AbstractUser` subclass with no extra fields yet. The
point of introducing it now — before any real migration touches `auth.User`
— is to avoid the well-known Django trap where swapping AUTH_USER_MODEL
after the first migration requires a painful data migration. Add
domain-specific fields here as real user-facing features land.
"""
from __future__ import annotations

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    class Meta:
        db_table = 'accounts_user'

    def __str__(self) -> str:
        return self.username
