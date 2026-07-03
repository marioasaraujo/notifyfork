import dataclasses
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from notifyfork.core.domain.events.notification_events import (
    NotificationFailed,
    NotificationQueued,
    NotificationSent,
)


class TestNotificationQueued:
    def test_holds_fields(self):
        notification_id = uuid4()
        event = NotificationQueued(notification_id=notification_id, channel="sms", recipient="+5511999999999")

        assert event.notification_id == notification_id
        assert event.channel == "sms"
        assert event.recipient == "+5511999999999"

    def test_defaults_occurred_at_to_now_utc(self):
        event = NotificationQueued(notification_id=uuid4(), channel="sms", recipient="+5511999999999")

        assert event.occurred_at.tzinfo == timezone.utc
        assert event.occurred_at <= datetime.now(timezone.utc)

    def test_is_frozen(self):
        event = NotificationQueued(notification_id=uuid4(), channel="sms", recipient="+5511999999999")

        with pytest.raises(dataclasses.FrozenInstanceError):
            event.channel = "email"


class TestNotificationSent:
    def test_holds_fields(self):
        notification_id = uuid4()
        event = NotificationSent(notification_id=notification_id, provider="twilio_sms")

        assert event.notification_id == notification_id
        assert event.provider == "twilio_sms"
        assert event.occurred_at.tzinfo == timezone.utc


class TestNotificationFailed:
    def test_holds_fields(self):
        notification_id = uuid4()
        event = NotificationFailed(
            notification_id=notification_id, reason="timeout", attempts=3
        )

        assert event.notification_id == notification_id
        assert event.reason == "timeout"
        assert event.attempts == 3
        assert event.occurred_at.tzinfo == timezone.utc
