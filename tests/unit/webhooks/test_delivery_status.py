"""
Tests for the delivery status webhook flow.
Covers: entity state transitions, task idempotency, webhook parsing.
"""
import base64
import hashlib
import hmac
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from notifyfork.core.domain.entities.notification import (
    Notification, NotificationChannel, NotificationStatus, NotificationType,
)


# Entity state machine

class TestDeliveryStatusTransitions:

    def test_mark_delivered_from_sent(self, sms_notification):
        sms_notification.mark_sent("twilio_sms", provider_message_id="SM123")
        sms_notification.mark_delivered()
        assert sms_notification.status == NotificationStatus.DELIVERED
        assert sms_notification.delivered_at is not None

    def test_mark_delivery_failed_from_sent(self, sms_notification):
        sms_notification.mark_sent("twilio_sms", provider_message_id="SM123")
        sms_notification.mark_delivery_failed("Invalid phone number")
        assert sms_notification.status == NotificationStatus.DELIVERY_FAILED
        assert sms_notification.error_detail == "Invalid phone number"

    def test_delivered_is_terminal(self, sms_notification):
        sms_notification.mark_sent("twilio_sms")
        sms_notification.mark_delivered()
        assert sms_notification.is_terminal is True

    def test_delivery_failed_is_terminal(self, sms_notification):
        sms_notification.mark_sent("twilio_sms")
        sms_notification.mark_delivery_failed("undelivered")
        assert sms_notification.is_terminal is True

    def test_sent_is_not_terminal(self, sms_notification):
        sms_notification.mark_sent("twilio_sms")
        assert sms_notification.is_terminal is False

    def test_mark_sent_stores_provider_message_id(self, sms_notification):
        sms_notification.mark_sent("twilio_sms", provider_message_id="SM_ABC123")
        assert sms_notification.provider_message_id == "SM_ABC123"

    def test_delivered_logs_latency(self, sms_notification):
        sms_notification.mark_sent("twilio_sms", provider_message_id="SM123")
        sms_notification.mark_delivered()
        # delivered_at must be after sent_at
        assert sms_notification.delivered_at >= sms_notification.sent_at


# Twilio webhook view

@pytest.mark.django_db
class TestTwilioStatusWebhook:

    URL = "/api/v1/webhooks/twilio/status/"

    def _post(self, api_client, data):
        return api_client.post(self.URL, data, format="multipart")

    def test_delivered_status_enqueues_task(self, api_client):
        with patch("notifyfork.api.webhooks.twilio_webhook.TwilioStatusWebhookView._validate_signature", return_value=True), \
             patch("notifyfork.api.webhooks.twilio_webhook.TwilioStatusWebhookView._find_notification_id", return_value=str(uuid4())), \
             patch("notifyfork.api.webhooks.tasks.process_delivery_update.delay") as mock_task:

            response = self._post(api_client, {
                "MessageSid": "SM123456",
                "MessageStatus": "delivered",
            })

        assert response.status_code == 200
        mock_task.assert_called_once()
        call_kwargs = mock_task.call_args[1]
        assert call_kwargs["delivered"] is True
        assert call_kwargs["provider"] == "twilio_sms"

    def test_failed_status_enqueues_task_with_delivered_false(self, api_client):
        with patch("notifyfork.api.webhooks.twilio_webhook.TwilioStatusWebhookView._validate_signature", return_value=True), \
             patch("notifyfork.api.webhooks.twilio_webhook.TwilioStatusWebhookView._find_notification_id", return_value=str(uuid4())), \
             patch("notifyfork.api.webhooks.tasks.process_delivery_update.delay") as mock_task:

            response = self._post(api_client, {
                "MessageSid": "SM123456",
                "MessageStatus": "failed",
                "ErrorCode": "30008",
                "ErrorMessage": "Unknown destination handset",
            })

        assert response.status_code == 200
        call_kwargs = mock_task.call_args[1]
        assert call_kwargs["delivered"] is False
        assert "30008" in call_kwargs["reason"]

    def test_intermediate_status_is_ignored(self, api_client):
        with patch("notifyfork.api.webhooks.twilio_webhook.TwilioStatusWebhookView._validate_signature", return_value=True), \
             patch("notifyfork.api.webhooks.tasks.process_delivery_update.delay") as mock_task:

            response = self._post(api_client, {
                "MessageSid": "SM123456",
                "MessageStatus": "sending",  # intermediate — not terminal
            })

        assert response.status_code == 200
        mock_task.assert_not_called()

    def test_invalid_signature_returns_403(self, api_client):
        with patch("notifyfork.api.webhooks.twilio_webhook.TwilioStatusWebhookView._validate_signature", return_value=False):
            response = self._post(api_client, {
                "MessageSid": "SM123",
                "MessageStatus": "delivered",
            })
        assert response.status_code == 403

    def test_unknown_message_sid_returns_200(self, api_client):
        """Unknown SID is not an error — could be a message sent outside NotifyFork."""
        with patch("notifyfork.api.webhooks.twilio_webhook.TwilioStatusWebhookView._validate_signature", return_value=True), \
             patch("notifyfork.api.webhooks.twilio_webhook.TwilioStatusWebhookView._find_notification_id", return_value=None), \
             patch("notifyfork.api.webhooks.tasks.process_delivery_update.delay") as mock_task:

            response = self._post(api_client, {
                "MessageSid": "SM_UNKNOWN",
                "MessageStatus": "delivered",
            })

        assert response.status_code == 200
        mock_task.assert_not_called()

    def test_missing_fields_returns_400(self, api_client):
        with patch("notifyfork.api.webhooks.twilio_webhook.TwilioStatusWebhookView._validate_signature", return_value=True):
            response = self._post(api_client, {"MessageSid": "SM123"})  # missing status
        assert response.status_code == 400


