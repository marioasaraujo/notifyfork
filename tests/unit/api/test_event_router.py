import pytest
from notifyfork.api.routing.event_router import EventRouter, EventType, UnroutableEvent
from notifyfork.core.domain.entities.notification import NotificationChannel, NotificationType


@pytest.fixture
def router():
    return EventRouter()


class TestEventType:
    def test_enum_values_are_dot_notation(self):
        assert EventType.USER_OTP_REQUESTED.value == "user.otp_requested"
        assert EventType.SYSTEM_ERROR.value == "system.error"

    def test_enum_can_be_parsed_from_string(self):
        assert EventType("user.otp_requested") == EventType.USER_OTP_REQUESTED

    def test_enum_raises_on_unknown_value(self):
        with pytest.raises(ValueError):
            EventType("nonexistent.event")

    def test_all_event_types_are_in_routing_table(self):
        from notifyfork.api.routing.event_router import EVENT_ROUTING_TABLE
        for event_type in EventType:
            assert event_type in EVENT_ROUTING_TABLE, (
                f"{event_type.name} is defined in EventType but missing from EVENT_ROUTING_TABLE"
            )


class TestEventRouter:
    def test_otp_routes_to_sms(self, router):
        rule = router.resolve(EventType.USER_OTP_REQUESTED.value)
        assert rule.channel == NotificationChannel.SMS
        assert rule.template_id == "otp_sms"
        assert rule.notification_type == NotificationType.TRANSACTIONAL

    def test_order_confirmed_routes_to_email(self, router):
        rule = router.resolve(EventType.ORDER_CONFIRMED.value)
        assert rule.channel == NotificationChannel.EMAIL

    def test_order_shipped_routes_to_whatsapp(self, router):
        rule = router.resolve(EventType.ORDER_SHIPPED.value)
        assert rule.channel == NotificationChannel.WHATSAPP

    def test_system_error_routes_to_slack(self, router):
        rule = router.resolve(EventType.SYSTEM_ERROR.value)
        assert rule.channel == NotificationChannel.SLACK
        assert rule.notification_type == NotificationType.ALERT

    def test_flash_sale_routes_to_push(self, router):
        rule = router.resolve(EventType.PROMOTION_FLASH_SALE.value)
        assert rule.channel == NotificationChannel.PUSH
        assert rule.notification_type == NotificationType.MARKETING

    def test_unknown_event_raises_unroutable(self, router):
        with pytest.raises(UnroutableEvent) as exc_info:
            router.resolve("totally.unknown.event")
        assert "totally.unknown.event" in str(exc_info.value)

    def test_unroutable_error_lists_valid_events(self, router):
        """Error message should tell the caller what valid values are."""
        with pytest.raises(UnroutableEvent) as exc_info:
            router.resolve("ghost.event")
        assert "user.otp_requested" in str(exc_info.value)

    def test_all_rules_have_valid_channels(self, router):
        from notifyfork.api.routing.event_router import EVENT_ROUTING_TABLE
        valid_channels = set(NotificationChannel)
        for event, rule in EVENT_ROUTING_TABLE.items():
            assert rule.channel in valid_channels, f"{event} has invalid channel"

    def test_all_rules_have_non_empty_template_id(self, router):
        from notifyfork.api.routing.event_router import EVENT_ROUTING_TABLE
        for event, rule in EVENT_ROUTING_TABLE.items():
            assert rule.template_id, f"{event} has empty template_id"

    def test_resolve_accepts_string_value(self, router):
        """resolve() takes strings so Django views don't need to import EventType."""
        rule = router.resolve("user.otp_requested")
        assert rule.channel == NotificationChannel.SMS
