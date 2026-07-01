"""
Dependency container for NotifyFork.

Reads environment variables and wires everything together.
One place to look when adding a new provider or changing config.

Usage:
    from notifyfork.core.infrastructure.container.providers import Container

    use_case = Container.send_notification_use_case()
    await use_case.execute(dto)
"""
import os
import logging
from functools import lru_cache

from notifyfork.core.application.interfaces.notification_provider import NotificationProvider
from notifyfork.core.application.use_cases.send_notification import SendNotificationUseCase
from notifyfork.core.infrastructure.repositories.notification_repository import DjangoNotificationRepository
from notifyfork.core.infrastructure.repositories.template_repository import DatabaseTemplateRepository

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER_ORDER = [
    "twilio_sms",
    "twilio_whatsapp",
    "sendgrid_email",
    "resend_email",
    "smtp_email",
    "firebase_push",
    "slack",
]


def _ordered(providers: list[NotificationProvider]) -> list[NotificationProvider]:
    """
    Orders providers for fallback. When more than one provider supports the
    same channel (e.g. SendGrid + SMTP for email), SendNotificationUseCase
    tries them in this order — first one that succeeds wins.

    Override with NOTIFYFORK_PROVIDER_ORDER="sendgrid_email,smtp_email"
    (comma-separated provider names). Anything registered but not listed
    keeps its default position, appended after the ones you did list.
    """
    raw = os.environ.get("NOTIFYFORK_PROVIDER_ORDER")
    order = [name.strip() for name in raw.split(",")] if raw else DEFAULT_PROVIDER_ORDER

    by_name = {p.name: p for p in providers}
    ordered = [by_name[name] for name in order if name in by_name]
    remaining = [p for p in providers if p.name not in order]
    return ordered + remaining


def _build_providers() -> list[NotificationProvider]:
    """
    Instantiates only the providers that have credentials configured.
    Missing credentials → provider is skipped with a warning.
    This lets you run locally with only the providers you need.
    """
    providers = []

    # Twilio SMS
    twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")
    twilio_from = os.environ.get("TWILIO_FROM_NUMBER")

    if all([twilio_sid, twilio_token, twilio_from]):
        from notifyfork.core.infrastructure.providers.twilio_provider import TwilioSMSProvider
        providers.append(TwilioSMSProvider(twilio_sid, twilio_token, twilio_from))
        logger.info("Provider registered: twilio_sms")
    else:
        logger.warning("twilio_sms skipped — missing TWILIO_ACCOUNT_SID / AUTH_TOKEN / FROM_NUMBER")

    # Twilio WhatsApp
    twilio_wa_from = os.environ.get("TWILIO_WHATSAPP_FROM_NUMBER")

    if all([twilio_sid, twilio_token, twilio_wa_from]):
        from notifyfork.core.infrastructure.providers.whatsapp_provider import TwilioWhatsAppProvider
        providers.append(TwilioWhatsAppProvider(twilio_sid, twilio_token, twilio_wa_from))
        logger.info("Provider registered: twilio_whatsapp")
    else:
        logger.warning("twilio_whatsapp skipped — missing TWILIO_WHATSAPP_FROM_NUMBER")

    # SendGrid Email
    sendgrid_key = os.environ.get("SENDGRID_API_KEY")
    sendgrid_from = os.environ.get("SENDGRID_FROM_EMAIL")
    sendgrid_name = os.environ.get("SENDGRID_FROM_NAME", "NotifyFork")

    if all([sendgrid_key, sendgrid_from]):
        from notifyfork.core.infrastructure.providers.sendgrid_provider import SendGridEmailProvider
        providers.append(SendGridEmailProvider(sendgrid_key, sendgrid_from, sendgrid_name))
        logger.info("Provider registered: sendgrid_email")
    else:
        logger.warning("sendgrid_email skipped — missing SENDGRID_API_KEY / FROM_EMAIL")

    # Resend Email
    resend_key = os.environ.get("RESEND_API_KEY")
    resend_from = os.environ.get("RESEND_FROM_EMAIL")
    resend_name = os.environ.get("RESEND_FROM_NAME", "")

    if all([resend_key, resend_from]):
        from notifyfork.core.infrastructure.providers.resend_provider import ResendEmailProvider
        providers.append(ResendEmailProvider(resend_key, resend_from, resend_name))
        logger.info("Provider registered: resend_email")
    else:
        logger.warning("resend_email skipped — missing RESEND_API_KEY / FROM_EMAIL")

    # SMTP Email (fallback)
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_user = os.environ.get("SMTP_USERNAME")
    smtp_pass = os.environ.get("SMTP_PASSWORD")
    smtp_from = os.environ.get("SMTP_FROM_EMAIL")

    if all([smtp_host, smtp_user, smtp_pass, smtp_from]):
        from notifyfork.core.infrastructure.providers.smtp_provider import SMTPEmailProvider
        providers.append(SMTPEmailProvider(
            host=smtp_host,
            port=int(os.environ.get("SMTP_PORT", "465")),
            username=smtp_user,
            password=smtp_pass,
            from_email=smtp_from,
        ))
        logger.info("Provider registered: smtp_email")
    else:
        logger.warning("smtp_email skipped — missing SMTP_HOST / USERNAME / PASSWORD / FROM_EMAIL")

    # Firebase Push
    firebase_creds = os.environ.get("FIREBASE_CREDENTIALS_PATH")

    if firebase_creds:
        from notifyfork.core.infrastructure.providers.firebase_provider import FirebasePushProvider
        providers.append(FirebasePushProvider())
        logger.info("Provider registered: firebase_push")
    else:
        logger.warning("firebase_push skipped — missing FIREBASE_CREDENTIALS_PATH")

    # Slack
    slack_token = os.environ.get("SLACK_BOT_TOKEN")

    if slack_token:
        from notifyfork.core.infrastructure.providers.slack_provider import SlackProvider
        providers.append(SlackProvider(bot_token=slack_token))
        logger.info("Provider registered: slack")
    else:
        logger.warning("slack skipped — missing SLACK_BOT_TOKEN")

    if not providers:
        logger.error("No providers registered — check your environment variables")

    return _ordered(providers)


class Container:
    """
    Simple service locator. Not a full DI framework on purpose —
    keeps the dependency graph explicit and easy to follow.
    """

    @staticmethod
    @lru_cache(maxsize=1)
    def providers() -> list[NotificationProvider]:
        return _build_providers()

    @staticmethod
    def notification_repository() -> DjangoNotificationRepository:
        return DjangoNotificationRepository()

    @staticmethod
    def template_repository() -> DatabaseTemplateRepository:
        return DatabaseTemplateRepository()

    @staticmethod
    def send_notification_use_case() -> SendNotificationUseCase:
        return SendNotificationUseCase(
            repository=Container.notification_repository(),
            template_repository=Container.template_repository(),
            providers=Container.providers(),
        )