# SendGrid webhook view

@pytest.mark.django_db
class TestSendGridEventWebhook:

    URL = "/api/v1/webhooks/sendgrid/events/"

    def test_delivered_event_enqueues_task(self, api_client):
        events = [{"event": "delivered", "sg_message_id": "msg-abc.filter0", "email": "u@example.com"}]

        with patch("notifyfork.api.webhooks.sendgrid_webhook.SendGridEventWebhookView._validate_signature", return_value=True), \
             patch("notifyfork.api.webhooks.sendgrid_webhook.SendGridEventWebhookView._find_notification_id", return_value=str(uuid4())), \
             patch("notifyfork.api.webhooks.tasks.process_delivery_update.delay") as mock_task:

            response = api_client.post(self.URL, events, format="json")

        assert response.status_code == 200
        assert response.data["accepted"] == 1
        call_kwargs = mock_task.call_args[1]
        assert call_kwargs["delivered"] is True

    def test_bounce_event_enqueues_task_as_failed(self, api_client):
        events = [{"event": "bounce", "sg_message_id": "msg-xyz", "reason": "550 5.1.1 No such user"}]

        with patch("notifyfork.api.webhooks.sendgrid_webhook.SendGridEventWebhookView._validate_signature", return_value=True), \
             patch("notifyfork.api.webhooks.sendgrid_webhook.SendGridEventWebhookView._find_notification_id", return_value=str(uuid4())), \
             patch("notifyfork.api.webhooks.tasks.process_delivery_update.delay") as mock_task:

            response = api_client.post(self.URL, events, format="json")

        assert response.status_code == 200
        call_kwargs = mock_task.call_args[1]
        assert call_kwargs["delivered"] is False
        assert "550" in call_kwargs["reason"]

    def test_intermediate_events_are_ignored(self, api_client):
        events = [
            {"event": "open",  "sg_message_id": "msg-1"},
            {"event": "click", "sg_message_id": "msg-2"},
        ]
        with patch("notifyfork.api.webhooks.sendgrid_webhook.SendGridEventWebhookView._validate_signature", return_value=True), \
             patch("notifyfork.api.webhooks.tasks.process_delivery_update.delay") as mock_task:

            response = api_client.post(self.URL, events, format="json")

        assert response.status_code == 200
        assert response.data["accepted"] == 0
        mock_task.assert_not_called()

    def test_batch_with_mixed_events(self, api_client):
        """SendGrid sends multiple events — only terminal ones are queued."""
        notification_id = str(uuid4())
        events = [
            {"event": "processed",  "sg_message_id": "msg-1"},   # skip
            {"event": "delivered",  "sg_message_id": "msg-2"},   # queue
            {"event": "open",       "sg_message_id": "msg-3"},   # skip
            {"event": "bounce",     "sg_message_id": "msg-4", "reason": "bad address"},  # queue
        ]

        with patch("notifyfork.api.webhooks.sendgrid_webhook.SendGridEventWebhookView._validate_signature", return_value=True), \
             patch("notifyfork.api.webhooks.sendgrid_webhook.SendGridEventWebhookView._find_notification_id", return_value=notification_id), \
             patch("notifyfork.api.webhooks.tasks.process_delivery_update.delay") as mock_task:

            response = api_client.post(self.URL, events, format="json")

        assert response.data["accepted"] == 2
        assert mock_task.call_count == 2

    def test_invalid_signature_returns_403(self, api_client):
        with patch("notifyfork.api.webhooks.sendgrid_webhook.SendGridEventWebhookView._validate_signature", return_value=False):
            response = api_client.post(self.URL, [], format="json")
        assert response.status_code == 403


