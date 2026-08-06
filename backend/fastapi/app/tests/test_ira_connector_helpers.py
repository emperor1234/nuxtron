"""Tests for pure resolver functions in ira_connector_integration.py."""
import os

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from backend.fastapi.app.ira_connector_integration import (
    resolve_email_config,
    resolve_slack_config,
    resolve_twilio_config,
    resolve_webhook_config,
)


class TestResolveEmailConfig:
    def test_smtp_provider(self):
        connector = {"config": {"provider": "smtp", "host": "smtp.example.com", "port": 465}}
        result = resolve_email_config(connector)
        assert result["provider"] == "smtp"
        assert result["host"] == "smtp.example.com"
        assert result["port"] == 465

    def test_resend_provider(self):
        connector = {"config": {"provider": "resend", "api_key": "re_abc123"}}
        result = resolve_email_config(connector)
        assert result["provider"] == "resend"
        assert result["api_key"] == "re_abc123"

    def test_default_provider_resend(self):
        connector = {}
        result = resolve_email_config(connector)
        assert result["provider"] == "resend"

    def test_from_email_set(self):
        connector = {"config": {"from_email": "hello@example.com"}}
        result = resolve_email_config(connector)
        assert result["from_email"] == "hello@example.com"

    def test_resend_base_url_trailing_slash_removed(self):
        connector = {"config": {"provider": "resend", "base_url": "https://api.resend.com/"}}
        result = resolve_email_config(connector)
        assert result["base_url"] == "https://api.resend.com"

    def test_smtp_port_defaults_to_587(self):
        connector = {"config": {"provider": "smtp"}}
        result = resolve_email_config(connector)
        assert result["port"] == 587


class TestResolveSlackConfig:
    def test_defaults(self):
        connector = {}
        result = resolve_slack_config(connector)
        assert result["channel"] == "#ira-alerts"
        assert result["username"] == "IRA"
        assert result["icon_emoji"] == ":robot_face:"

    def test_custom_channel(self):
        connector = {"config": {"channel": "#custom", "webhook_url": "https://hooks.slack.com/abc"}}
        result = resolve_slack_config(connector)
        assert result["channel"] == "#custom"
        assert result["webhook_url"] == "https://hooks.slack.com/abc"


class TestResolveTwilioConfig:
    def test_defaults_empty(self):
        connector = {}
        result = resolve_twilio_config(connector)
        assert result["base_url"] == "https://api.twilio.com"
        assert result["account_sid"] == ""

    def test_from_connector_config(self):
        connector = {
            "config": {
                "account_sid": "ACabc",
                "auth_token": "token123",
                "from_number": "+15550000",
            }
        }
        result = resolve_twilio_config(connector)
        assert result["account_sid"] == "ACabc"
        assert result["auth_token"] == "token123"
        assert result["from_number"] == "+15550000"

    def test_trailing_slash_removed_from_base_url(self):
        connector = {"config": {"base_url": "https://custom.twilio.com/"}}
        result = resolve_twilio_config(connector)
        assert result["base_url"] == "https://custom.twilio.com"


class TestResolveWebhookConfig:
    def test_defaults(self):
        connector = {}
        result = resolve_webhook_config(connector)
        assert result["method"] == "POST"
        assert result["auth_type"] == "none"
        assert result["url"] == ""

    def test_custom_values(self):
        connector = {
            "config": {
                "url": "https://example.com/hook",
                "method": "get",
                "auth_type": "bearer",
                "auth_value": "my-token",
            }
        }
        result = resolve_webhook_config(connector)
        assert result["url"] == "https://example.com/hook"
        assert result["method"] == "GET"  # uppercased
        assert result["auth_type"] == "bearer"
        assert result["auth_value"] == "my-token"

    def test_headers_default_empty_dict(self):
        connector = {}
        result = resolve_webhook_config(connector)
        assert result["headers"] == {}

    def test_custom_headers(self):
        connector = {"config": {"headers": {"X-Custom": "value"}}}
        result = resolve_webhook_config(connector)
        assert result["headers"] == {"X-Custom": "value"}
