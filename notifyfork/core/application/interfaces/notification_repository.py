from abc import ABC, abstractmethod
from uuid import UUID

from notifyfork.core.domain.entities.notification import Notification


class NotificationRepository(ABC):
    @abstractmethod
    async def save(self, notification: Notification) -> None: ...

    @abstractmethod
    async def get_by_id(self, notification_id: UUID) -> Notification | None: ...

    @abstractmethod
    async def get_pending_retries(self, limit: int = 100) -> list[Notification]: ...
