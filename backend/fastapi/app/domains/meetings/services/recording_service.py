"""Honest capability boundary for meeting recording providers.

Calendar integrations in this application can read and create meeting events,
but do not currently start recordings or reliably associate recording artifacts
with a specific meeting. Keep those operations unavailable until provider APIs,
participant consent, and meeting-scoped artifact ownership are implemented.
"""

from enum import Enum


class RecordingCapabilityUnavailable(RuntimeError):
    """Raised when a provider operation is not implemented or verifiable."""


class RecordingProvider(str, Enum):
    GOOGLE_MEET = "google_meet"
    TEAMS = "teams"


class RecordingManagementService:
    """Fail-closed interface for operations not supported by current adapters."""

    _providers = {"google", "outlook"}

    @classmethod
    def _validate_provider(cls, provider: str) -> None:
        if provider not in cls._providers:
            raise ValueError(f"Unsupported recording provider: {provider}")

    async def setup_recording(self, provider: str, event_id: str, access_token: str, **kwargs) -> dict:
        """Never report recording as started without a provider-side start API."""
        self._validate_provider(provider)
        raise RecordingCapabilityUnavailable(
            "Starting recordings is not supported by the configured calendar provider API."
        )

    async def get_recording_status(self, provider: str, event_id: str, access_token: str) -> dict:
        """Do not infer recording state from a calendar event or meeting link."""
        self._validate_provider(provider)
        raise RecordingCapabilityUnavailable(
            "The configured calendar provider does not expose a verified recording-status lookup here."
        )

    async def get_recording_link(self, provider: str, meeting_id: str, access_token: str) -> str | None:
        """Do not return an unassociated or cross-meeting recording artifact."""
        self._validate_provider(provider)
        raise RecordingCapabilityUnavailable(
            "A recording artifact cannot be safely associated with this meeting by the current provider adapter."
        )