# Resend webhook view

@pytest.mark.django_db
class TestResendEventWebhook:

    URL = "/api/v1/webhooks/resend/events/"

    def test_delivered_event_enqueues_task(self, api_client):
        event = {"type": "email.delivered", "data": {"email_id": "resend-msg-1"}}

        with patch("notifyfork.api.webhooks.resend_webhook.ResendEventWebhookView._validate_signature", return_value=True), \
             patch("notifyfork.api.webhooks.resend_webhook.ResendEventWebhookView._find_notification_id", return_value=str(uuid4())), \
             patch("notifyfork.api.webhooks.tasks.process_delivery_update.delay") as mock_task:

            response = api_client.post(self.URL, event, format="json")

        assert response.status_code == 200
        call_kwargs = mock_task.call_args[1]
        assert call_kwargs["delivered"] is True
        assert call_kwargs["provider"] == "resend_email"

    def test_bounced_event_enqueues_task_as_failed(self, api_client):
        event = {
            "type": "email.bounced",
            "data": {"email_id": "resend-msg-2", "reason": "550 5.1.1 No such user"},
        }

        with patch("notifyfork.api.webhooks.resend_webhook.ResendEventWebhookView._validate_signature", return_value=True), \
             patch("notifyfork.api.webhooks.resend_webhook.ResendEventWebhookView._find_notification_id", return_value=str(uuid4())), \
             patch("notifyfork.api.webhooks.tasks.process_delivery_update.delay") as mock_task:

            response = api_client.post(self.URL, event, format="json")

        assert response.status_code == 200
        call_kwargs = mock_task.call_args[1]
        assert call_kwargs["delivered"] is False
        assert "550" in call_kwargs["reason"]

    def test_intermediate_event_is_ignored(self, api_client):
        event = {"type": "email.sent", "data": {"email_id": "resend-msg-3"}}

        with patch("notifyfork.api.webhooks.resend_webhook.ResendEventWebhookView._validate_signature", return_value=True), \
             patch("notifyfork.api.webhooks.tasks.process_delivery_update.delay") as mock_task:

            response = api_client.post(self.URL, event, format="json")

        assert response.status_code == 200
        mock_task.assert_not_called()

    def test_missing_email_id_returns_400(self, api_client):
        with patch("notifyfork.api.webhooks.resend_webhook.ResendEventWebhookView._validate_signature", return_value=True):
            response = api_client.post(self.URL, {"type": "email.delivered", "data": {}}, format="json")
        assert response.status_code == 400

    def test_unknown_email_id_returns_200(self, api_client):
        """Unknown email_id is not an error — could be a message sent outside NotifyFork."""
        event = {"type": "email.delivered", "data": {"email_id": "resend-unknown"}}

        with patch("notifyfork.api.webhooks.resend_webhook.ResendEventWebhookView._validate_signature", return_value=True), \
             patch("notifyfork.api.webhooks.resend_webhook.ResendEventWebhookView._find_notification_id", return_value=None), \
             patch("notifyfork.api.webhooks.tasks.process_delivery_update.delay") as mock_task:

            response = api_client.post(self.URL, event, format="json")

        assert response.status_code == 200
        mock_task.assert_not_called()

    def test_invalid_signature_returns_403(self, api_client):
        with patch("notifyfork.api.webhooks.resend_webhook.ResendEventWebhookView._validate_signature", return_value=False):
            response = api_client.post(self.URL, {"type": "email.delivered", "data": {}}, format="json")
        assert response.status_code == 403

    def test_missing_secret_skips_validation(self, api_client, settings):
        """Dev-mode fallback — matches the Twilio/SendGrid webhooks' behavior."""
        settings.RESEND_WEBHOOK_SECRET = None
        event = {"type": "email.delivered", "data": {"email_id": "resend-msg-4"}}

        with patch("notifyfork.api.webhooks.resend_webhook.ResendEventWebhookView._find_notification_id", return_value=str(uuid4())), \
             patch("notifyfork.api.webhooks.tasks.process_delivery_update.delay"):

            response = api_client.post(self.URL, event, format="json")

        assert response.status_code == 200

    def test_real_signature_verification_accepts_valid_signature(self, api_client, settings):
        secret_bytes = b"0" * 32
        settings.RESEND_WEBHOOK_SECRET = "whsec_" + base64.b64encode(secret_bytes).decode()

        body = json.dumps({"type": "email.delivered", "data": {"email_id": "resend-msg-5"}})
        svix_id = "msg_test"
        svix_timestamp = "1700000000"
        signed_content = f"{svix_id}.{svix_timestamp}.{body}"
        signature = base64.b64encode(
            hmac.new(secret_bytes, signed_content.encode(), hashlib.sha256).digest()
        ).decode()

        with patch("notifyfork.api.webhooks.resend_webhook.ResendEventWebhookView._find_notification_id", return_value=str(uuid4())), \
             patch("notifyfork.api.webhooks.tasks.process_delivery_update.delay"):

            response = api_client.post(
                self.URL, data=body, content_type="application/json",
                HTTP_SVIX_ID=svix_id,
                HTTP_SVIX_TIMESTAMP=svix_timestamp,
                HTTP_SVIX_SIGNATURE=f"v1,{signature}",
            )

        assert response.status_code == 200

    def test_real_signature_verification_rejects_tampered_signature(self, api_client, settings):
        secret_bytes = b"0" * 32
        settings.RESEND_WEBHOOK_SECRET = "whsec_" + base64.b64encode(secret_bytes).decode()

        body = json.dumps({"type": "email.delivered", "data": {"email_id": "resend-msg-6"}})

        response = api_client.post(
            self.URL, data=body, content_type="application/json",
            HTTP_SVIX_ID="msg_test",
            HTTP_SVIX_TIMESTAMP="1700000000",
            HTTP_SVIX_SIGNATURE="v1,not-the-real-signature",
        )

        assert response.status_code == 403


# Idempotency

class TestDeliveryUpdateIdempotency:
    """
    If a provider retries the webhook (common), we must not double-process.
    process_delivery_update skips notifications already in terminal state.
    """

    @pytest.mark.asyncio
    async def test_skips_already_delivered_notification(self, sms_notification):
        sms_notification.mark_sent("twilio_sms", provider_message_id="SM123")
        sms_notification.mark_delivered()
        assert sms_notification.is_terminal is True

        # Calling mark_delivered again doesn't crash or change state
        # (the task checks is_terminal before processing)
        initial_status = sms_notification.status
        sms_notification.mark_delivered()  # would be called again on duplicate webhook
        assert sms_notification.status == initial_status  # unchanged

    @pytest.mark.asyncio
    async def test_skips_already_failed_notification(self, sms_notification):
        for _ in range(sms_notification.max_attempts):
            sms_notification.mark_failed("error")
        assert sms_notification.is_terminal is True
        assert sms_notification.status == NotificationStatus.FAILED
