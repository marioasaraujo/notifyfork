import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from notifyfork.core.domain.entities.notification import NotificationChannel
from notifyfork.core.domain.value_objects.template import NotificationTemplate
from notifyfork.core.infrastructure.providers.resend_provider import ResendEmailProvider


@pytest.fixture
def provider():
    return ResendEmailProvider(
        api_key="re_test",
        from_email="no-reply@example.com",
        from_name="Example App",
    )


@pytest.fixture
def local_email_template():
    return NotificationTemplate(
        id="order_local",
        body="<p>Order $order_id confirmed. Total: $total</p>",
        subject="Order $order_id confirmed",
    )


def mock_resend_response(status_code: int, message_id: str = "msg-123") -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = ""
    mock.json.return_value = {"id": message_id}
    return mock


@pytest.mark.asyncio
class TestResendEmailProvider:
    async def test_name_and_channel(self, provider):
        assert provider.name == "resend_email"
        assert provider.supports(NotificationChannel.EMAIL)
        assert not provider.supports(NotificationChannel.SMS)

    async def test_sends_rendered_html(self, provider, local_email_template):
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_resend_response(200)
            )
            result = await provider.send_with_template(
                "user@example.com",
                local_email_template,
                {"order_id": "ORD-1", "total": "R$100"},
            )

        assert result.success is True
        assert result.external_id == "msg-123"

    async def test_payload_has_rendered_body_and_sender(self, provider, local_email_template):
        with patch("httpx.AsyncClient") as mock_client:
            post_mock = AsyncMock(return_value=mock_resend_response(200))
            mock_client.return_value.__aenter__.return_value.post = post_mock

            await provider.send_with_template(
                "user@example.com",
                local_email_template,
                {"order_id": "ORD-1", "total": "R$100"},
            )

        payload = post_mock.call_args[1]["json"]
        assert payload["to"] == ["user@example.com"]
        assert payload["from"] == "Example App <no-reply@example.com>"
        assert "ORD-1" in payload["html"]

    async def test_returns_failure_on_non_2xx(self, provider, local_email_template):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = '{"message": "Invalid API key"}'

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_resp
            )
            result = await provider.send_with_template(
                "user@example.com", local_email_template, {"order_id": "1", "total": "R$0"}
            )

        assert result.success is False
        assert "401" in result.error

    async def test_returns_failure_on_http_error(self, provider, local_email_template):
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("refused")
            )
            result = await provider.send_with_template(
                "user@example.com", local_email_template, {"order_id": "1", "total": "R$0"}
            )

        assert result.success is False
