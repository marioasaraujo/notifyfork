from notifyfork.core.infrastructure.admin import NotificationTemplateAdmin
from notifyfork.core.infrastructure.models import NotificationTemplateModel


class TestNotificationTemplateAdmin:
    def test_body_kind_for_external_mode(self):
        template = NotificationTemplateModel(
            id="order_confirmed_sg",
            mode=NotificationTemplateModel.ModeChoices.EXTERNAL,
            body="d-abc123def456ghi789jkl012mno345",
        )

        result = NotificationTemplateAdmin.body_kind(None, template)

        assert result.startswith("ID externo: ")
        assert "d-abc123def456ghi789jkl012mno345"[:24] in result

    def test_body_kind_for_local_mode(self):
        template = NotificationTemplateModel(
            id="order_confirmed",
            mode=NotificationTemplateModel.ModeChoices.LOCAL,
            body="Order $order_id confirmed. Total: $total",
        )

        result = NotificationTemplateAdmin.body_kind(None, template)

        assert result.startswith("conteúdo local: ")
        assert "Order $order_id confirmed. Total: $total"[:40] in result

    def test_registered_admin_config(self):
        assert NotificationTemplateAdmin.list_display == ("id", "mode", "body_kind", "is_active", "updated_at")
        assert NotificationTemplateAdmin.list_filter == ("mode", "is_active")
