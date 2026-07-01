from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="NotificationModel",
            fields=[
                ("id", models.UUIDField(primary_key=True, editable=False)),
                ("recipient", models.CharField(max_length=255)),
                ("channel", models.CharField(max_length=20)),
                ("notification_type", models.CharField(max_length=20)),
                ("template_id", models.CharField(max_length=100)),
                ("context", models.JSONField(default=dict)),
                ("status", models.CharField(max_length=20, default="pending", db_index=True)),
                ("provider_used", models.CharField(max_length=50, null=True, blank=True)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("max_attempts", models.PositiveSmallIntegerField(default=3)),
                ("error_detail", models.TextField(null=True, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("sent_at", models.DateTimeField(null=True, blank=True)),
            ],
            options={"db_table": "notifyfork_notifications", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="NotificationModel",
            index=models.Index(fields=["status", "attempts"], name="idx_status_attempts"),
        ),
        migrations.CreateModel(
            name="NotificationTemplateModel",
            fields=[
                ("id", models.CharField(max_length=100, primary_key=True)),
                ("body", models.TextField()),
                ("subject", models.CharField(max_length=255, null=True, blank=True)),
                ("mode", models.CharField(max_length=10, default="local")),
                ("variable_mapping", models.JSONField(default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "notifyfork_templates"},
        ),
    ]
