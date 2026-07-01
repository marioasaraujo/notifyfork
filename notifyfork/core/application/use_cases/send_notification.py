import logging
from uuid import UUID

from notifyfork.core.application.dtos.send_notification_dto import SendNotificationDTO
from notifyfork.core.application.interfaces.notification_provider import NotificationProvider
from notifyfork.core.application.interfaces.notification_repository import NotificationRepository
from notifyfork.core.application.interfaces.template_repository import TemplateRepository
from notifyfork.core.domain.entities.notification import Notification
from notifyfork.shared.exceptions.provider_exceptions import NoProviderAvailable, TemplateNotFound

logger = logging.getLogger(__name__)


class SendNotificationUseCase:
    """
    Orchestrates notification dispatch.

    Does not know whether templates are local or external —
    that's the provider's responsibility.
    Does not know how Twilio, SendGrid or Firebase work.
    Knows only: get template, pick providers, persist state, deliver.

    When more than one provider supports the channel, tries them in order
    (see Container's provider ordering) and falls through to the next on
    failure. notification.provider_used always records which one actually
    sent it, and each fallback is logged as it happens.
    """

    def __init__(
        self,
        repository: NotificationRepository,
        template_repository: TemplateRepository,
        providers: list[NotificationProvider],
    ) -> None:
        self._repository = repository
        self._template_repository = template_repository
        self._providers = providers

    async def execute(self, dto: SendNotificationDTO) -> UUID:
        template = await self._template_repository.get_by_id(dto.template_id)
        if not template:
            raise TemplateNotFound(dto.template_id)

        candidates = self._resolve_providers(dto.channel)

        notification = Notification(
            recipient=dto.recipient,
            channel=dto.channel,
            notification_type=dto.notification_type,
            template_id=dto.template_id,
            context=dto.context,
            max_attempts=dto.max_attempts,
        )

        notification.mark_queued()
        await self._repository.save(notification)

        error = "Unknown provider error"
        for index, provider in enumerate(candidates):
            # Provider handles LOCAL vs EXTERNAL rendering internally
            result = await provider.send_with_template(
                recipient=dto.recipient,
                template=template,
                context=dto.context,
            )
            if result.success:
                notification.mark_sent(provider.name)
                break

            error = result.error or "Unknown provider error"
            has_fallback = index < len(candidates) - 1
            logger.warning(
                "Provider failed" + (", falling back to next provider" if has_fallback else ""),
                extra={
                    "provider": provider.name,
                    "channel": dto.channel.value,
                    "error": error,
                    "fallback_available": has_fallback,
                },
            )
        else:
            notification.mark_failed(error)

        await self._repository.save(notification)
        return notification.id

    def _resolve_providers(self, channel) -> list[NotificationProvider]:
        candidates = [p for p in self._providers if p.supports(channel)]
        if not candidates:
            raise NoProviderAvailable(channel)
        return candidates
