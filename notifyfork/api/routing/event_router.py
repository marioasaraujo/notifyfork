import logging
from dataclasses import dataclass
from enum import Enum

from notifyfork.core.domain.entities.notification import NotificationChannel, NotificationType

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """
    All supported event types.

    Using str + Enum means the value serializes naturally to/from JSON
    and can be compared directly with strings — no .value needed.

    Add a new event here, then add its rule to EVENT_ROUTING_TABLE below.
    That's the only two places that ever need to change.

    Usage:
        EventType.USER_OTP_REQUESTED          # → "user.otp_requested"
        EventType("user.otp_requested")       # works for deserialization
        EventType.USER_OTP_REQUESTED.value    # → "user.otp_requested"
    """

    # User
    USER_OTP_REQUESTED      = "user.otp_requested"
    USER_EMAIL_VERIFICATION = "user.email_verification"

    # Order
    ORDER_CONFIRMED         = "order.confirmed"
    ORDER_SHIPPED           = "order.shipped"
    ORDER_READY_FOR_PICKUP  = "order.ready_for_pickup"

    # Payment
    PAYMENT_FAILED          = "payment.failed"

    # Promotions
    PROMOTION_FLASH_SALE    = "promotion.flash_sale"

    # System / ops alerts
    SYSTEM_ERROR            = "system.error"
    DEPLOY_COMPLETED        = "deploy.completed"
    WORKER_QUEUE_OVERFLOW   = "worker.queue_overflow"


@dataclass(frozen=True)
class RoutingRule:
    """
    Maps an EventType to a channel + template + notification type.
    Immutable — routing rules are never mutated at runtime.
    """
    channel: NotificationChannel
    template_id: str
    notification_type: NotificationType


# Central routing table — one line per event type.
# EventType enum guarantees no typos. RoutingRule guarantees immutability.
EVENT_ROUTING_TABLE: dict[EventType, RoutingRule] = {

    # Transactional
    EventType.USER_OTP_REQUESTED:      RoutingRule(NotificationChannel.SMS,      "otp_sms",            NotificationType.TRANSACTIONAL),
    EventType.USER_EMAIL_VERIFICATION: RoutingRule(NotificationChannel.EMAIL,    "email_verification", NotificationType.TRANSACTIONAL),
    EventType.ORDER_CONFIRMED:         RoutingRule(NotificationChannel.EMAIL,    "order_confirmed",    NotificationType.TRANSACTIONAL),
    EventType.ORDER_SHIPPED:           RoutingRule(NotificationChannel.WHATSAPP, "order_shipped_wa",   NotificationType.TRANSACTIONAL),
    EventType.ORDER_READY_FOR_PICKUP:  RoutingRule(NotificationChannel.PUSH,     "pickup_ready_push",  NotificationType.TRANSACTIONAL),
    EventType.PAYMENT_FAILED:          RoutingRule(NotificationChannel.SMS,      "payment_failed_sms", NotificationType.TRANSACTIONAL),

    # Marketing
    EventType.PROMOTION_FLASH_SALE:    RoutingRule(NotificationChannel.PUSH,     "flash_sale_push",    NotificationType.MARKETING),

    # Ops / alerts
    EventType.SYSTEM_ERROR:            RoutingRule(NotificationChannel.SLACK,    "system_error_slack", NotificationType.ALERT),
    EventType.DEPLOY_COMPLETED:        RoutingRule(NotificationChannel.SLACK,    "deploy_done_slack",  NotificationType.ALERT),
    EventType.WORKER_QUEUE_OVERFLOW:   RoutingRule(NotificationChannel.SLACK,    "queue_overflow",     NotificationType.ALERT),
}


class EventRouter:
    """
    Resolves an EventType to its RoutingRule.

    Single responsibility: knows where events go.
    Does not know how to send anything.
    """

    def resolve(self, event_type: str) -> RoutingRule:
        try:
            parsed = EventType(event_type)
        except ValueError:
            logger.warning("Unknown event type", extra={"event_type": event_type})
            raise UnroutableEvent(event_type)

        rule = EVENT_ROUTING_TABLE[parsed]
        logger.info(
            "Event routed",
            extra={
                "event_type": event_type,
                "channel": rule.channel.value,
                "template_id": rule.template_id,
            },
        )
        return rule


class UnroutableEvent(Exception):
    def __init__(self, event_type: str) -> None:
        valid = [e.value for e in EventType]
        super().__init__(
            f"No routing rule for event: '{event_type}'. "
            f"Valid events: {valid}"
        )
        self.event_type = event_type
