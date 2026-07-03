import logging
from typing import Any

import firebase_admin
from firebase_admin import credentials, messaging
from firebase_admin.exceptions import FirebaseError

from notifyfork.core.application.interfaces.notification_provider import NotificationProvider, ProviderResult
from notifyfork.core.domain.entities.notification import NotificationChannel
from notifyfork.core.domain.value_objects.template import NotificationTemplate

logger = logging.getLogger(__name__)


class FirebasePushProvider(NotificationProvider):
    """
    Firebase Cloud Messaging provider for push notifications.

    Recipient is expected to be a valid FCM device token.
    """

    def __init__(self, credentials_path: str) -> None:
        # firebase_admin raises if initialize_app() is called twice on the
        # default app — guard against that when multiple Container instances
        # (or test re-imports) build a provider against the same process.
        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app(credentials.Certificate(credentials_path))

    @property
    def name(self) -> str:
        return "firebase_push"

    @property
    def supported_channels(self) -> list[NotificationChannel]:
        # "push" — generic, eligible for fallback if another push provider is
        # registered. "firebase_push" (== self.name) — pins this exact vendor.
        return [NotificationChannel.PUSH, self.name]

    async def send_with_template(
        self,
        recipient: str,
        template: NotificationTemplate,
        context: dict[str, Any],
    ) -> ProviderResult:
        body = template.render(context)
        subject = template.render_subject(context)
        return await self.send(recipient=recipient, body=body, subject=subject)

    async def send(
        self,
        recipient: str,
        body: str,
        subject: str | None = None,
        **kwargs,
    ) -> ProviderResult:
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=subject or "Notification",
                    body=body,
                ),
                token=recipient,
            )
            response = messaging.send(message)
            return ProviderResult(
                success=True,
                provider_name=self.name,
                external_id=response,
            )
        except FirebaseError as e:
            logger.error("Firebase error", extra={"error": str(e)})
            return ProviderResult(
                success=False,
                provider_name=self.name,
                error=str(e),
            )
