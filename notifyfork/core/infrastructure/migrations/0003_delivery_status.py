"""
Migration: adds DELIVERED and DELIVERY_FAILED statuses,
plus provider_message_id and delivered_at fields.

provider_message_id is indexed — webhook lookups query by this field.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("notifyfork", "0002_seed_templates")]

    operations = [
        migrations.AddField(
            model_name="NotificationModel",
            name="provider_message_id",
            field=models.CharField(
                max_length=255,
                null=True,
                blank=True,
                db_index=True,   # indexed — webhook lookup by this field
                help_text="External ID returned by provider at send time (e.g. Twilio MessageSid)",
            ),
        ),
        migrations.AddField(
            model_name="NotificationModel",
            name="delivered_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        # Update status choices to include new states
        migrations.AlterField(
            model_name="NotificationModel",
            name="status",
            field=models.CharField(
                max_length=20,
                default="pending",
                db_index=True,
                choices=[
                    ("pending",          "Pending"),
                    ("queued",           "Queued"),
                    ("sent",             "Sent"),
                    ("delivered",        "Delivered"),
                    ("delivery_failed",  "Delivery Failed"),
                    ("failed",           "Failed"),
                    ("retrying",         "Retrying"),
                ],
            ),
        ),
    ]
