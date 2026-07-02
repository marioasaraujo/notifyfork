from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from notifyfork.core.domain.entities.notification import NotificationChannel
from notifyfork.core.domain.value_objects.template import NotificationTemplate


@dataclass
class ProviderResult:
    success: bool
    provider_name: str
    external_id: str | None = None
    error: str | None = None


class NotificationProvider(ABC):
    """
    Base contract every provider must implement.

    send_with_template() is the unified entry point.
    The provider decides internally whether to render locally
    or delegate to an external template system.
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def supported_channels(self) -> list[NotificationChannel | str]: ...

    @abstractmethod
    async def send_with_template(
        self,
        recipient: str,
        template: NotificationTemplate,
        context: dict[str, Any],
    ) -> ProviderResult: ...

    def supports(self, channel: NotificationChannel | str) -> bool:
        return channel in self.supported_channels
