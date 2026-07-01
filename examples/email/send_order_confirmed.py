"""
Send an order confirmation email (local HTML template via SMTP or SendGrid).
Template: order_confirmed — LOCAL mode
Requires: SMTP_* or SENDGRID_* vars in .env

Run from inside a Django project that has NotifyFork installed, e.g.:
    python manage.py shell < examples/email/send_order_confirmed.py
"""
import notifyfork

recipient = "customer@example.com"

print(f"→ Email order confirmation to {recipient}")
task = notifyfork.send_event(
    event_type="order.confirmed",
    recipient=recipient,
    context={
        "name": "Mario Araujo",
        "order_id": "ORD-20240601-001",
        "total": "R$ 349,90",
    },
)
print(f"✓ task_id={task.id}")
