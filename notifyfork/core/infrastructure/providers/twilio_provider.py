import logging
from typing import Any

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from notifyfork.core.application.interfaces.notification_provider import NotificationProvider, ProviderResult
from notifyfork.core.domain.entities.notification import NotificationChannel
from notifyfork.core.domain.value_objects.template import NotificationTemplate, TemplateMode

logger = logging.getLogger(__name__)


class TwilioSMSProvider(NotificationProvider):
    """
    Twilio SMS provider.

    LOCAL mode  — sends free-form text. Body is rendered locally.
    EXTERNAL mode — not applicable for SMS (no template system).
    """

    def __init__(self, account_sid: str, auth_token: str, from_number: str) -> None:
        self._client = Client(account_sid, auth_token)
        self._from_number = from_number

    @property
    def name(self) -> str:
        return "twilio_sms"

    @property
    def supported_channels(self) -> list[NotificationChannel]:
        # "sms" — generic, eligible for fallback if another SMS provider is
        # registered. "twilio_sms" (== self.name) — pins this exact vendor.
        return [NotificationChannel.SMS, self.name]

    async def send_with_template(
        self,
        recipient: str,
        template: NotificationTemplate,
        context: dict[str, Any],
    ) -> ProviderResult:
        body = template.render(context)

        try:
            message = self._client.messages.create(
                body=body,
                from_=self._from_number,
                to=recipient,
            )
            logger.info("SMS sent", extra={"sid": message.sid, "to": recipient[:6] + "***"})
            return ProviderResult(success=True, provider_name=self.name, external_id=message.sid)

        except TwilioRestException as e:
            logger.error("Twilio SMS error", extra={"code": e.code, "twilio_message": e.msg})
            return ProviderResult(
                success=False, provider_name=self.name, error=f"Twilio [{e.code}]: {e.msg}"
            )
