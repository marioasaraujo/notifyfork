"""
Resend delivery event webhook.

Resend calls this endpoint when an email's status changes.
Configure in Resend Dashboard → Webhooks → add endpoint:
    https://yourdomain.com/api/v1/webhooks/resend/events/

Resend sends one event per POST as JSON:
    type          — email.sent | email.delivered | email.delivery_delayed
                    | email.bounced | email.complained
    data.email_id — the external ID we stored as provider_message_id

Security: Resend signs every request using Svix (svix-id / svix-timestamp /
svix-signature headers, HMAC-SHA256). We validate this before processing —
rejects spoofed requests. See:
    https://resend.com/docs/dashboard/webhooks/verify-webhooks-requests
"""
import base64
import hashlib
import hmac
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from notifyfork.api.webhooks.tasks import process_delivery_update

logger = logging.getLogger(__name__)

RESEND_DELIVERED_EVENTS = {"email.delivered"}
RESEND_FAILED_EVENTS = {"email.bounced", "email.complained", "email.delivery_delayed"}


class ResendEventWebhookView(APIView):
    """
    POST /api/v1/webhooks/resend/events/

    Resend sends one event per request, signed via Svix headers.
    Responds 200 immediately, enqueues the update to Celery.
    """

    authentication_classes = []   # Resend uses signature, not token auth
    permission_classes = []

    def post(self, request: Request) -> Response:
        if not self._validate_signature(request):
            logger.warning("Invalid Resend signature — possible spoofed webhook", extra={
                "ip": request.META.get("REMOTE_ADDR"),
            })
            return Response({"detail": "Invalid signature"}, status=status.HTTP_403_FORBIDDEN)

        event_type = request.data.get("type", "")
        data = request.data.get("data") or {}
        email_id = data.get("email_id")

        if not email_id:
            return Response({"detail": "Missing data.email_id"}, status=status.HTTP_400_BAD_REQUEST)

        logger.info("Resend webhook received", extra={"type": event_type, "email_id": email_id})

        # Resend also sends intermediate events (sent, opened, clicked) —
        # we only care about the final delivery outcome.
        if event_type not in RESEND_DELIVERED_EVENTS | RESEND_FAILED_EVENTS:
            return Response({"detail": "intermediate event, ignored"}, status=status.HTTP_200_OK)

        notification_id = self._find_notification_id(email_id)
        if not notification_id:
            # Could be a message sent outside NotifyFork — not an error
            logger.info("No notification found for email_id", extra={"email_id": email_id})
            return Response({"detail": "unknown message"}, status=status.HTTP_200_OK)

        delivered = event_type in RESEND_DELIVERED_EVENTS
        reason = data.get("reason") if not delivered else None

        process_delivery_update.delay(
            notification_id=str(notification_id),
            provider="resend_email",
            delivered=delivered,
            reason=reason,
        )

        return Response({"detail": "accepted"}, status=status.HTTP_200_OK)

    @staticmethod
    def _validate_signature(request: Request) -> bool:
        secret = getattr(settings, "RESEND_WEBHOOK_SECRET", None)
        if not secret:
            logger.warning("RESEND_WEBHOOK_SECRET not configured — skipping signature validation")
            return True  # dev mode only — never in production

        svix_id = request.META.get("HTTP_SVIX_ID", "")
        svix_timestamp = request.META.get("HTTP_SVIX_TIMESTAMP", "")
        svix_signature = request.META.get("HTTP_SVIX_SIGNATURE", "")

        if not all([svix_id, svix_timestamp, svix_signature]):
            return False

        secret_bytes = base64.b64decode(secret.removeprefix("whsec_"))
        signed_content = f"{svix_id}.{svix_timestamp}.{request.body.decode()}"
        expected = base64.b64encode(
            hmac.new(secret_bytes, signed_content.encode(), hashlib.sha256).digest()
        ).decode()

        # svix-signature can carry multiple "v1,<sig>" pairs (key rotation) — accept any match
        candidates = [part.split(",", 1)[1] for part in svix_signature.split() if "," in part]
        return any(hmac.compare_digest(expected, candidate) for candidate in candidates)

    @staticmethod
    def _find_notification_id(email_id: str) -> str | None:
        """
        Looks up notification by the provider_message_id we stored at send time.
        Single indexed query — provider_message_id should be indexed in production.
        """
        import asyncio
        from notifyfork.core.infrastructure.models.notification_model import NotificationModel

        async def _get():
            try:
                obj = await NotificationModel.objects.aget(provider_message_id=email_id)
                return str(obj.id)
            except NotificationModel.DoesNotExist:
                return None

        return asyncio.get_event_loop().run_until_complete(_get())
