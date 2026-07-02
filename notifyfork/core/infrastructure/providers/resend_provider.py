import logging
import httpx
from typing import Any

from notifyfork.core.application.interfaces.notification_provider import NotificationProvider, ProviderResult
from notifyfork.core.domain.entities.notification import NotificationChannel
from notifyfork.core.domain.value_objects.template import NotificationTemplate

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


class ResendEmailProvider(NotificationProvider):
    """
    Resend email provider.

    LOCAL mode only — renders body locally, sends as raw HTML. Resend
    doesn't have a server-side dynamic template system like SendGrid; if
    you need EXTERNAL mode, use SendGridEmailProvider instead.
    """

    def __init__(self, api_key: str, from_email: str, from_name: str = "") -> None:
        self._api_key = api_key
        self._from_email = from_email
        self._from_name = from_name

    @property
    def name(self) -> str:
        return "resend_email"

    @property
    def supported_channels(self) -> list[NotificationChannel]:
        # "email" — generic, eligible for fallback to sendgrid_email/smtp_email.
        # "resend_email" (== self.name) — pins this exact vendor.
        return [NotificationChannel.EMAIL, self.name]

    async def send_with_template(
        self,
        recipient: str,
        template: NotificationTemplate,
        context: dict[str, Any],
    ) -> ProviderResult:
        body = template.render(context)
        subject = template.render_subject(context) or "(no subject)"
        sender = f"{self._from_name} <{self._from_email}>" if self._from_name else self._from_email

        payload = {
            "from": sender,
            "to": [recipient],
            "subject": subject,
            "html": body,
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    RESEND_API_URL,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

            if response.status_code in (200, 201):
                message_id = response.json().get("id")
                logger.info("Email sent via Resend", extra={"message_id": message_id})
                return ProviderResult(success=True, provider_name=self.name, external_id=message_id)

            logger.error(
                "Resend error",
                extra={"status": response.status_code, "body": response.text},
            )
            return ProviderResult(
                success=False,
                provider_name=self.name,
                error=f"Resend [{response.status_code}]: {response.text}",
            )

        except httpx.HTTPError as e:
            logger.error("Resend HTTP error", extra={"error": str(e)})
            return ProviderResult(success=False, provider_name=self.name, error=str(e))
