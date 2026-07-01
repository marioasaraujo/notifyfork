"""
Root conftest — fixtures available to the entire test suite.

Shared fixtures live here.
Layer-specific fixtures (e.g. Django mocks) live in their own conftest.py.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from notifyfork.core.application.interfaces.notification_provider import ProviderResult
from notifyfork.core.domain.entities.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from notifyfork.core.domain.value_objects.template import NotificationTemplate


# Domain fixtures

@pytest.fixture
def sms_notification() -> Notification:
    return Notification(
        recipient="+5511999990001",
        channel=NotificationChannel.SMS,
        notification_type=NotificationType.TRANSACTIONAL,
        template_id="otp_sms",
        context={"code": "123456"},
        max_attempts=3,
    )


@pytest.fixture
def email_notification() -> Notification:
    return Notification(
        recipient="user@example.com",
        channel=NotificationChannel.EMAIL,
        notification_type=NotificationType.TRANSACTIONAL,
        template_id="order_confirmed",
        context={"order_id": "ORD-999", "total": "R$ 250,00"},
        max_attempts=3,
    )


@pytest.fixture
def whatsapp_notification() -> Notification:
    return Notification(
        recipient="+5511999990002",
        channel=NotificationChannel.WHATSAPP,
        notification_type=NotificationType.TRANSACTIONAL,
        template_id="order_shipped_wa",
        context={"tracking_code": "BR123456789"},
        max_attempts=3,
    )


@pytest.fixture
def slack_notification() -> Notification:
    return Notification(
        recipient="C012AB3CD",
        channel=NotificationChannel.SLACK,
        notification_type=NotificationType.ALERT,
        template_id="system_error_slack",
        context={"service": "payment-api", "error": "connection timeout"},
        max_attempts=2,
    )


@pytest.fixture
def push_notification() -> Notification:
    return Notification(
        recipient="fcm-device-token-abc123",
        channel=NotificationChannel.PUSH,
        notification_type=NotificationType.MARKETING,
        template_id="flash_sale_push",
        context={"discount": "30%", "expires_in": "2h"},
        max_attempts=3,
    )


# Template fixtures

@pytest.fixture
def otp_template() -> NotificationTemplate:
    return NotificationTemplate(id="otp_sms", body="Your code is: $code")


@pytest.fixture
def email_template() -> NotificationTemplate:
    return NotificationTemplate(
        id="order_confirmed",
        subject="Order $order_id confirmed",
        body="<p>Your order <strong>$order_id</strong> has been confirmed. Total: $total</p>",
    )


@pytest.fixture
def whatsapp_template() -> NotificationTemplate:
    return NotificationTemplate(
        id="order_shipped_wa",
        body="Your order is on the way! Track it: $tracking_code",
    )


@pytest.fixture
def slack_template() -> NotificationTemplate:
    return NotificationTemplate(
        id="system_error_slack",
        subject="🚨 Error in $service",
        body="*Service:* $service\n*Error:* $error",
    )


@pytest.fixture
def push_template() -> NotificationTemplate:
    return NotificationTemplate(
        id="flash_sale_push",
        subject="Flash Sale — $discount OFF",
        body="Hurry! Sale ends in $expires_in",
    )


# Provider mock factories

def make_mock_provider(
    name: str,
    channels: list[NotificationChannel],
    success: bool = True,
    error: str | None = None,
) -> MagicMock:
    provider = MagicMock()
    provider.name = name
    provider.supported_channels = channels
    provider.supports = lambda ch: ch in channels
    provider.send_with_template = AsyncMock(
        return_value=ProviderResult(
            success=success,
            provider_name=name,
            external_id=str(uuid4()) if success else None,
            error=error,
        )
    )
    return provider


@pytest.fixture
def twilio_sms_provider():
    return make_mock_provider("twilio_sms", [NotificationChannel.SMS])


@pytest.fixture
def twilio_whatsapp_provider():
    return make_mock_provider("twilio_whatsapp", [NotificationChannel.WHATSAPP])


@pytest.fixture
def firebase_push_provider():
    return make_mock_provider("firebase_push", [NotificationChannel.PUSH])


@pytest.fixture
def smtp_email_provider():
    return make_mock_provider("smtp_email", [NotificationChannel.EMAIL])


@pytest.fixture
def slack_provider():
    return make_mock_provider("slack", [NotificationChannel.SLACK])


@pytest.fixture
def all_providers(
    twilio_sms_provider,
    twilio_whatsapp_provider,
    firebase_push_provider,
    smtp_email_provider,
    slack_provider,
):
    return [
        twilio_sms_provider,
        twilio_whatsapp_provider,
        firebase_push_provider,
        smtp_email_provider,
        slack_provider,
    ]


# Repository mocks

@pytest.fixture
def mock_notification_repository():
    repo = AsyncMock()
    repo.save = AsyncMock(return_value=None)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_pending_retries = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_template_repository(
    otp_template,
    email_template,
    whatsapp_template,
    slack_template,
    push_template,
):
    templates = {
        otp_template.id: otp_template,
        email_template.id: email_template,
        whatsapp_template.id: whatsapp_template,
        slack_template.id: slack_template,
        push_template.id: push_template,
    }

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(side_effect=lambda tid: templates.get(tid))
    return repo


# External template fixtures

@pytest.fixture
def whatsapp_external_template():
    from notifyfork.core.domain.value_objects.template import TemplateMode, VariableMapping
    return NotificationTemplate(
        id="wa_otp_external",
        body="HXabc123def456",
        mode=TemplateMode.EXTERNAL,
        variable_mapping=VariableMapping({"name": "1", "code": "2"}),
    )


@pytest.fixture
def sendgrid_external_template():
    from notifyfork.core.domain.value_objects.template import TemplateMode, VariableMapping
    return NotificationTemplate(
        id="order_sendgrid",
        body="d-abc123def456",
        mode=TemplateMode.EXTERNAL,
        variable_mapping=VariableMapping({
            "order_id": "order_id",
            "total": "order_total",
            "name": "customer_name",
        }),
    )
