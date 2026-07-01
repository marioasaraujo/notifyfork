import logging
from uuid import UUID

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,        # 1 min first retry
    retry_backoff=True,            # exponential: 1m, 2m, 4m
    retry_backoff_max=600,         # cap at 10 minutes
    acks_late=True,                # only ack after task completes — safe on worker crash
    reject_on_worker_lost=True,
)
def dispatch_notification(self, payload: dict) -> dict:
    """
    Celery task that drives notification dispatch.

    acks_late=True + reject_on_worker_lost=True ensures that if a
    worker dies mid-execution, the task is re-queued instead of lost.

    Retry strategy uses exponential backoff to avoid hammering
    a provider that's temporarily down (thundering herd prevention).
    """
    from notifyfork.core.application.dtos.send_notification_dto import SendNotificationDTO
    from notifyfork.core.infrastructure.container import Container

    try:
        dto = SendNotificationDTO(**payload)
        use_case = Container.send_notification_use_case()

        import asyncio
        notification_id = asyncio.get_event_loop().run_until_complete(use_case.execute(dto))

        logger.info("Task completed", extra={"notification_id": str(notification_id)})
        return {"notification_id": str(notification_id), "status": "dispatched"}

    except Exception as exc:
        logger.warning(
            "Task failed, scheduling retry",
            extra={"attempt": self.request.retries + 1, "error": str(exc)},
        )
        raise self.retry(exc=exc)


@shared_task
def retry_pending_notifications() -> dict:
    """
    Periodic task (beat) that picks up notifications stuck in RETRYING state.

    Prevents silent failures from getting lost if the worker
    crashed before persisting the final status.

    Schedule this via Celery Beat — e.g. every 5 minutes.
    """
    from notifyfork.core.infrastructure.container import Container

    repository = Container.notification_repository()

    import asyncio
    pending = asyncio.get_event_loop().run_until_complete(
        repository.get_pending_retries(limit=100)
    )

    queued = 0
    for notification in pending:
        if notification.can_retry:
            dispatch_notification.delay({
                "recipient": notification.recipient,
                "channel": notification.channel,
                "notification_type": notification.notification_type,
                "template_id": notification.template_id,
                "context": notification.context,
            })
            queued += 1

    logger.info("Retry sweep complete", extra={"queued": queued})
    return {"retried": queued}
