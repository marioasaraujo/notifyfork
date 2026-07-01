from typing import Any
from pydantic import BaseModel, field_validator
from notifyfork.core.domain.entities.notification import NotificationChannel, NotificationType


class SendNotificationDTO(BaseModel):
    recipient: str
    channel: NotificationChannel
    notification_type: NotificationType
    template_id: str
    context: dict[str, Any] = {}
    max_attempts: int = 3

    @field_validator("recipient")
    @classmethod
    def recipient_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Recipient cannot be empty")
        return v.strip()

    @field_validator("max_attempts")
    @classmethod
    def valid_attempts(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("max_attempts must be between 1 and 5")
        return v
