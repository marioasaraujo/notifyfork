"""
Celery tasks for processing provider delivery callbacks.

Design: webhook endpoints respond 200 immediately, then enqueue here.
This prevents provider retries caused by slow processing, and keeps
the webhook handler stateless and fast.
"""
import logging
from uuid import UUID

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10, acks_late=True)
def process_delivery_update(
    self,
    notification_id: str,
    provider: str,
    delivered: bool,
    reason: str | None = None,
) -> dict:
    """
    Updates notification delivery status from provider webhook.

    Runs async so the webhook endpoint can respond instantly.
    Idempotent — safe to run twice if the provider retries the webhook.
    """
    from notifyfork.core.infrastructure.container.providers import Container
    import asyncio

    try:
        repository = Container.notification_repository()
        uid = UUID(notification_id)

        notification = asyncio.get_event_loop().run_until_complete(
            repository.get_by_id(uid)
        )

        if not notification:
            logger.warning("Webhook for unknown notification", extra={
                "notification_id": notification_id, "provider": provider,
            })
            return {"status": "not_found"}

        # Idempotency — if already terminal, skip
        if notification.is_terminal:
            logger.info("Notification already terminal, skipping webhook", extra={
                "notification_id": notification_id,
                "current_status": notification.status,
            })
            return {"status": "already_terminal"}

        if delivered:
            notification.mark_delivered()
        else:
            notification.mark_delivery_failed(reason or "Provider reported delivery failure")

        asyncio.get_event_loop().run_until_complete(repository.save(notification))

        logger.info("Delivery status updated", extra={
            "notification_id": notification_id,
            "delivered": delivered,
            "status": notification.status,
        })
        return {"status": notification.status}

    except Exception as exc:
        logger.error("Failed to process delivery update", extra={
            "notification_id": notification_id, "error": str(exc),
        })
        raise self.retry(exc=exc)
