"""Social Workspace capabilities strict social startup blockers service."""

from .capabilities import _strict_social_mode_enabled
from .oauth import _oauth_mode
import os


def _strict_social_startup_blockers(*, db_backing_enabled: bool) -> list[str]:
    if not _strict_social_mode_enabled():
        return []
    blockers: list[str] = []
    if _oauth_mode() != "live":
        blockers.append("SOCIAL_OAUTH_MODE=live is required when SOCIAL_STRICT_NO_FALLBACK is enabled.")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        blockers.append("OPENAI_API_KEY is required when SOCIAL_STRICT_NO_FALLBACK is enabled.")
    if not (os.getenv("SOCIAL_AI_POLICY_JSON", "").strip() or os.getenv("SOCIAL_AI_POLICY_PATH", "").strip()):
        blockers.append("SOCIAL_AI_POLICY_JSON or SOCIAL_AI_POLICY_PATH is required in strict social mode.")
    if not os.getenv("SENTRY_DSN", "").strip():
        blockers.append("SENTRY_DSN is required in strict social mode.")
    if not os.getenv("STRIPE_SECRET_KEY", "").strip():
        blockers.append("STRIPE_SECRET_KEY is required in strict social mode.")
    if not os.getenv("CANVA_ACCESS_TOKEN", "").strip():
        blockers.append("CANVA_ACCESS_TOKEN is required in strict social mode.")
    if not db_backing_enabled:
        blockers.append("Durable social database backing is required in strict social mode.")
    if not any(
        (os.getenv(key, "").strip() for key in ("BITLY_ACCESS_TOKEN", "TINYURL_API_TOKEN", "REBRANDLY_API_KEY"))
    ):
        blockers.append(
            "At least one URL shortener key is required in strict social mode (Bitly, TinyURL, or Rebrandly)."
        )
    strict_integration_requirements: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("slack", ("SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET", "SLACK_WEBHOOK_URL")),
        ("google_login", ("GOOGLE_CLIENT_ID",)),
        ("microsoft_login", ("MICROSOFT_CLIENT_ID",)),
        ("zapier", ("SOCIAL_WEBHOOK_SECRET", "ZAPIER_WEBHOOK_URL")),
        ("make", ("SOCIAL_WEBHOOK_SECRET", "MAKE_WEBHOOK_URL")),
        ("n8n", ("N8N_WEBHOOK_URL", "N8N_API_KEY")),
        ("google_drive", ("GOOGLE_DRIVE_CLIENT_ID",)),
        ("onedrive", ("ONEDRIVE_CLIENT_ID",)),
        ("microsoft_teams", ("MS_TEAMS_WEBHOOK_URL", "MICROSOFT_TEAMS_APP_ID")),
        ("salesforce", ("SALESFORCE_CLIENT_ID", "SALESFORCE_ACCESS_TOKEN")),
        ("hubspot", ("HUBSPOT_ACCESS_TOKEN",)),
        ("okta", ("OKTA_CLIENT_ID",)),
        ("azure_ad", ("AZURE_AD_CLIENT_ID",)),
        ("outlook_calendar", ("OUTLOOK_CLIENT_ID",)),
        ("google_calendar", ("GOOGLE_CALENDAR_CLIENT_ID",)),
        ("notion", ("NOTION_API_KEY", "NOTION_WEBHOOK_SECRET")),
        ("discord", ("SOCIAL_OAUTH_DISCORD_CLIENT_ID", "DISCORD_BOT_TOKEN")),
        ("github", ("GITHUB_APP_ID", "WEBHOOK_GITHUB_SECRET")),
        ("gitlab", ("GITLAB_CLIENT_ID",)),
        ("project_management", ("TRELLO_API_KEY", "ASANA_ACCESS_TOKEN", "CLICKUP_API_KEY")),
    )
    for integration, required_env_keys in strict_integration_requirements:
        missing = [key for key in required_env_keys if not os.getenv(key, "").strip()]
        if missing:
            blockers.append(f"{integration} missing required credentials: {', '.join(missing)}")
    return blockers
