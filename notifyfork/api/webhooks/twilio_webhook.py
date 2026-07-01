"""
Twilio delivery status webhook.

Twilio calls this endpoint when a message status changes.
Configure in Twilio Console → Phone Numbers → Status Callback URL:
    https://yourdomain.com/api/v1/webhooks/twilio/status/

Twilio sends form-data (not JSON) with these key fields:
    MessageSid    — the external ID we stored as provider_message_id
    MessageStatus — queued | sent | delivered | undelivered | failed

Security: Twilio signs every request with X-Twilio-Signature.
We validate this before processing — rejects spoofed requests.
"""
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from twilio.request_validator import RequestValidator

from notifyfork.api.webhooks.tasks import process_delivery_update

logger = logging.getLogger(__name__)

# Twilio statuses that mean "delivered to handset"
TWILIO_DELIVERED_STATUSES = {"delivered", "read"}

# Twilio statuses that mean "provider confirmed failure"
TWILIO_FAILED_STATUSES = {"failed", "undelivered"}


class TwilioStatusWebhookView(APIView):
    """
    POST /api/v1/webhooks/twilio/status/

    Validates Twilio signature, responds 200 immediately,
    enqueues status update to Celery for async processing.
    """

    authentication_classes = []   # Twilio uses signature, not token auth
    permission_classes = []
    parser_classes = [FormParser, MultiPartParser]   # Twilio posts form-data, not JSON

    def post(self, request: Request) -> Response:
        if not self._validate_signature(request):
            logger.warning("Invalid Twilio signature — possible spoofed webhook", extra={
                "ip": request.META.get("REMOTE_ADDR"),
            })
            return Response({"detail": "Invalid signature"}, status=status.HTTP_403_FORBIDDEN)

        message_sid    = request.data.get("MessageSid")
        message_status = request.data.get("MessageStatus", "").lower()
        error_code     = request.data.get("ErrorCode")
        error_message  = request.data.get("ErrorMessage")

        if not message_sid or not message_status:
            return Response({"detail": "Missing MessageSid or MessageStatus"},
                            status=status.HTTP_400_BAD_REQUEST)

        logger.info("Twilio webhook received", extra={
            "message_sid": message_sid,
            "message_status": message_status,
            "error_code": error_code,
        })

        # Twilio also sends intermediate statuses (queued, sending, sent) —
        # we only care about the final delivery outcome.
        if message_status not in TWILIO_DELIVERED_STATUSES | TWILIO_FAILED_STATUSES:
            return Response({"detail": "intermediate status, ignored"}, status=status.HTTP_200_OK)

        notification_id = self._find_notification_id(message_sid)
        if not notification_id:
            # Could be a message sent outside NotifyFork — not an error
            logger.info("No notification found for MessageSid", extra={"message_sid": message_sid})
            return Response({"detail": "unknown message"}, status=status.HTTP_200_OK)

        delivered = message_status in TWILIO_DELIVERED_STATUSES
        reason = f"Twilio [{error_code}]: {error_message}" if error_code else None

        process_delivery_update.delay(
            notification_id=str(notification_id),
            provider="twilio_sms",
            delivered=delivered,
            reason=reason,
        )

        return Response({"detail": "accepted"}, status=status.HTTP_200_OK)

    @staticmethod
    def _validate_signature(request: Request) -> bool:
        auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
        if not auth_token:
            logger.error("TWILIO_AUTH_TOKEN not configured — skipping signature validation")
            return True  # dev mode only — never in production

        validator = RequestValidator(auth_token)
        signature = request.META.get("HTTP_X_TWILIO_SIGNATURE", "")
        url = request.build_absolute_uri()
        return validator.validate(url, request.data, signature)

    @staticmethod
    def _find_notification_id(message_sid: str) -> str | None:
        """
        Looks up notification by the provider_message_id we stored at send time.
        Single indexed query — provider_message_id should be indexed in production.
        """
        import asyncio
        from notifyfork.core.infrastructure.models.notification_model import NotificationModel

        async def _get():
            try:
                obj = await NotificationModel.objects.aget(provider_message_id=message_sid)
                return str(obj.id)
            except NotificationModel.DoesNotExist:
                return None

        return asyncio.get_event_loop().run_until_complete(_get())
