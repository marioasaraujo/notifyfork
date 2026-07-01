import pytest
from unittest.mock import MagicMock, patch

from notifyfork.core.domain.entities.notification import NotificationChannel
from notifyfork.core.domain.value_objects.template import NotificationTemplate, TemplateMode, VariableMapping
from notifyfork.core.infrastructure.providers.whatsapp_provider import TwilioWhatsAppProvider


@pytest.fixture
def provider():
    return TwilioWhatsAppProvider(
        account_sid="ACtest",
        auth_token="token",
        from_number="+15550000000",
    )


@pytest.fixture
def local_template():
    return NotificationTemplate(
        id="wa_local",
        body="Your code is: $code",
        mode=TemplateMode.LOCAL,
    )


@pytest.fixture
def external_template():
    return NotificationTemplate(
        id="wa_otp",
        body="HXabc123def456",
        mode=TemplateMode.EXTERNAL,
        variable_mapping=VariableMapping({"name": "1", "code": "2"}),
    )


@pytest.mark.asyncio
class TestTwilioWhatsAppProvider:
    async def test_name_and_channel(self, provider):
        assert provider.name == "twilio_whatsapp"
        assert provider.supports(NotificationChannel.WHATSAPP)
        assert not provider.supports(NotificationChannel.SMS)

    async def test_adds_whatsapp_prefix(self, provider, local_template):
        with patch.object(provider._client.messages, "create") as mock_create:
            mock_create.return_value = MagicMock(sid="SMtest")
            await provider.send_with_template("+5511999999999", local_template, {"code": "123"})
            assert mock_create.call_args[1]["to"] == "whatsapp:+5511999999999"

    async def test_does_not_double_prefix(self, provider, local_template):
        with patch.object(provider._client.messages, "create") as mock_create:
            mock_create.return_value = MagicMock(sid="SMtest")
            await provider.send_with_template("whatsapp:+5511999999999", local_template, {"code": "1"})
            assert mock_create.call_args[1]["to"] == "whatsapp:+5511999999999"

    async def test_local_mode_renders_body(self, provider, local_template):
        with patch.object(provider._client.messages, "create") as mock_create:
            mock_create.return_value = MagicMock(sid="SMtest")
            await provider.send_with_template("+5511999999999", local_template, {"code": "999"})
            assert mock_create.call_args[1]["body"] == "Your code is: 999"

    async def test_external_mode_uses_content_sid(self, provider, external_template):
        with patch.object(provider._client.messages, "create") as mock_create:
            mock_create.return_value = MagicMock(sid="SM999")
            await provider.send_with_template(
                "+5511999999999", external_template, {"name": "Mario", "code": "847291"}
            )
            kwargs = mock_create.call_args[1]
            assert kwargs["content_sid"] == "HXabc123def456"
            assert "body" not in kwargs

    async def test_external_mode_translates_variables(self, provider, external_template):
        with patch.object(provider._client.messages, "create") as mock_create:
            mock_create.return_value = MagicMock(sid="SM999")
            await provider.send_with_template(
                "+5511999999999", external_template, {"name": "Mario", "code": "847291"}
            )
            kwargs = mock_create.call_args[1]
            # variables translated: name→1, code→2
            assert "1" in kwargs["content_variables"]
            assert "2" in kwargs["content_variables"]

    async def test_returns_success_with_sid(self, provider, local_template):
        with patch.object(provider._client.messages, "create") as mock_create:
            mock_create.return_value = MagicMock(sid="SM123456")
            result = await provider.send_with_template("+5511999999999", local_template, {"code": "1"})
        assert result.success is True
        assert result.external_id == "SM123456"

    async def test_returns_failure_on_twilio_error(self, provider, local_template):
        from twilio.base.exceptions import TwilioRestException
        with patch.object(provider._client.messages, "create") as mock_create:
            mock_create.side_effect = TwilioRestException(
                status=400, uri="/Messages", msg="Invalid number", code=21211
            )
            result = await provider.send_with_template("+invalid", local_template, {"code": "1"})
        assert result.success is False
        assert "21211" in result.error
