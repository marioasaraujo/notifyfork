import logging
import httpx
from typing import Any

from notifyfork.core.application.interfaces.notification_provider import NotificationProvider, ProviderResult
from notifyfork.core.domain.entities.notification import NotificationChannel
from notifyfork.core.domain.value_objects.template import NotificationTemplate, TemplateMode

logger = logging.getLogger(__name__)

SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"


class SendGridEmailProvider(NotificationProvider):
    """
    SendGrid email provider.

    LOCAL mode  — renders body locally, sends as raw HTML.
    EXTERNAL mode — uses a SendGrid Dynamic Template (d-xxxx).
                    Variables are translated via VariableMapping
                    and sent as `dynamic_template_data`.

    SendGrid Dynamic Templates use Handlebars: {{name}}, {{order_id}}
    Your context keys must match the template's variable names,
    or use VariableMapping to translate them.

    Example:
        template = NotificationTemplate(
            id="order_confirmed",
            body="d-abc123def456",           # SendGrid template ID
            mode=TemplateMode.EXTERNAL,
            variable_mapping=VariableMapping({
                "order_id": "order_id",       # same name — pass through
                "total": "order_total",       # renamed to match SendGrid template
                "name": "customer_name",
            })
        )
        # context: {"order_id": "ORD-1", "total": "R$100", "name": "Mario"}
        # sent to SendGrid as: {"order_id": "ORD-1", "order_total": "R$100", "customer_name": "Mario"}
    """

    def __init__(self, api_key: str, from_email: str, from_name: str = "") -> None:
        self._api_key = api_key
        self._from_email = from_email
        self._from_name = from_name

    @property
    def name(self) -> str:
        return "sendgrid_email"

    @property
    def supported_channels(self) -> list[NotificationChannel]:
        return [NotificationChannel.EMAIL]

    async def send_with_template(
        self,
        recipient: str,
        template: NotificationTemplate,
        context: dict[str, Any],
    ) -> ProviderResult:
        if template.mode == TemplateMode.EXTERNAL:
            return await self._send_external(recipient, template, context)
        return await self._send_local(recipient, template, context)

    async def _send_external(
        self,
        recipient: str,
        template: NotificationTemplate,
        context: dict[str, Any],
    ) -> ProviderResult:
        """Uses a SendGrid Dynamic Template with Handlebars variables."""
        translated = template.translate_variables(context)

        payload = {
            "from": {"email": self._from_email, "name": self._from_name},
            "personalizations": [
                {
                    "to": [{"email": recipient}],
                    "dynamic_template_data": translated,
                }
            ],
            "template_id": template.external_template_id,
        }

        logger.info(
            "Sending email via SendGrid external template",
            extra={
                "template_id": template.external_template_id,
                "to": recipient,
                "variables": list(translated.keys()),
            },
        )

        return await self._post(payload)

    async def _send_local(
        self,
        recipient: str,
        template: NotificationTemplate,
        context: dict[str, Any],
    ) -> ProviderResult:
        """Renders HTML locally, sends as raw content."""
        body = template.render(context)
        subject = template.render_subject(context) or "(no subject)"

        payload = {
            "from": {"email": self._from_email, "name": self._from_name},
            "personalizations": [{"to": [{"email": recipient}]}],
            "subject": subject,
            "content": [{"type": "text/html", "value": body}],
        }

        return await self._post(payload)

    async def _post(self, payload: dict) -> ProviderResult:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    SENDGRID_API_URL,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

            # SendGrid returns 202 on success, no body
            if response.status_code == 202:
                message_id = response.headers.get("X-Message-Id")
                logger.info("Email sent via SendGrid", extra={"message_id": message_id})
                return ProviderResult(
                    success=True, provider_name=self.name, external_id=message_id
                )

            logger.error(
                "SendGrid error",
                extra={"status": response.status_code, "body": response.text},
            )
            return ProviderResult(
                success=False,
                provider_name=self.name,
                error=f"SendGrid [{response.status_code}]: {response.text}",
            )

        except httpx.HTTPError as e:
            logger.error("SendGrid HTTP error", extra={"error": str(e)})
            return ProviderResult(success=False, provider_name=self.name, error=str(e))
