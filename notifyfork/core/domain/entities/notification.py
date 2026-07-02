from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4
import logging

logger = logging.getLogger(__name__)


class NotificationStatus(str, Enum):
    PENDING          = "pending"
    QUEUED           = "queued"
    SENT             = "sent"          # provider accepted — not yet confirmed delivered
    DELIVERED        = "delivered"     # provider confirmed delivery to recipient
    DELIVERY_FAILED  = "delivery_failed"  # provider confirmed it could NOT deliver
    FAILED           = "failed"        # our system exhausted all retry attempts
    RETRYING         = "retrying"


class NotificationChannel(str, Enum):
    SMS       = "sms"
    EMAIL     = "email"
    PUSH      = "push"
    WHATSAPP  = "whatsapp"
    SLACK     = "slack"


class NotificationType(str, Enum):
    TRANSACTIONAL = "transactional"
    ALERT         = "alert"
    MARKETING     = "marketing"


@dataclass
class Notification:
    """
    Core domain entity. Owns its own state machine.

    State flow:
        PENDING → QUEUED → SENT ──────────────→ DELIVERED        (confirmed by provider webhook)
                               ↘ RETRYING →  ↗                   (retry succeeded)
                                           → DELIVERY_FAILED      (provider confirmed failure)
                               → FAILED                           (our retries exhausted)

    SENT means "provider accepted" — not "recipient got it".
    DELIVERED means the provider webhook confirmed actual delivery.
    DELIVERY_FAILED means the provider confirmed it could not deliver
    (bad number, full inbox, uninstalled app, etc).
    """

    recipient: str
    channel: str
    notification_type: str
    template_id: str
    context: dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    status: NotificationStatus = field(default=NotificationStatus.PENDING)
    provider_used: str | None = None
    provider_message_id: str | None = None   # external ID for webhook correlation
    attempts: int = 0
    max_attempts: int = 3
    error_detail: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: datetime | None = None
    delivered_at: datetime | None = None

    def mark_queued(self) -> None:
        logger.info("Notification queued", extra={
            "notification_id": str(self.id), "channel": self.channel,
        })
        self.status = NotificationStatus.QUEUED

    def mark_sent(self, provider: str, provider_message_id: str | None = None) -> None:
        self.status = NotificationStatus.SENT
        self.provider_used = provider
        self.provider_message_id = provider_message_id
        self.sent_at = datetime.now(timezone.utc)
        logger.info("Notification sent — awaiting delivery confirmation", extra={
            "notification_id": str(self.id),
            "provider": provider,
            "provider_message_id": provider_message_id,
            "channel": self.channel,
        })

    def mark_delivered(self) -> None:
        """Called when provider webhook confirms delivery to recipient."""
        if self.status != NotificationStatus.SENT:
            logger.warning("mark_delivered called on non-SENT notification", extra={
                "notification_id": str(self.id), "current_status": self.status,
            })
        self.status = NotificationStatus.DELIVERED
        self.delivered_at = datetime.now(timezone.utc)
        logger.info("Notification delivered", extra={
            "notification_id": str(self.id),
            "provider": self.provider_used,
            "latency_ms": int((self.delivered_at - self.sent_at).total_seconds() * 1000)
            if self.sent_at else None,
        })

    def mark_delivery_failed(self, reason: str) -> None:
        """Called when provider webhook confirms it could NOT deliver."""
        self.status = NotificationStatus.DELIVERY_FAILED
        self.error_detail = reason
        logger.error("Delivery failed (provider confirmed)", extra={
            "notification_id": str(self.id),
            "provider": self.provider_used,
            "reason": reason,
        })

    def mark_failed(self, reason: str) -> None:
        """Called when our retry logic gives up."""
        self.attempts += 1
        self.error_detail = reason
        if self.attempts >= self.max_attempts:
            self.status = NotificationStatus.FAILED
            logger.error("Notification permanently failed", extra={
                "notification_id": str(self.id),
                "attempts": self.attempts,
                "reason": reason,
            })
        else:
            self.status = NotificationStatus.RETRYING
            logger.warning("Notification failed, will retry", extra={
                "notification_id": str(self.id),
                "attempt": self.attempts,
                "max_attempts": self.max_attempts,
                "reason": reason,
            })

    @property
    def can_retry(self) -> bool:
        return self.attempts < self.max_attempts

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            NotificationStatus.DELIVERED,
            NotificationStatus.DELIVERY_FAILED,
            NotificationStatus.FAILED,
        )
