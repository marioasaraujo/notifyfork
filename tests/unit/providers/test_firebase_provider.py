import pytest
from unittest.mock import MagicMock, patch

from firebase_admin.exceptions import FirebaseError

from notifyfork.core.domain.entities.notification import NotificationChannel
from notifyfork.core.domain.value_objects.template import NotificationTemplate, TemplateMode
from notifyfork.core.infrastructure.providers.firebase_provider import FirebasePushProvider


@pytest.fixture
def local_push_template():
    return NotificationTemplate(
        id="flash_sale",
        body="$percent% off today only",
        subject="Flash sale",
        mode=TemplateMode.LOCAL,
    )


class TestFirebasePushProviderInit:
    def test_initializes_app_when_none_exists(self):
        with patch("notifyfork.core.infrastructure.providers.firebase_provider.firebase_admin") as mock_admin, \
             patch("notifyfork.core.infrastructure.providers.firebase_provider.credentials") as mock_credentials:
            mock_admin.get_app.side_effect = ValueError("no default app")
            mock_cert = MagicMock()
            mock_credentials.Certificate.return_value = mock_cert

            FirebasePushProvider("credentials/firebase.json")

            mock_credentials.Certificate.assert_called_once_with("credentials/firebase.json")
            mock_admin.initialize_app.assert_called_once_with(mock_cert)

    def test_skips_initialize_when_app_already_exists(self):
        with patch("notifyfork.core.infrastructure.providers.firebase_provider.firebase_admin") as mock_admin, \
             patch("notifyfork.core.infrastructure.providers.firebase_provider.credentials") as mock_credentials:
            mock_admin.get_app.return_value = MagicMock()

            FirebasePushProvider("credentials/firebase.json")

            mock_admin.initialize_app.assert_not_called()
            mock_credentials.Certificate.assert_not_called()


@pytest.fixture
def provider():
    with patch("notifyfork.core.infrastructure.providers.firebase_provider.firebase_admin") as mock_admin, \
         patch("notifyfork.core.infrastructure.providers.firebase_provider.credentials"):
        mock_admin.get_app.return_value = MagicMock()
        return FirebasePushProvider("credentials/firebase.json")


@pytest.mark.asyncio
class TestFirebasePushProviderSend:
    async def test_name_and_channel(self, provider):
        assert provider.name == "firebase_push"
        assert provider.supports(NotificationChannel.PUSH)
        assert provider.supports("firebase_push")

    async def test_send_with_template_success(self, provider, local_push_template):
        with patch(
            "notifyfork.core.infrastructure.providers.firebase_provider.messaging"
        ) as mock_messaging:
            mock_messaging.send.return_value = "projects/x/messages/abc123"

            result = await provider.send_with_template(
                "device-token", local_push_template, {"percent": "20"}
            )

        assert result.success is True
        assert result.provider_name == "firebase_push"
        assert result.external_id == "projects/x/messages/abc123"

    async def test_send_returns_failure_on_firebase_error(self, provider, local_push_template):
        with patch(
            "notifyfork.core.infrastructure.providers.firebase_provider.messaging"
        ) as mock_messaging:
            mock_messaging.send.side_effect = FirebaseError("INTERNAL", "token invalid")

            result = await provider.send_with_template(
                "device-token", local_push_template, {"percent": "20"}
            )

        assert result.success is False
        assert result.provider_name == "firebase_push"
        assert "token invalid" in result.error
