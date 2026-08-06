"""Tests for ira_connector_integration.py."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import httpx
from backend.fastapi.app.ira_connector_integration import (
    dispatch_email_via_connector,
    dispatch_slack_via_connector,
    dispatch_via_ira_connector,
    dispatch_webhook_via_connector,
    dispatch_whatsapp_via_connector,
    resolve_email_config,
    resolve_slack_config,
    resolve_twilio_config,
    resolve_webhook_config,
)

# --------------------------------------------------------------------------- #
#  resolve_email_config
# --------------------------------------------------------------------------- #

class TestResolveEmailConfig:
    def test_smtp_provider(self):
        connector = {"config": {
            "provider": "smtp",
            "host": "mail.example.com",
            "port": 465,
            "username": "user",
            "password": "pass",
            "from_email": "from@example.com",
        }}
        cfg = resolve_email_config(connector)
        assert cfg["provider"] == "smtp"
        assert cfg["host"] == "mail.example.com"
        assert cfg["port"] == 465
        assert cfg["from_email"] == "from@example.com"

    def test_resend_provider(self):
        connector = {"config": {
            "provider": "resend",
            "api_key": "re_key_123",
        }}
        cfg = resolve_email_config(connector)
        assert cfg["provider"] == "resend"
        assert cfg["api_key"] == "re_key_123"
        assert "resend.com" in cfg["base_url"]

    def test_default_provider_from_arg(self):
        connector = {"config": {}}
        cfg = resolve_email_config(connector, env_provider="smtp")
        assert cfg["provider"] == "smtp"

    def test_env_fallbacks_for_smtp(self):
        connector = {"config": {"provider": "smtp"}}
        with patch.dict(os.environ, {
            "SMTP_HOST": "env.smtp.host",
            "SMTP_PORT": "25",
            "SMTP_USERNAME": "envuser",
            "SMTP_PASSWORD": "envpass",
            "SMTP_FROM_EMAIL": "env@from.com",
        }):
            cfg = resolve_email_config(connector)
        assert cfg["host"] == "env.smtp.host"
        assert cfg["port"] == 25

    def test_env_fallbacks_for_resend(self):
        connector = {"config": {"provider": "resend"}}
        with patch.dict(os.environ, {"RESEND_API_KEY": "re_envkey", "RESEND_API_BASE_URL": "https://my.resend"}):
            cfg = resolve_email_config(connector)
        assert cfg["api_key"] == "re_envkey"
        assert cfg["base_url"] == "https://my.resend"


# --------------------------------------------------------------------------- #
#  resolve_slack_config
# --------------------------------------------------------------------------- #

class TestResolveSlackConfig:
    def test_from_connector(self):
        connector = {"config": {
            "webhook_url": "https://hooks.slack.com/xxx",
            "channel": "#alerts",
        }}
        cfg = resolve_slack_config(connector)
        assert cfg["webhook_url"] == "https://hooks.slack.com/xxx"
        assert cfg["channel"] == "#alerts"

    def test_defaults(self):
        connector = {"config": {}}
        cfg = resolve_slack_config(connector)
        assert cfg["channel"] == "#ira-alerts"
        assert cfg["username"] == "IRA"


# --------------------------------------------------------------------------- #
#  resolve_twilio_config
# --------------------------------------------------------------------------- #

class TestResolveTwilioConfig:
    def test_from_connector(self):
        connector = {"config": {
            "account_sid": "ACtest",
            "auth_token": "authtoken",
            "from_number": "+11234567890",
        }}
        cfg = resolve_twilio_config(connector)
        assert cfg["account_sid"] == "ACtest"
        assert cfg["from_number"] == "+11234567890"

    def test_env_fallback(self):
        connector = {"config": {}}
        with patch.dict(os.environ, {
            "TWILIO_ACCOUNT_SID": "ACENV",
            "TWILIO_AUTH_TOKEN": "envtoken",
            "TWILIO_FROM_NUMBER": "+10000000000",
        }):
            cfg = resolve_twilio_config(connector)
        assert cfg["account_sid"] == "ACENV"


# --------------------------------------------------------------------------- #
#  resolve_webhook_config
# --------------------------------------------------------------------------- #

class TestResolveWebhookConfig:
    def test_from_connector(self):
        connector = {"config": {
            "url": "https://my.webhook.com/hook",
            "method": "PUT",
            "auth_type": "bearer",
            "auth_value": "mytoken",
        }}
        cfg = resolve_webhook_config(connector)
        assert cfg["url"] == "https://my.webhook.com/hook"
        assert cfg["method"] == "PUT"
        assert cfg["auth_type"] == "bearer"

    def test_defaults(self):
        connector = {"config": {}}
        cfg = resolve_webhook_config(connector)
        assert cfg["method"] == "POST"
        assert cfg["auth_type"] == "none"


# --------------------------------------------------------------------------- #
#  dispatch_email_via_connector
# --------------------------------------------------------------------------- #

class TestDispatchEmail:
    def _smtp_connector(self):
        return {"config": {
            "provider": "smtp",
            "host": "smtp.example.com",
            "port": 587,
            "username": "user",
            "password": "pass",
            "from_email": "ira@example.com",
        }}

    def _resend_connector(self):
        return {"config": {
            "provider": "resend",
            "api_key": "re_key",
            "from_email": "ira@example.com",
        }}

    def test_smtp_success(self):
        connector = self._smtp_connector()
        mock_smtp = MagicMock()
        with patch("smtplib.SMTP") as mock_cls:
            mock_cls.return_value.__enter__ = lambda s: mock_smtp
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = dispatch_email_via_connector(
                ira_connector=connector,
                recipient="to@example.com",
                subject="Test",
                body="Hello",
            )
        assert result["provider"] == "smtp"
        assert result["delivery_status"] in ("sent", "queued")

    def test_smtp_exception_queues(self):
        connector = self._smtp_connector()
        with patch("smtplib.SMTP", side_effect=Exception("Connection refused")):
            result = dispatch_email_via_connector(
                ira_connector=connector,
                recipient="to@example.com",
                subject="Test",
                body="Hello",
            )
        assert result["delivery_status"] == "queued"
        assert result["reason"] == "smtp_delivery_failed"

    def test_resend_success(self):
        connector = self._resend_connector()
        mock_response = MagicMock()
        mock_response.is_success = True
        with patch("httpx.post", return_value=mock_response):
            result = dispatch_email_via_connector(
                ira_connector=connector,
                recipient="to@example.com",
                subject="Test",
                body="Hello",
            )
        assert result["provider"] == "resend"
        assert result["delivery_status"] == "sent"

    def test_resend_http_error_queues(self):
        connector = self._resend_connector()
        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 422
        with patch("httpx.post", return_value=mock_response):
            result = dispatch_email_via_connector(
                ira_connector=connector,
                recipient="to@example.com",
                subject="Test",
                body="Hello",
            )
        assert result["delivery_status"] == "queued"
        assert "422" in result["reason"]

    def test_resend_timeout_queues(self):
        connector = self._resend_connector()
        with patch("httpx.post", side_effect=httpx.TimeoutException("timed out")):
            result = dispatch_email_via_connector(
                ira_connector=connector,
                recipient="to@example.com",
                subject="Test",
                body="Hello",
            )
        assert result["delivery_status"] == "queued"
        assert result["reason"] == "timeout"

    def test_resend_http_error_exception_queues(self):
        connector = self._resend_connector()
        with patch("httpx.post", side_effect=httpx.HTTPError("bad request")):
            result = dispatch_email_via_connector(
                ira_connector=connector,
                recipient="to@example.com",
                subject="Test",
                body="Hello",
            )
        assert result["delivery_status"] == "queued"

    def test_no_provider_configured(self):
        connector = {"config": {"provider": "unknown_provider"}}
        result = dispatch_email_via_connector(
            ira_connector=connector,
            recipient="to@example.com",
            subject="Test",
            body="Hello",
        )
        assert result["delivery_status"] == "queued"
        assert result["reason"] == "no_provider_configured"


# --------------------------------------------------------------------------- #
#  dispatch_slack_via_connector
# --------------------------------------------------------------------------- #

class TestDispatchSlack:
    def _slack_connector(self):
        return {"config": {"webhook_url": "https://hooks.slack.com/test"}}

    def test_no_webhook_url_queues(self):
        result = dispatch_slack_via_connector(
            ira_connector={"config": {}},
            message="alert",
        )
        assert result["delivery_status"] == "queued"
        assert result["reason"] == "no_webhook_url"

    def test_success(self):
        mock_response = MagicMock()
        mock_response.is_success = True
        with patch("httpx.post", return_value=mock_response):
            result = dispatch_slack_via_connector(
                ira_connector=self._slack_connector(),
                message="alert",
                title="Title",
            )
        assert result["delivery_status"] == "sent"

    def test_http_error_queues(self):
        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 500
        with patch("httpx.post", return_value=mock_response):
            result = dispatch_slack_via_connector(
                ira_connector=self._slack_connector(),
                message="alert",
            )
        assert result["delivery_status"] == "queued"

    def test_timeout_queues(self):
        with patch("httpx.post", side_effect=httpx.TimeoutException("timeout")):
            result = dispatch_slack_via_connector(
                ira_connector=self._slack_connector(),
                message="alert",
            )
        assert result["delivery_status"] == "queued"
        assert result["reason"] == "timeout"

    def test_http_exception_queues(self):
        with patch("httpx.post", side_effect=httpx.HTTPError("bad")):
            result = dispatch_slack_via_connector(
                ira_connector=self._slack_connector(),
                message="alert",
            )
        assert result["delivery_status"] == "queued"


# --------------------------------------------------------------------------- #
#  dispatch_whatsapp_via_connector
# --------------------------------------------------------------------------- #

class TestDispatchWhatsapp:
    def _twilio_connector(self):
        return {"config": {
            "account_sid": "ACxxx",
            "auth_token": "authxxx",
            "from_number": "+10000000001",
        }}

    def test_missing_credentials_queues(self):
        result = dispatch_whatsapp_via_connector(
            ira_connector={"config": {}},
            recipient="+11234567890",
            body="Test message",
        )
        assert result["delivery_status"] == "queued"
        assert result["reason"] == "missing_credentials"

    def test_success(self):
        mock_response = MagicMock()
        mock_response.is_success = True
        with patch("httpx.post", return_value=mock_response):
            result = dispatch_whatsapp_via_connector(
                ira_connector=self._twilio_connector(),
                recipient="+11234567890",
                body="Hello",
            )
        assert result["delivery_status"] == "sent"

    def test_http_error_queues(self):
        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 400
        with patch("httpx.post", return_value=mock_response):
            result = dispatch_whatsapp_via_connector(
                ira_connector=self._twilio_connector(),
                recipient="+11234567890",
                body="Hello",
            )
        assert result["delivery_status"] == "queued"

    def test_timeout_queues(self):
        with patch("httpx.post", side_effect=httpx.TimeoutException("timeout")):
            result = dispatch_whatsapp_via_connector(
                ira_connector=self._twilio_connector(),
                recipient="+11234567890",
                body="Hello",
            )
        assert result["delivery_status"] == "queued"
        assert result["reason"] == "timeout"

    def test_http_exception_queues(self):
        with patch("httpx.post", side_effect=httpx.HTTPError("err")):
            result = dispatch_whatsapp_via_connector(
                ira_connector=self._twilio_connector(),
                recipient="+11234567890",
                body="Hello",
            )
        assert result["delivery_status"] == "queued"


# --------------------------------------------------------------------------- #
#  dispatch_webhook_via_connector
# --------------------------------------------------------------------------- #

class TestDispatchWebhook:
    def _webhook_connector(self, auth_type="none", auth_value=""):
        return {"config": {
            "url": "https://my.webhook.com/hook",
            "method": "POST",
            "auth_type": auth_type,
            "auth_value": auth_value,
        }}

    def test_no_url_queues(self):
        result = dispatch_webhook_via_connector(
            ira_connector={"config": {}},
            payload={"event": "test"},
        )
        assert result["delivery_status"] == "queued"
        assert result["reason"] == "no_url_configured"

    def test_success_no_auth(self):
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        with patch("httpx.request", return_value=mock_response):
            result = dispatch_webhook_via_connector(
                ira_connector=self._webhook_connector(),
                payload={"event": "test"},
            )
        assert result["delivery_status"] == "sent"

    def test_bearer_auth_applied(self):
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        with patch("httpx.request", return_value=mock_response) as mock_req:
            dispatch_webhook_via_connector(
                ira_connector=self._webhook_connector(auth_type="bearer", auth_value="mytoken"),
                payload={},
            )
        call_kwargs = mock_req.call_args[1]
        assert "Authorization" in call_kwargs["headers"]
        assert "Bearer mytoken" in call_kwargs["headers"]["Authorization"]

    def test_api_key_auth_applied(self):
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        with patch("httpx.request", return_value=mock_response) as mock_req:
            dispatch_webhook_via_connector(
                ira_connector=self._webhook_connector(auth_type="api_key", auth_value="apikey123"),
                payload={},
            )
        call_kwargs = mock_req.call_args[1]
        assert call_kwargs["headers"].get("X-API-Key") == "apikey123"

    def test_http_error_status_queues(self):
        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 503
        with patch("httpx.request", return_value=mock_response):
            result = dispatch_webhook_via_connector(
                ira_connector=self._webhook_connector(),
                payload={},
            )
        assert result["delivery_status"] == "queued"

    def test_timeout_queues(self):
        with patch("httpx.request", side_effect=httpx.TimeoutException("timeout")):
            result = dispatch_webhook_via_connector(
                ira_connector=self._webhook_connector(),
                payload={},
            )
        assert result["delivery_status"] == "queued"
        assert result["reason"] == "timeout"

    def test_http_exception_queues(self):
        with patch("httpx.request", side_effect=httpx.HTTPError("err")):
            result = dispatch_webhook_via_connector(
                ira_connector=self._webhook_connector(),
                payload={},
            )
        assert result["delivery_status"] == "queued"


# --------------------------------------------------------------------------- #
#  dispatch_via_ira_connector (unified)
# --------------------------------------------------------------------------- #

class TestDispatchViaIraConnector:
    def test_email_dispatch(self):
        with patch("backend.fastapi.app.ira_connector_integration.dispatch_email_via_connector",
                   return_value={"delivery_status": "sent"}) as mock_fn:
            result = dispatch_via_ira_connector(
                channel="email",
                ira_connector={},
                recipient="a@b.com",
                subject="sub",
                body="body",
            )
        assert result["delivery_status"] == "sent"
        mock_fn.assert_called_once()

    def test_slack_dispatch(self):
        with patch("backend.fastapi.app.ira_connector_integration.dispatch_slack_via_connector",
                   return_value={"delivery_status": "sent"}):
            result = dispatch_via_ira_connector(
                channel="slack",
                ira_connector={},
                message="hi",
            )
        assert result["delivery_status"] == "sent"

    def test_whatsapp_dispatch(self):
        with patch("backend.fastapi.app.ira_connector_integration.dispatch_whatsapp_via_connector",
                   return_value={"delivery_status": "sent"}):
            result = dispatch_via_ira_connector(
                channel="whatsapp",
                ira_connector={},
                recipient="+1234567890",
                body="msg",
            )
        assert result["delivery_status"] == "sent"

    def test_webhook_dispatch(self):
        with patch("backend.fastapi.app.ira_connector_integration.dispatch_webhook_via_connector",
                   return_value={"delivery_status": "sent"}):
            result = dispatch_via_ira_connector(
                channel="webhook",
                ira_connector={},
                payload={"event": "test"},
            )
        assert result["delivery_status"] == "sent"

    def test_unknown_channel_fails(self):
        result = dispatch_via_ira_connector(
            channel="unknown",  # type: ignore
            ira_connector={},
        )
        assert result["delivery_status"] == "failed"
        assert "unknown_channel" in result["reason"]
