"""
Send an order confirmation email (local HTML template via SMTP or SendGrid).

Provider: whichever of sendgrid_email, resend_email, smtp_email is registered
(credentials present) is picked per DEFAULT_PROVIDER_ORDER, overridable with
NOTIFYFORK_PROVIDER_ORDER. This works because the template below is LOCAL
mode — plain HTML any of those three can render and send. That fallback would
NOT hold for an EXTERNAL-mode template (see send_sendgrid_external.py): a
SendGrid Dynamic Template ID only SendGrid understands.

Unlike the other examples, channel here is deliberately left as the generic
"email" instead of pinning a vendor (e.g. "sendgrid_email") — pinning one
would defeat the point of this example, which is to show automatic fallback
across all three email providers. Use the generic form when you want
fallback; use the explicit vendor_channel form (as in the other examples)
when you don't.

Template: order_confirmed — LOCAL mode
Requires: SMTP_* or SENDGRID_* vars in .env

Run from inside a Django project that has NotifyFork installed, e.g.:
    python manage.py shell < examples/email/send_order_confirmed.py
"""
import notifyfork

recipient = "customer@example.com"

print(f"→ Email order confirmation to {recipient}")
task = notifyfork.send(
    recipient=recipient,
    channel="email",
    template_id="order_confirmed",
    notification_type="transactional",
    context={
        "name": "Mario Araujo",
        "order_id": "ORD-20240601-001",
        "total": "R$ 349,90",
    },
)
print(f"✓ task_id={task.id}")
