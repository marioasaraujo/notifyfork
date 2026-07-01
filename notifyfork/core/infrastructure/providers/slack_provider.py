import logging
from typing import Any
import httpx

from notifyfork.core.application.interfaces.notification_provider import NotificationProvider, ProviderResult
from notifyfork.core.domain.entities.notification import NotificationChannel
from notifyfork.core.domain.value_objects.template import NotificationTemplate

logger = logging.getLogger(__name__)

SLACK_API_URL = "https://slack.com/api/chat.postMessage"


class SlackProvider(NotificationProvider):
    """
    Slack provider via Web API.

    Recipient is a Slack channel ID or user ID (e.g. C012AB3CD, U012AB3CD).
    Bot token must have chat:write scope.

    Use for: internal alerts, ops notifications, system events.
    Not for end-user transactional messages.
    """

    def __init__(self, bot_token: str) -> None:
        self._token = bot_token

    @property
    def name(self) -> str:
        return "slack"

    @property
    def supported_channels(self) -> list[NotificationChannel]:
        return [NotificationChannel.SLACK]

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
        payload = {
            "channel": recipient,
            "text": body,
        }

        # Optional: rich block format when subject is provided
        if subject:
            payload["blocks"] = [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": subject},
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": body},
                },
            ]

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    SLACK_API_URL,
                    headers={"Authorization": f"Bearer {self._token}"},
                    json=payload,
                )
                data = response.json()

            if not data.get("ok"):
                error = data.get("error", "unknown_error")
                logger.error("Slack API error", extra={"error": error, "channel": recipient})
                return ProviderResult(
                    success=False,
                    provider_name=self.name,
                    error=f"Slack error: {error}",
                )

            logger.info(
                "Slack message sent",
                extra={"channel": recipient, "ts": data.get("ts")},
            )
            return ProviderResult(
                success=True,
                provider_name=self.name,
                external_id=data.get("ts"),
            )

        except httpx.HTTPError as e:
            logger.error("Slack HTTP error", extra={"error": str(e)})
            return ProviderResult(
                success=False,
                provider_name=self.name,
                error=f"HTTP error: {str(e)}",
            )
