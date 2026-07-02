"""
Python entry point for NotifyFork.

Use this when the caller lives in the same project that has NotifyFork
installed. For a different service to send events, expose your own
authenticated view that calls this function — see the README.
"""
import logging
from typing import Any

from celery.result import AsyncResult

from notifyfork.core.domain.entities.notification import NotificationChannel, NotificationType
from notifyfork.core.infrastructure.queue.tasks import dispatch_notification

logger = logging.getLogger(__name__)

__all__ = ["send"]


def send(
    recipient: str,
    channel: NotificationChannel | str,
    template_id: str,
    notification_type: NotificationType | str,
    context: dict[str, Any] | None = None,
    max_attempts: int = 3,
) -> AsyncResult:
    """
    Enqueues a notification for delivery.

    You already know the channel and template you want, so this just
    passes them straight to the queue — no routing table or event
    catalog to register first.

    Raises ValueError if recipient is blank or max_attempts is out of
    range (1-5).
    """
    if not recipient or not recipient.strip():
        raise ValueError("recipient cannot be blank")
    if not 1 <= max_attempts <= 5:
        raise ValueError("max_attempts must be between 1 and 5")

    task = dispatch_notification.delay({
        "recipient": recipient.strip(),
        "channel": channel,
        "notification_type": notification_type,
        "template_id": template_id,
        "context": context or {},
        "max_attempts": max_attempts,
    })

    logger.info(
        "Notification accepted and enqueued",
        extra={
            "channel": channel,
            "template_id": template_id,
            "task_id": task.id,
            "recipient_hint": recipient[:6] + "***",  # never log full PII
        },
    )

    return task
