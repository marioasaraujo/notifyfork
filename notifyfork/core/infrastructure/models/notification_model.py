import uuid
from django.db import models


class NotificationModel(models.Model):
    """
    Django ORM model for persisting Notification state.

    Intentionally separate from the domain entity —
    the domain entity owns behavior, this model owns persistence.
    """

    class StatusChoices(models.TextChoices):
        PENDING = "pending"
        QUEUED = "queued"
        SENT = "sent"
        DELIVERED = "delivered"
        DELIVERY_FAILED = "delivery_failed"
        FAILED = "failed"
        RETRYING = "retrying"

    class ChannelChoices(models.TextChoices):
        SMS = "sms"
        EMAIL = "email"
        PUSH = "push"
        WHATSAPP = "whatsapp"
        SLACK = "slack"

    class TypeChoices(models.TextChoices):
        TRANSACTIONAL = "transactional"
        ALERT = "alert"
        MARKETING = "marketing"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.CharField(max_length=255)
    channel = models.CharField(max_length=20, choices=ChannelChoices.choices)
    notification_type = models.CharField(max_length=20, choices=TypeChoices.choices)
    template_id = models.CharField(max_length=100)
    context = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING, db_index=True
    )
    provider_used = models.CharField(max_length=50, null=True, blank=True)
    provider_message_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text="External ID returned by provider at send time (e.g. Twilio MessageSid)",
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    error_detail = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "notifyfork"
        db_table = "notifyfork_notifications"
        ordering = ["-created_at"]
        indexes = [
            # Most common query: retrying notifications for the sweep task
            models.Index(fields=["status", "attempts"], name="idx_status_attempts"),
        ]

    def __str__(self) -> str:
        return f"Notification({self.channel} → {self.recipient[:8]}*** [{self.status}])"


class NotificationTemplateModel(models.Model):
    """
    Stores templates in the database.
    Supports both LOCAL (body = content) and EXTERNAL (body = provider template ID) modes.
    """

    class ModeChoices(models.TextChoices):
        LOCAL = "local"
        EXTERNAL = "external"

    id = models.CharField(max_length=100, primary_key=True)  # e.g. "otp_sms"
    body = models.TextField()                                  # content or external template ID
    subject = models.CharField(max_length=255, null=True, blank=True)
    mode = models.CharField(max_length=10, choices=ModeChoices.choices, default=ModeChoices.LOCAL)
    variable_mapping = models.JSONField(
        default=dict,
        help_text='Maps context keys to provider keys. e.g. {"name": "1", "code": "2"} for Twilio WA',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "notifyfork"
        db_table = "notifyfork_templates"

    def __str__(self) -> str:
        return f"Template({self.id} [{self.mode}])"
