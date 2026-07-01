from unittest.mock import MagicMock

from notifyfork.core.infrastructure.container.providers import DEFAULT_PROVIDER_ORDER, _ordered


def make_provider(name: str) -> MagicMock:
    provider = MagicMock()
    provider.name = name
    return provider


class TestProviderOrdering:
    def test_uses_default_order_when_no_env_override(self, monkeypatch):
        monkeypatch.delenv("NOTIFYFORK_PROVIDER_ORDER", raising=False)
        smtp = make_provider("smtp_email")
        sendgrid = make_provider("sendgrid_email")

        # Registered SMTP first, but the default order puts SendGrid ahead
        result = _ordered([smtp, sendgrid])

        assert [p.name for p in result] == ["sendgrid_email", "smtp_email"]

    def test_env_override_wins_over_default_order(self, monkeypatch):
        monkeypatch.setenv("NOTIFYFORK_PROVIDER_ORDER", "smtp_email,sendgrid_email")
        smtp = make_provider("smtp_email")
        sendgrid = make_provider("sendgrid_email")

        result = _ordered([sendgrid, smtp])

        assert [p.name for p in result] == ["smtp_email", "sendgrid_email"]

    def test_providers_not_listed_are_appended_after(self, monkeypatch):
        monkeypatch.setenv("NOTIFYFORK_PROVIDER_ORDER", "smtp_email")
        smtp = make_provider("smtp_email")
        slack = make_provider("slack")

        result = _ordered([slack, smtp])

        assert [p.name for p in result] == ["smtp_email", "slack"]

    def test_default_order_covers_every_known_provider_name(self):
        known_names = {
            "twilio_sms", "twilio_whatsapp", "sendgrid_email", "resend_email",
            "smtp_email", "firebase_push", "slack",
        }
        assert set(DEFAULT_PROVIDER_ORDER) == known_names
