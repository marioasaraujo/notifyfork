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
            has_fallback = index < len(candidates) - 1
            try:
                # Provider handles LOCAL vs EXTERNAL rendering internally
                result = await provider.send_with_template(
                    recipient=dto.recipient,
                    template=template,
                    context=dto.context,
                )
            except Exception as exc:
                # A provider raising instead of returning ProviderResult(success=False)
                # must not escape this loop: an uncaught exception here propagates to
                # the Celery task, which retries the whole use case from scratch
                # (creating a brand-new Notification each time) and this notification
                # is never saved as FAILED — it's left stuck in QUEUED forever, even
                # after Celery's own retries are exhausted.
                error = str(exc)
                logger.warning(
                    "Provider raised an exception"
                    + (", falling back to next provider" if has_fallback else ""),
                    extra={
                        "provider": provider.name,
                        "channel": dto.channel,
                        "error": error,
                        "fallback_available": has_fallback,
                    },
                )
                continue

            if result.success:
                notification.mark_sent(provider.name, result.external_id)
                break

            error = result.error or "Unknown provider error"
            logger.warning(
                "Provider failed" + (", falling back to next provider" if has_fallback else ""),
                extra={
                    "provider": provider.name,
                    "channel": dto.channel,
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
