"""
Send via SendGrid Dynamic Template (EXTERNAL mode).
Template: order_confirmed_sg — body is your SendGrid template ID (d-xxxx)

Variable mapping stored in the DB translates context keys:
    name     → customer_name
    order_id → order_id
    total    → order_total

Setup:
    1. Create template in SendGrid with {{customer_name}}, {{order_id}}, {{order_total}}
    2. Run: UPDATE notifyfork_templates SET body='d-YOUR_ID' WHERE id='order_confirmed_sg';
    3. Set SENDGRID_API_KEY and SENDGRID_FROM_EMAIL in .env

Run from inside a Django project that has NotifyFork installed, e.g.:
    python manage.py shell < examples/email/send_sendgrid_external.py
"""
import notifyfork

recipient = "customer@example.com"

print(f"→ Email via SendGrid Dynamic Template to {recipient}")
task = notifyfork.send_event(
    event_type="order.confirmed",
    recipient=recipient,
    context={
        "name": "Mario Araujo",
        "order_id": "ORD-2024-001",
        "total": "R$ 349,90",
    },
)
print(f"✓ task_id={task.id}")
