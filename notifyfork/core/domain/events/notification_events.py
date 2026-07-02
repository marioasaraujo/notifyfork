from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


@dataclass(frozen=True)
class NotificationQueued:
    notification_id: UUID
    channel: str
    recipient: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class NotificationSent:
    notification_id: UUID
    provider: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class NotificationFailed:
    notification_id: UUID
    reason: str
    attempts: int
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
