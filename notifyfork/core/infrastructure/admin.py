from django.contrib import admin

from notifyfork.core.infrastructure.models import NotificationTemplateModel


@admin.register(NotificationTemplateModel)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "mode", "body_kind", "is_active", "updated_at")
    list_filter = ("mode", "is_active")
    search_fields = ("id",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("id", "mode", "is_active")}),
        (
            "Conteúdo",
            {
                "fields": ("body", "subject"),
                "description": (
                    "Modo LOCAL: \"body\" é o texto/HTML enviado, com $variaveis "
                    "(ex: \"Seu código é: $code\"). "
                    "Modo EXTERNAL: \"body\" NÃO é texto de mensagem — é o ID do "
                    "template no provider. Para WhatsApp (Twilio) é o Content SID "
                    "(HXxxx); para SendGrid é o Dynamic Template ID (d-xxxx)."
                ),
            },
        ),
        ("Mapeamento de variáveis", {"fields": ("variable_mapping",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="body é...")
    def body_kind(self, obj: NotificationTemplateModel) -> str:
        if obj.mode == NotificationTemplateModel.ModeChoices.EXTERNAL:
            return f"ID externo: {obj.body[:24]}"
        return f"conteúdo local: {obj.body[:40]}"
