import logging
from uuid import UUID

from notifyfork.core.application.interfaces.notification_repository import NotificationRepository
from notifyfork.core.domain.entities.notification import Notification, NotificationStatus

logger = logging.getLogger(__name__)


class DjangoNotificationRepository(NotificationRepository):

    async def save(self, notification: Notification) -> None:
        from notifyfork.core.infrastructure.models.notification_model import NotificationModel
        await NotificationModel.objects.aupdate_or_create(
            id=notification.id,
            defaults={
                "recipient": notification.recipient,
                "channel": notification.channel,
                "notification_type": notification.notification_type,
                "template_id": notification.template_id,
                "context": notification.context,
                "status": notification.status.value,
                "provider_used": notification.provider_used,
                "attempts": notification.attempts,
                "max_attempts": notification.max_attempts,
                "error_detail": notification.error_detail,
                "sent_at": notification.sent_at,
            },
        )

    async def get_by_id(self, notification_id: UUID) -> Notification | None:
        from notifyfork.core.infrastructure.models.notification_model import NotificationModel
        try:
            obj = await NotificationModel.objects.aget(id=notification_id)
            return self._to_entity(obj)
        except NotificationModel.DoesNotExist:
            return None

    async def get_pending_retries(self, limit: int = 100) -> list[Notification]:
        """
        Single bounded query — never loads all records then filters in Python.
        N+1 safe: one query, one trip to the database.
        """
        from notifyfork.core.infrastructure.models.notification_model import NotificationModel
        qs = (
            NotificationModel.objects
            .filter(status=NotificationModel.StatusChoices.RETRYING)
            .order_by("created_at")[:limit]
        )
        return [self._to_entity(obj) async for obj in qs]

    @staticmethod
    def _to_entity(obj) -> Notification:
        n = Notification(
            recipient=obj.recipient,
            channel=obj.channel,
            notification_type=obj.notification_type,
            template_id=obj.template_id,
            context=obj.context,
            id=obj.id,
            attempts=obj.attempts,
            max_attempts=obj.max_attempts,
            error_detail=obj.error_detail,
            created_at=obj.created_at,
            sent_at=obj.sent_at,
            provider_used=obj.provider_used,
        )
        n.status = NotificationStatus(obj.status)
        return n
