"""
Send shipment notification via WhatsApp (Twilio Content Template — EXTERNAL mode).
Template: order_shipped_wa — body is your Twilio Content SID (HXxxx)

Variable mapping: name→1, tracking_code→2, carrier→3 (positional Twilio vars)

Setup:
    1. Create and get approval for a Content Template in Twilio Console.
       Example body: "Hi {{1}}! Your order shipped via {{3}}. Track: {{2}}"
    2. Run: UPDATE notifyfork_templates SET body='HX_YOUR_SID' WHERE id='order_shipped_wa';
    3. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM_NUMBER in .env

Sandbox: free-form messages work for opted-in numbers only.
Production: approved Content Template required.

Run from inside a Django project that has NotifyFork installed, e.g.:
    python manage.py shell < examples/whatsapp/send_order_shipped.py
"""
import notifyfork

recipient = "+5511999990002"  # replace with opted-in number

print(f"→ WhatsApp shipment alert to {recipient}")
task = notifyfork.send_event(
    event_type="order.shipped",
    recipient=recipient,
    context={
        "name": "Mario",
        "tracking_code": "BR999888777BR",
        "carrier": "Correios",
    },
)
print(f"✓ task_id={task.id}")
