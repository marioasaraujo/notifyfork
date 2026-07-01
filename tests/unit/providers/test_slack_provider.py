import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from notifyfork.core.infrastructure.providers.slack_provider import SlackProvider


@pytest.fixture
def provider():
    return SlackProvider(bot_token="xoxb-test-token")


@pytest.mark.asyncio
class TestSlackProvider:
    async def test_name_is_correct(self, provider):
        assert provider.name == "slack"

    async def test_supports_slack_channel(self, provider):
        from notifyfork.core.domain.entities.notification import NotificationChannel
        assert provider.supports(NotificationChannel.SLACK)

    async def test_does_not_support_sms(self, provider):
        from notifyfork.core.domain.entities.notification import NotificationChannel
        assert not provider.supports(NotificationChannel.SMS)

    async def test_sends_plain_message_without_subject(self, provider):
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "ts": "1234567890.000"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            result = await provider.send(recipient="C012AB3CD", body="Alert triggered")

        assert result.success is True
        assert result.external_id == "1234567890.000"

    async def test_sends_block_message_with_subject(self, provider):
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "ts": "9999"}

        with patch("httpx.AsyncClient") as mock_client:
            post_mock = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = post_mock
            await provider.send(recipient="C012AB3CD", body="Body text", subject="Alert Title")

        payload = post_mock.call_args[1]["json"]
        assert "blocks" in payload
        assert payload["blocks"][0]["text"]["text"] == "Alert Title"

    async def test_returns_failure_on_slack_api_error(self, provider):
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": False, "error": "channel_not_found"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            result = await provider.send(recipient="INVALID", body="msg")

        assert result.success is False
        assert "channel_not_found" in result.error

    async def test_returns_failure_on_http_error(self, provider):
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("refused")
            )
            result = await provider.send(recipient="C012", body="msg")

        assert result.success is False
        assert result.error is not None
