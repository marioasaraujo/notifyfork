import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from notifyfork.core.application.interfaces.notification_provider import NotificationProvider, ProviderResult
from notifyfork.core.domain.entities.notification import NotificationChannel
from notifyfork.core.domain.value_objects.template import NotificationTemplate

logger = logging.getLogger(__name__)


class SMTPEmailProvider(NotificationProvider):
    """
    Generic SMTP email provider — renders templates locally.

    Always LOCAL mode. Body is HTML rendered here before sending.
    For external template rendering (SendGrid, Mailgun), use their
    dedicated providers instead.
    """

    def __init__(self, host: str, port: int, username: str, password: str, from_email: str) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from_email = from_email

    @property
    def name(self) -> str:
        return "smtp_email"

    @property
    def supported_channels(self) -> list[NotificationChannel]:
        return [NotificationChannel.EMAIL]

    async def send_with_template(
        self,
        recipient: str,
        template: NotificationTemplate,
        context: dict[str, Any],
    ) -> ProviderResult:
        body = template.render(context)
        subject = template.render_subject(context) or "(no subject)"

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self._from_email
            msg["To"] = recipient
            msg.attach(MIMEText(body, "html"))

            with smtplib.SMTP_SSL(self._host, self._port) as server:
                server.login(self._username, self._password)
                server.sendmail(self._from_email, recipient, msg.as_string())

            logger.info("Email sent via SMTP", extra={"to": recipient, "subject": subject})
            return ProviderResult(success=True, provider_name=self.name)

        except smtplib.SMTPException as e:
            logger.error("SMTP error", extra={"error": str(e)})
            return ProviderResult(success=False, provider_name=self.name, error=str(e))
