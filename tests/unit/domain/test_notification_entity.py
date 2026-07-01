import pytest
from notifyfork.core.domain.entities.notification import Notification, NotificationStatus


class TestNotificationLifecycle:
    def test_initial_status_is_pending(self, sms_notification):
        assert sms_notification.status == NotificationStatus.PENDING

    def test_mark_queued(self, sms_notification):
        sms_notification.mark_queued()
        assert sms_notification.status == NotificationStatus.QUEUED

    def test_mark_sent_sets_provider_and_timestamp(self, sms_notification):
        sms_notification.mark_sent("twilio_sms")
        assert sms_notification.status == NotificationStatus.SENT
        assert sms_notification.provider_used == "twilio_sms"
        assert sms_notification.sent_at is not None

    def test_first_failure_transitions_to_retrying(self, sms_notification):
        sms_notification.mark_failed("timeout")
        assert sms_notification.status == NotificationStatus.RETRYING
        assert sms_notification.attempts == 1
        assert sms_notification.can_retry is True

    def test_exhausted_attempts_transitions_to_failed(self, sms_notification):
        for _ in range(sms_notification.max_attempts):
            sms_notification.mark_failed("timeout")
        assert sms_notification.status == NotificationStatus.FAILED
        assert sms_notification.can_retry is False

    def test_is_not_terminal_when_sent(self, sms_notification):
        # SENT means the provider accepted it, not that it was delivered —
        # only a webhook confirming DELIVERED/DELIVERY_FAILED makes it terminal.
        sms_notification.mark_sent("twilio_sms")
        assert sms_notification.is_terminal is False

    def test_is_terminal_when_permanently_failed(self, sms_notification):
        for _ in range(sms_notification.max_attempts):
            sms_notification.mark_failed("error")
        assert sms_notification.is_terminal is True

    def test_not_terminal_when_retrying(self, sms_notification):
        sms_notification.mark_failed("error")  # attempt 1 of 3
        assert sms_notification.is_terminal is False

    def test_error_detail_recorded_on_failure(self, sms_notification):
        sms_notification.mark_failed("connection refused")
        assert sms_notification.error_detail == "connection refused"

    def test_attempts_increment_each_failure(self, sms_notification):
        sms_notification.mark_failed("e1")
        sms_notification.mark_failed("e2")
        assert sms_notification.attempts == 2

    def test_slack_notification_alert_type(self, slack_notification):
        from notifyfork.core.domain.entities.notification import NotificationType
        assert slack_notification.notification_type == NotificationType.ALERT

    def test_whatsapp_notification_channel(self, whatsapp_notification):
        from notifyfork.core.domain.entities.notification import NotificationChannel
        assert whatsapp_notification.channel == NotificationChannel.WHATSAPP
