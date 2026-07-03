import pytest
from unittest.mock import MagicMock, patch

from twilio.base.exceptions import TwilioRestException

from notifyfork.core.domain.entities.notification import NotificationChannel
from notifyfork.core.domain.value_objects.template import NotificationTemplate, TemplateMode
from notifyfork.core.infrastructure.providers.twilio_provider import TwilioSMSProvider


@pytest.fixture
def provider():
    return TwilioSMSProvider(
        account_sid="ACtest",
        auth_token="token",
        from_number="+15550000000",
    )


@pytest.fixture
def local_template():
    return NotificationTemplate(
        id="sms_otp",
        body="Your code is: $code",
        mode=TemplateMode.LOCAL,
    )


@pytest.mark.asyncio
class TestTwilioSMSProvider:
    async def test_name_and_channel(self, provider):
        assert provider.name == "twilio_sms"
        assert provider.supports(NotificationChannel.SMS)
        assert not provider.supports(NotificationChannel.WHATSAPP)

    async def test_local_mode_renders_body(self, provider, local_template):
        with patch.object(provider._client.messages, "create") as mock_create:
            mock_create.return_value = MagicMock(sid="SMtest")
            await provider.send_with_template("+5511999999999", local_template, {"code": "999"})
            assert mock_create.call_args[1]["body"] == "Your code is: 999"
            assert mock_create.call_args[1]["from_"] == "+15550000000"
            assert mock_create.call_args[1]["to"] == "+5511999999999"

    async def test_returns_success_with_sid(self, provider, local_template):
        with patch.object(provider._client.messages, "create") as mock_create:
            mock_create.return_value = MagicMock(sid="SM123456")
            result = await provider.send_with_template("+5511999999999", local_template, {"code": "1"})

        assert result.success is True
        assert result.provider_name == "twilio_sms"
        assert result.external_id == "SM123456"

    async def test_returns_failure_on_twilio_error(self, provider, local_template):
        with patch.object(provider._client.messages, "create") as mock_create:
            mock_create.side_effect = TwilioRestException(
                status=400, uri="/Messages", msg="Invalid number", code=21211
            )
            result = await provider.send_with_template("+invalid", local_template, {"code": "1"})

        assert result.success is False
        assert result.provider_name == "twilio_sms"
        assert "21211" in result.error
        assert "Invalid number" in result.error
