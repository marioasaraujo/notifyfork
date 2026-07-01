import logging
from notifyfork.core.application.interfaces.template_repository import TemplateRepository
from notifyfork.core.domain.value_objects.template import NotificationTemplate, TemplateMode, VariableMapping

logger = logging.getLogger(__name__)


class DatabaseTemplateRepository(TemplateRepository):

    async def get_by_id(self, template_id: str) -> NotificationTemplate | None:
        from notifyfork.core.infrastructure.models.notification_model import NotificationTemplateModel
        try:
            obj = await NotificationTemplateModel.objects.aget(id=template_id, is_active=True)
            return NotificationTemplate(
                id=obj.id,
                body=obj.body,
                subject=obj.subject,
                mode=TemplateMode(obj.mode),
                variable_mapping=VariableMapping(obj.variable_mapping or {}),
            )
        except NotificationTemplateModel.DoesNotExist:
            logger.warning("Template not found", extra={"template_id": template_id})
            return None
