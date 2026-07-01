from abc import ABC, abstractmethod

from notifyfork.core.domain.value_objects.template import NotificationTemplate


class TemplateRepository(ABC):
    @abstractmethod
    async def get_by_id(self, template_id: str) -> NotificationTemplate | None: ...
