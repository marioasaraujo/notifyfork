"""
Seed migration — inserts the default templates that ship with NotifyFork.

These are starter templates. Edit them in the database or via Django admin
to match your product's copy and branding.
"""
from django.db import migrations


TEMPLATES = [
    # SMS
    {
        "id": "otp_sms",
        "body": "Your NotifyFork verification code is: $code. Valid for 10 minutes.",
        "subject": None,
        "mode": "local",
        "variable_mapping": {},
    },
    {
        "id": "payment_failed_sms",
        "body": "Payment of $amount failed for order $order_id. Please update your payment method.",
        "subject": None,
        "mode": "local",
        "variable_mapping": {},
    },

    # Email (local HTML)
    {
        "id": "email_verification",
        "body": "<p>Hi $name,</p><p>Click <a href='$link'>here</a> to verify your email.</p>",
        "subject": "Verify your email address",
        "mode": "local",
        "variable_mapping": {},
    },
    {
        "id": "order_confirmed",
        "body": "<p>Hi $name,</p><p>Your order <strong>$order_id</strong> is confirmed. Total: $total</p>",
        "subject": "Order $order_id confirmed",
        "mode": "local",
        "variable_mapping": {},
    },

    # WhatsApp (Twilio external template)
    # body = Twilio Content Template SID
    # variable_mapping translates context keys to positional Twilio variables
    {
        "id": "order_shipped_wa",
        "body": "REPLACE_WITH_YOUR_TWILIO_CONTENT_SID",
        "subject": None,
        "mode": "external",
        "variable_mapping": {"name": "1", "tracking_code": "2", "carrier": "3"},
    },

    # Email (SendGrid external template)
    # body = SendGrid Dynamic Template ID (d-xxxx)
    {
        "id": "order_confirmed_sg",
        "body": "REPLACE_WITH_YOUR_SENDGRID_TEMPLATE_ID",
        "subject": None,
        "mode": "external",
        "variable_mapping": {
            "name": "customer_name",
            "order_id": "order_id",
            "total": "order_total",
        },
    },

    # Push (Firebase, rendered locally)
    {
        "id": "flash_sale_push",
        "body": "Hurry! $discount OFF everything. Ends in $expires_in.",
        "subject": "Flash Sale — $discount OFF",
        "mode": "local",
        "variable_mapping": {},
    },
    {
        "id": "pickup_ready_push",
        "body": "Your order $order_id is ready for pickup at $location.",
        "subject": "Your order is ready!",
        "mode": "local",
        "variable_mapping": {},
    },

    # Slack (rendered locally with Markdown)
    {
        "id": "system_error_slack",
        "body": "*Service:* $service\n*Error:* $error\n*Environment:* $env",
        "subject": "🚨 Error in $service",
        "mode": "local",
        "variable_mapping": {},
    },
    {
        "id": "deploy_done_slack",
        "body": "*Service:* $service deployed successfully\n*Version:* $version\n*By:* $author",
        "subject": "✅ Deploy completed — $service",
        "mode": "local",
        "variable_mapping": {},
    },
]


def seed_templates(apps, schema_editor):
    NotificationTemplateModel = apps.get_model("notifyfork", "NotificationTemplateModel")
    for t in TEMPLATES:
        NotificationTemplateModel.objects.get_or_create(id=t["id"], defaults=t)


def unseed_templates(apps, schema_editor):
    NotificationTemplateModel = apps.get_model("notifyfork", "NotificationTemplateModel")
    ids = [t["id"] for t in TEMPLATES]
    NotificationTemplateModel.objects.filter(id__in=ids).delete()


class Migration(migrations.Migration):
    dependencies = [("notifyfork", "0001_initial")]
    operations = [migrations.RunPython(seed_templates, unseed_templates)]
