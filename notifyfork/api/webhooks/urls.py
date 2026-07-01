from django.urls import path
from notifyfork.api.webhooks.twilio_webhook import TwilioStatusWebhookView
from notifyfork.api.webhooks.sendgrid_webhook import SendGridEventWebhookView
from notifyfork.api.webhooks.resend_webhook import ResendEventWebhookView

urlpatterns = [
    path("twilio/status/",    TwilioStatusWebhookView.as_view(),   name="webhook-twilio-status"),
    path("sendgrid/events/",  SendGridEventWebhookView.as_view(),  name="webhook-sendgrid-events"),
    path("resend/events/",    ResendEventWebhookView.as_view(),    name="webhook-resend-events"),
]
