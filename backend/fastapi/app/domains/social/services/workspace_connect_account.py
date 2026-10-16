"""Social Workspace workspace connect account service."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.persistence import _sw_audit
from ....domains.social.persistence import _sw_get_account
from ....domains.social.schemas import SocialEngageRequest
from ..constants import ACCOUNT_NOT_FOUND
from ..constants import INTEGRATIONS_WEBHOOKS_ROUTE
from ..constants import MESSAGE_NOT_FOUND
from ..constants import SUPPORTED_NETWORKS
from .brand import _sw_profile_defaults
from .workspace import _sw_http_error
from .workspace import _sw_seed_inbox_messages
from .workspace import _sw_seed_notifications
from .workspace import _sw_seed_post_history
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any
import os


def _sw_connect_account(
    st: _SocialWorkspaceState,
    *,
    tenant_id: str,
    network: str,
    account_name: str,
    handle: str,
    account_type: str,
    website: str | None,
    description: str | None,
    oauth_provider: str,
) -> tuple[dict[str, Any], bool]:
    clean_handle = handle.strip().lstrip("@")
    with st.lock:
        existing = next(
            (
                account
                for account in st.social_accounts
                if account.get("tenant_id") == tenant_id
                and account.get("network") == network
                and (account.get("handle") == clean_handle)
            ),
            None,
        )
        if existing:
            return (existing.copy(), False)
        account_id = len(st.social_accounts) + 1
        # Audience figures come only from the network's own API after OAuth;
        # a newly connected account starts at zero rather than a made-up number.
        account = {
            "id": account_id,
            "tenant_id": tenant_id,
            "network": network,
            "network_label": SUPPORTED_NETWORKS[network]["label"],
            "account_name": account_name.strip(),
            "handle": clean_handle,
            "account_type": account_type.strip(),
            "website": website,
            "description": description or f"{account_name.strip()} on {SUPPORTED_NETWORKS[network]['label']}.",
            "oauth_status": "connected",
            "oauth_provider": oauth_provider,
            "token_expires_at": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            "capabilities": SUPPORTED_NETWORKS[network]["formats"],
            "followers": 0,
            "likes": 0,
            "shares": 0,
            "comments": 0,
            "mentions": 0,
            "connected_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        st.social_accounts.append(account)
    _sw_profile_defaults(st, tenant_id)
    _sw_seed_notifications(st, tenant_id, network, account_name.strip())
    _sw_seed_inbox_messages(st, tenant_id, network, clean_handle)
    _sw_seed_post_history(st, tenant_id, network, account["id"])
    _sw_audit(st, tenant_id, "social_account_connected", account["id"])
    return (account.copy(), True)


def _sw_integration_catalog() -> list[dict[str, Any]]:
    return [
        {
            "category": "social_networks",
            "providers": [
                {
                    "vendor": "Meta (Facebook/Instagram)",
                    "provider_key": "facebook_instagram",
                    "configured": bool(os.getenv("SOCIAL_OAUTH_FACEBOOK_CLIENT_ID", "").strip()),
                },
                {
                    "vendor": "LinkedIn",
                    "provider_key": "linkedin",
                    "configured": bool(os.getenv("SOCIAL_OAUTH_LINKEDIN_CLIENT_ID", "").strip()),
                },
                {
                    "vendor": "X",
                    "provider_key": "x",
                    "configured": bool(os.getenv("SOCIAL_OAUTH_X_CLIENT_ID", "").strip()),
                },
                {
                    "vendor": "TikTok",
                    "provider_key": "tiktok",
                    "configured": bool(os.getenv("SOCIAL_OAUTH_TIKTOK_CLIENT_ID", "").strip()),
                },
                {
                    "vendor": "YouTube",
                    "provider_key": "youtube",
                    "configured": bool(os.getenv("SOCIAL_OAUTH_YOUTUBE_CLIENT_ID", "").strip()),
                },
            ],
        },
        {
            "category": "design_media",
            "providers": [
                {
                    "vendor": "Canva",
                    "provider_key": "canva",
                    "configured": True,
                    "route": "/social/integrations/canva/import",
                },
                {
                    "vendor": "Unsplash",
                    "provider_key": "unsplash",
                    "configured": True,
                    "route": "/api/fastapi/ai/social-studio/asset-library",
                },
                {
                    "vendor": "Giphy",
                    "provider_key": "giphy",
                    "configured": True,
                    "route": "/api/fastapi/ai/social-studio/asset-library",
                },
            ],
        },
        {
            "category": "automation",
            "providers": [
                {
                    "vendor": "Zapier",
                    "provider_key": "zapier",
                    "configured": True,
                    "route": INTEGRATIONS_WEBHOOKS_ROUTE,
                },
                {"vendor": "Make", "provider_key": "make", "configured": True, "route": INTEGRATIONS_WEBHOOKS_ROUTE},
                {
                    "vendor": "Custom Webhooks",
                    "provider_key": "custom",
                    "configured": True,
                    "route": INTEGRATIONS_WEBHOOKS_ROUTE,
                },
                {
                    "vendor": "n8n",
                    "provider_key": "n8n",
                    "configured": bool(
                        os.getenv("N8N_WEBHOOK_URL", "").strip() or os.getenv("N8N_API_KEY", "").strip()
                    ),
                    "route": INTEGRATIONS_WEBHOOKS_ROUTE,
                },
            ],
        },
        {
            "category": "communication",
            "providers": [
                {
                    "vendor": "Slack",
                    "provider_key": "slack",
                    "configured": bool(
                        os.getenv("SLACK_BOT_TOKEN", "").strip() or os.getenv("SLACK_WEBHOOK_URL", "").strip()
                    ),
                    "route": INTEGRATIONS_WEBHOOKS_ROUTE,
                },
                {
                    "vendor": "Microsoft Teams",
                    "provider_key": "microsoft_teams",
                    "configured": bool(
                        os.getenv("MS_TEAMS_WEBHOOK_URL", "").strip() or os.getenv("MICROSOFT_TEAMS_APP_ID", "").strip()
                    ),
                    "route": INTEGRATIONS_WEBHOOKS_ROUTE,
                },
                {
                    "vendor": "Discord",
                    "provider_key": "discord",
                    "configured": bool(
                        os.getenv("SOCIAL_OAUTH_DISCORD_CLIENT_ID", "").strip()
                        or os.getenv("DISCORD_BOT_TOKEN", "").strip()
                    ),
                    "route": "/social/oauth/{network}/start",
                },
            ],
        },
        {
            "category": "identity_sso",
            "providers": [
                {
                    "vendor": "Google Identity",
                    "provider_key": "google_identity",
                    "configured": bool(os.getenv("GOOGLE_CLIENT_ID", "").strip()),
                    "route": "/social/oauth/{network}/start",
                },
                {
                    "vendor": "Microsoft Entra ID",
                    "provider_key": "microsoft_entra",
                    "configured": bool(
                        os.getenv("MICROSOFT_CLIENT_ID", "").strip() or os.getenv("AZURE_AD_CLIENT_ID", "").strip()
                    ),
                    "route": "/social/oauth/{network}/start",
                },
                {
                    "vendor": "GitHub OAuth",
                    "provider_key": "github_oauth",
                    "configured": bool(os.getenv("GITHUB_CLIENT_ID", "").strip()),
                    "route": "/social/oauth/{network}/start",
                },
                {
                    "vendor": "Okta",
                    "provider_key": "okta",
                    "configured": bool(os.getenv("OKTA_CLIENT_ID", "").strip()),
                    "route": "/social/oauth/{network}/start",
                },
            ],
        },
        {
            "category": "crm_sales",
            "providers": [
                {
                    "vendor": "HubSpot",
                    "provider_key": "hubspot",
                    "configured": bool(os.getenv("HUBSPOT_ACCESS_TOKEN", "").strip()),
                    "route": "/social/integrations/webhooks/incoming/{provider}",
                },
                {
                    "vendor": "Salesforce",
                    "provider_key": "salesforce",
                    "configured": bool(
                        os.getenv("SALESFORCE_ACCESS_TOKEN", "").strip()
                        or os.getenv("SALESFORCE_CLIENT_ID", "").strip()
                    ),
                    "route": "/social/integrations/webhooks/incoming/{provider}",
                },
            ],
        },
        {
            "category": "cloud_storage",
            "providers": [
                {
                    "vendor": "Google Drive",
                    "provider_key": "google_drive",
                    "configured": bool(os.getenv("GOOGLE_DRIVE_CLIENT_ID", "").strip()),
                    "route": "/social/integrations/canva/import",
                },
                {
                    "vendor": "OneDrive",
                    "provider_key": "onedrive",
                    "configured": bool(os.getenv("ONEDRIVE_CLIENT_ID", "").strip()),
                    "route": "/social/integrations/canva/import",
                },
                {
                    "vendor": "Dropbox",
                    "provider_key": "dropbox",
                    "configured": bool(os.getenv("DROPBOX_APP_KEY", "").strip()),
                    "route": "/social/integrations/canva/import",
                },
                {
                    "vendor": "Box",
                    "provider_key": "box",
                    "configured": bool(os.getenv("BOX_CLIENT_ID", "").strip()),
                    "route": "/social/integrations/canva/import",
                },
            ],
        },
        {
            "category": "calendars_scheduling",
            "providers": [
                {
                    "vendor": "Google Calendar",
                    "provider_key": "google_calendar",
                    "configured": bool(os.getenv("GOOGLE_CALENDAR_CLIENT_ID", "").strip()),
                    "route": "/social/calendar",
                },
                {
                    "vendor": "Outlook Calendar",
                    "provider_key": "outlook_calendar",
                    "configured": bool(os.getenv("OUTLOOK_CLIENT_ID", "").strip()),
                    "route": "/social/calendar",
                },
            ],
        },
        {
            "category": "billing_payments",
            "providers": [
                {
                    "vendor": "Stripe",
                    "provider_key": "stripe",
                    "configured": bool(os.getenv("STRIPE_SECRET_KEY", "").strip()),
                    "route": "/social/integrations/webhooks",
                },
                {
                    "vendor": "PayPal",
                    "provider_key": "paypal",
                    "configured": bool(os.getenv("PAYPAL_CLIENT_ID", "").strip()),
                    "route": "/social/integrations/webhooks",
                },
            ],
        },
        {
            "category": "developer_tools",
            "providers": [
                {
                    "vendor": "GitHub",
                    "provider_key": "github",
                    "configured": bool(
                        os.getenv("GITHUB_APP_ID", "").strip() or os.getenv("WEBHOOK_GITHUB_SECRET", "").strip()
                    ),
                    "route": "/social/integrations/webhooks/incoming/{provider}",
                },
                {
                    "vendor": "GitLab",
                    "provider_key": "gitlab",
                    "configured": bool(os.getenv("GITLAB_CLIENT_ID", "").strip()),
                    "route": "/social/integrations/webhooks/incoming/{provider}",
                },
                {
                    "vendor": "Notion",
                    "provider_key": "notion",
                    "configured": bool(os.getenv("NOTION_API_KEY", "").strip()),
                    "route": "/social/integrations/webhooks/incoming/{provider}",
                },
                {
                    "vendor": "Trello",
                    "provider_key": "trello",
                    "configured": bool(os.getenv("TRELLO_API_KEY", "").strip()),
                    "route": "/social/integrations/webhooks/incoming/{provider}",
                },
                {
                    "vendor": "Asana",
                    "provider_key": "asana",
                    "configured": bool(os.getenv("ASANA_ACCESS_TOKEN", "").strip()),
                    "route": "/social/integrations/webhooks/incoming/{provider}",
                },
                {
                    "vendor": "ClickUp",
                    "provider_key": "clickup",
                    "configured": bool(os.getenv("CLICKUP_API_KEY", "").strip()),
                    "route": "/social/integrations/webhooks/incoming/{provider}",
                },
            ],
        },
        {
            "category": "ecommerce",
            "providers": [
                {
                    "vendor": "Shopify",
                    "provider_key": "shopify",
                    "configured": bool(
                        os.getenv("SHOPIFY_API_KEY", "").strip() or os.getenv("SHOPIFY_ACCESS_TOKEN", "").strip()
                    ),
                    "supported_triggers": ["new_product_release"],
                },
                {
                    "vendor": "WooCommerce",
                    "provider_key": "woocommerce",
                    "configured": bool(os.getenv("WEBHOOK_WOOCOMMERCE_SECRET", "").strip()),
                    "supported_triggers": ["new_product_release"],
                },
            ],
        },
        {
            "category": "analytics_marketing",
            "providers": [
                {
                    "vendor": "Google Analytics",
                    "provider_key": "google_analytics",
                    "configured": bool(os.getenv("GOOGLE_ANALYTICS_MEASUREMENT_ID", "").strip()),
                    "route": "/social/reports",
                },
                {
                    "vendor": "Meta Ads",
                    "provider_key": "meta_ads",
                    "configured": bool(
                        os.getenv("META_ADS_ACCESS_TOKEN", "").strip() or os.getenv("META_ACCESS_TOKEN", "").strip()
                    ),
                    "route": "/social/ads/analytics",
                },
                {
                    "vendor": "LinkedIn Ads",
                    "provider_key": "linkedin_ads",
                    "configured": bool(os.getenv("LINKEDIN_ADS_ACCESS_TOKEN", "").strip()),
                    "route": "/social/ads/analytics",
                },
            ],
        },
        {
            "category": "link_shortening",
            "providers": [
                {
                    "vendor": "Bitly",
                    "provider_key": "bitly",
                    "configured": bool(os.getenv("BITLY_ACCESS_TOKEN", "").strip()),
                },
                {
                    "vendor": "TinyURL",
                    "provider_key": "tinyurl",
                    "configured": bool(os.getenv("TINYURL_API_TOKEN", "").strip()),
                },
                {
                    "vendor": "Rebrandly",
                    "provider_key": "rebrandly",
                    "configured": bool(os.getenv("REBRANDLY_API_KEY", "").strip()),
                },
            ],
        },
    ]


def _sw_seed_inbox_for_tenant(st: _SocialWorkspaceState, tenant_id: str) -> None:
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return


def _sw_seed_automation_rules(st: _SocialWorkspaceState, tenant_id: str) -> None:
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return


def _sw_seed_automation_feeds(st: _SocialWorkspaceState, tenant_id: str) -> None:
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return


def _sw_seed_content_ideas(st: _SocialWorkspaceState, tenant_id: str) -> None:
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return


def _sw_workspace_overview(st: _SocialWorkspaceState, tenant_id: str) -> dict[str, Any]:
    with st.lock:
        accounts = [account for account in st.social_accounts if account.get("tenant_id") == tenant_id]
        inbox = [message for message in st.inbox_messages if message.get("tenant_id") == tenant_id]
        unread_notifications = [n for n in st.notifications if n.get("tenant_id") == tenant_id and (not n.get("read"))]
        competitors = [profile for profile in st.competitor_profiles if profile.get("tenant_id") == tenant_id]
        snapshots = [snap for snap in st.competitor_snapshots if snap.get("tenant_id") == tenant_id]
        scheduled = [post for post in st.scheduled_posts if post.get("tenant_id") == tenant_id]
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "overview": {
            "connected_accounts": len(accounts),
            "networks_connected": len({account.get("network") for account in accounts}),
            "inbox_open": sum((1 for message in inbox if message.get("status") != "complete")),
            "notifications_unread": len(unread_notifications),
            "competitors_tracked": len(competitors),
            "competitor_snapshots": len(snapshots),
            "scheduled_posts": len(scheduled),
            "engagement_total": sum(
                (
                    int(account.get("likes", 0)) + int(account.get("shares", 0)) + int(account.get("comments", 0))
                    for account in accounts
                )
            ),
        },
    }


def _sw_engage_inbox_message(
    st: _SocialWorkspaceState, message_id: int, payload: SocialEngageRequest, tenant_id: str
) -> dict[str, Any]:
    account = _sw_get_account(st, tenant_id, payload.account_id)
    if account is None:
        raise _sw_http_error(status_code=404, detail=ACCOUNT_NOT_FOUND)
    with st.lock:
        message = next(
            (item for item in st.inbox_messages if item.get("tenant_id") == tenant_id and item.get("id") == message_id),
            None,
        )
        if message is None:
            raise _sw_http_error(status_code=404, detail=MESSAGE_NOT_FOUND)
        message["replied"] = True
        message["replied_at"] = datetime.now(UTC).isoformat()
        message["status"] = "complete"
        message["assigned_to"] = payload.agent_name.strip()
        message["read"] = True
        message["updated_at"] = datetime.now(UTC).isoformat()
        engagement = {
            "message_id": message_id,
            "account_id": payload.account_id,
            "action": payload.action,
            "reply_text": payload.reply_text,
            "handled_by": payload.agent_name.strip(),
            "sent_at": datetime.now(UTC).isoformat(),
        }
        st.notifications.append(
            {
                "id": len(st.notifications) + 1,
                "tenant_id": tenant_id,
                "title": f"{account.get('network_label')} engagement sent",
                "message": f"{payload.action.title()} sent to @{message.get('author_handle')} from @{account.get('handle')}.",
                "category": "social",
                "priority": "info",
                "read": False,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        updated = message.copy()
    _sw_audit(st, tenant_id, "social_inbox_engaged", message_id)
    return {"status": "ok", "tenant_id": tenant_id, "message": updated, "engagement": engagement}


def _buffer_seed_community_comments(st: _SocialWorkspaceState, tenant_id: str) -> None:
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return
