"""
SendGrid delivery event webhook.

SendGrid batches multiple events in one POST as a JSON array.
Configure in SendGrid → Settings → Mail Settings → Event Webhook:
    https://yourdomain.com/api/v1/webhooks/sendgrid/events/

Each event in the array has:
    event       — processed | delivered | bounce | dropped | spamreport | unsubscribe
    sg_message_id — the external ID we stored as provider_message_id
    reason      — present on bounce/drop events

Security: SendGrid signs requests with a public key (Ed25519).
We verify the signature using the public key from your SendGrid account.
"""
import json
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from notifyfork.api.webhooks.tasks import process_delivery_update

logger = logging.getLogger(__name__)

SENDGRID_DELIVERED_EVENTS = {"delivered"}
SENDGRID_FAILED_EVENTS    = {"bounce", "dropped", "spamreport"}


class SendGridEventWebhookView(APIView):
    """
    POST /api/v1/webhooks/sendgrid/events/

    SendGrid sends a JSON array of events — can be many at once.
    We process each terminal event independently.
    Responds 200 immediately, enqueues each update to Celery.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request: Request) -> Response:
        if not self._validate_signature(request):
            logger.warning("Invalid SendGrid signature", extra={
                "ip": request.META.get("REMOTE_ADDR"),
            })
            return Response({"detail": "Invalid signature"}, status=status.HTTP_403_FORBIDDEN)

        try:
            events = request.data if isinstance(request.data, list) else json.loads(request.body)
        except (ValueError, TypeError):
            return Response({"detail": "Invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)

        queued = 0
        for event in events:
            event_type    = event.get("event", "").lower()
            sg_message_id = event.get("sg_message_id", "").split(".")[0]  # strip suffix
            reason        = event.get("reason") or event.get("type")

            if event_type not in SENDGRID_DELIVERED_EVENTS | SENDGRID_FAILED_EVENTS:
                continue  # intermediate events (open, click, etc) — skip

            notification_id = self._find_notification_id(sg_message_id)
            if not notification_id:
                continue

            logger.info("SendGrid event received", extra={
                "event": event_type,
                "sg_message_id": sg_message_id,
                "notification_id": notification_id,
            })

            delivered = event_type in SENDGRID_DELIVERED_EVENTS
            process_delivery_update.delay(
                notification_id=notification_id,
                provider="sendgrid_email",
                delivered=delivered,
                reason=reason,
            )
            queued += 1

        return Response({"accepted": queued}, status=status.HTTP_200_OK)

    @staticmethod
    def _validate_signature(request: Request) -> bool:
        """
        Validates Ed25519 signature from SendGrid.
        Public key is in SendGrid → Settings → Mail Settings → Event Webhook.
        """
        public_key = getattr(settings, "SENDGRID_WEBHOOK_PUBLIC_KEY", None)
        if not public_key:
            logger.warning("SENDGRID_WEBHOOK_PUBLIC_KEY not set — skipping validation (dev only)")
            return True

        try:
            from sendgrid.helpers.eventwebhook import EventWebhook, EventWebhookHeader
            ew = EventWebhook()
            ec_public_key = ew.convert_public_key_to_ecdsa(public_key)
            return ew.verify_signature(
                ec_public_key,
                request.body,
                request.META.get(EventWebhookHeader.SIGNATURE, ""),
                request.META.get(EventWebhookHeader.TIMESTAMP, ""),
            )
        except Exception as e:
            logger.error("SendGrid signature validation error", extra={"error": str(e)})
            return False

    @staticmethod
    def _find_notification_id(sg_message_id: str) -> str | None:
        import asyncio
        from notifyfork.core.infrastructure.models.notification_model import NotificationModel

        async def _get():
            try:
                obj = await NotificationModel.objects.aget(provider_message_id=sg_message_id)
                return str(obj.id)
            except NotificationModel.DoesNotExist:
                return None

        return asyncio.get_event_loop().run_until_complete(_get())
