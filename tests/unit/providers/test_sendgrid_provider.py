import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from notifyfork.core.domain.entities.notification import NotificationChannel
from notifyfork.core.domain.value_objects.template import NotificationTemplate, TemplateMode, VariableMapping
from notifyfork.core.infrastructure.providers.sendgrid_provider import SendGridEmailProvider


@pytest.fixture
def provider():
    return SendGridEmailProvider(
        api_key="SG.test",
        from_email="no-reply@example.com",
        from_name="Example App",
    )


@pytest.fixture
def local_email_template():
    return NotificationTemplate(
        id="order_local",
        body="<p>Order $order_id confirmed. Total: $total</p>",
        subject="Order $order_id confirmed",
        mode=TemplateMode.LOCAL,
    )


@pytest.fixture
def external_email_template():
    return NotificationTemplate(
        id="order_external",
        body="d-abc123def456",
        mode=TemplateMode.EXTERNAL,
        variable_mapping=VariableMapping({
            "order_id": "order_id",
            "total": "order_total",
            "name": "customer_name",
        }),
    )


def mock_sendgrid_response(status_code: int, message_id: str = "msg-123") -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.headers = {"X-Message-Id": message_id}
    mock.text = ""
    return mock


@pytest.mark.asyncio
class TestSendGridEmailProvider:
    async def test_name_and_channel(self, provider):
        assert provider.name == "sendgrid_email"
        assert provider.supports(NotificationChannel.EMAIL)
        assert not provider.supports(NotificationChannel.SMS)

    async def test_local_mode_sends_rendered_html(self, provider, local_email_template):
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_sendgrid_response(202)
            )
            result = await provider.send_with_template(
                "user@example.com",
                local_email_template,
                {"order_id": "ORD-1", "total": "R$100"},
            )

        assert result.success is True
        assert result.external_id == "msg-123"

    async def test_local_mode_payload_has_content(self, provider, local_email_template):
        with patch("httpx.AsyncClient") as mock_client:
            post_mock = AsyncMock(return_value=mock_sendgrid_response(202))
            mock_client.return_value.__aenter__.return_value.post = post_mock

            await provider.send_with_template(
                "user@example.com",
                local_email_template,
                {"order_id": "ORD-1", "total": "R$100"},
            )

        payload = post_mock.call_args[1]["json"]
        assert "content" in payload
        assert "template_id" not in payload
        assert "ORD-1" in payload["content"][0]["value"]

    async def test_external_mode_uses_template_id(self, provider, external_email_template):
        with patch("httpx.AsyncClient") as mock_client:
            post_mock = AsyncMock(return_value=mock_sendgrid_response(202))
            mock_client.return_value.__aenter__.return_value.post = post_mock

            await provider.send_with_template(
                "user@example.com",
                external_email_template,
                {"order_id": "ORD-1", "total": "R$100", "name": "Mario"},
            )

        payload = post_mock.call_args[1]["json"]
        assert payload["template_id"] == "d-abc123def456"
        assert "content" not in payload

    async def test_external_mode_translates_variables(self, provider, external_email_template):
        with patch("httpx.AsyncClient") as mock_client:
            post_mock = AsyncMock(return_value=mock_sendgrid_response(202))
            mock_client.return_value.__aenter__.return_value.post = post_mock

            await provider.send_with_template(
                "user@example.com",
                external_email_template,
                {"order_id": "ORD-1", "total": "R$100", "name": "Mario"},
            )

        payload = post_mock.call_args[1]["json"]
        template_data = payload["personalizations"][0]["dynamic_template_data"]
        # "total" mapped to "order_total", "name" to "customer_name"
        assert "order_total" in template_data
        assert "customer_name" in template_data
        assert "total" not in template_data
        assert "name" not in template_data

    async def test_returns_failure_on_non_202(self, provider, local_email_template):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = '{"errors": [{"message": "Invalid API key"}]}'
        mock_resp.headers = {}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_resp
            )
            result = await provider.send_with_template(
                "user@example.com", local_email_template, {"order_id": "1", "total": "R$0"}
            )

        assert result.success is False
        assert "400" in result.error

    async def test_returns_failure_on_http_error(self, provider, local_email_template):
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("refused")
            )
            result = await provider.send_with_template(
                "user@example.com", local_email_template, {"order_id": "1", "total": "R$0"}
            )

        assert result.success is False
