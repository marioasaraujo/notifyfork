import logging
from typing import Any

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from notifyfork.core.application.interfaces.notification_provider import NotificationProvider, ProviderResult
from notifyfork.core.domain.entities.notification import NotificationChannel
from notifyfork.core.domain.value_objects.template import NotificationTemplate, TemplateMode

logger = logging.getLogger(__name__)


class TwilioWhatsAppProvider(NotificationProvider):
    """
    WhatsApp via Twilio.

    LOCAL mode — sandbox/dev only. Sends free-form text.
    EXTERNAL mode — production. Uses Meta-approved template SID + mapped variables.

    Twilio WhatsApp external templates use positional variables: "1", "2", "3"...
    Use VariableMapping to translate your semantic context to positional keys:

        VariableMapping({"name": "1", "code": "2"})

    So context {"name": "Mario", "code": "847291"} becomes {"1": "Mario", "2": "847291"}
    which is what Twilio's ContentTemplate API expects.
    """

    def __init__(self, account_sid: str, auth_token: str, from_number: str) -> None:
        self._client = Client(account_sid, auth_token)
        self._from_number = (
            from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"
        )

    @property
    def name(self) -> str:
        return "twilio_whatsapp"

    @property
    def supported_channels(self) -> list[NotificationChannel]:
        return [NotificationChannel.WHATSAPP]

    async def send_with_template(
        self,
        recipient: str,
        template: NotificationTemplate,
        context: dict[str, Any],
    ) -> ProviderResult:
        to = recipient if recipient.startswith("whatsapp:") else f"whatsapp:{recipient}"

        if template.mode == TemplateMode.EXTERNAL:
            return await self._send_external(to, template, context)
        return await self._send_local(to, template, context)

    async def _send_external(
        self,
        to: str,
        template: NotificationTemplate,
        context: dict[str, Any],
    ) -> ProviderResult:
        """
        Sends using a Meta-approved Twilio Content Template.
        Variables are translated via VariableMapping before dispatch.
        """
        translated = template.translate_variables(context)

        logger.info(
            "Sending WhatsApp via external template",
            extra={
                "template_sid": template.external_template_id,
                "to": to[:12] + "***",
                "variables": list(translated.keys()),
            },
        )

        try:
            message = self._client.messages.create(
                content_sid=template.external_template_id,
                content_variables=str(translated),  # Twilio expects JSON string
                from_=self._from_number,
                to=to,
            )
            return ProviderResult(
                success=True, provider_name=self.name, external_id=message.sid
            )
        except TwilioRestException as e:
            logger.error("WhatsApp external template error", extra={"code": e.code, "msg": e.msg})
            return ProviderResult(
                success=False,
                provider_name=self.name,
                error=f"Twilio WhatsApp [{e.code}]: {e.msg}",
            )

    async def _send_local(
        self,
        to: str,
        template: NotificationTemplate,
        context: dict[str, Any],
    ) -> ProviderResult:
        """Free-form message — only valid in sandbox/dev."""
        body = template.render(context)
        try:
            message = self._client.messages.create(body=body, from_=self._from_number, to=to)
            return ProviderResult(
                success=True, provider_name=self.name, external_id=message.sid
            )
        except TwilioRestException as e:
            return ProviderResult(
                success=False,
                provider_name=self.name,
                error=f"Twilio WhatsApp [{e.code}]: {e.msg}",
            )
