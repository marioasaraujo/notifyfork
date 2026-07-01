"""
Python entry point for NotifyFork.

Use this when the caller lives in the same project that has NotifyFork
installed. For a different service to send events, expose your own
authenticated view that calls this function — see the README.
"""
import logging
from typing import Any

from celery.result import AsyncResult

from notifyfork.api.routing.event_router import EventRouter, UnroutableEvent
from notifyfork.core.infrastructure.queue.tasks import dispatch_notification

logger = logging.getLogger(__name__)

__all__ = ["send_event", "UnroutableEvent"]

_router = EventRouter()


def send_event(
    event_type: str,
    recipient: str,
    context: dict[str, Any] | None = None,
    max_attempts: int = 3,
) -> AsyncResult:
    """
    Resolves event_type to a channel + template and enqueues delivery.

    Raises UnroutableEvent if event_type has no routing rule, ValueError
    if recipient is blank or max_attempts is out of range (1-5).
    """
    if not recipient or not recipient.strip():
        raise ValueError("recipient cannot be blank")
    if not 1 <= max_attempts <= 5:
        raise ValueError("max_attempts must be between 1 and 5")

    normalized_event_type = event_type.strip().lower().replace(" ", "_")
    rule = _router.resolve(normalized_event_type)

    task = dispatch_notification.delay({
        "recipient": recipient.strip(),
        "channel": rule.channel.value,
        "notification_type": rule.notification_type.value,
        "template_id": rule.template_id,
        "context": context or {},
        "max_attempts": max_attempts,
    })

    logger.info(
        "Event accepted and enqueued",
        extra={
            "event_type": normalized_event_type,
            "channel": rule.channel.value,
            "task_id": task.id,
            "recipient_hint": recipient[:6] + "***",  # never log full PII
        },
    )

    return task
