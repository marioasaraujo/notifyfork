"""
Send shipment notification via WhatsApp (Twilio Content Template — EXTERNAL mode).

Provider: NotifyFork's only WhatsApp backend today is Twilio
(TwilioWhatsAppProvider, registered as "twilio_whatsapp" — see
notifyfork/core/infrastructure/providers/whatsapp_provider.py).

channel below is set to the explicit "twilio_whatsapp" rather than the
generic "whatsapp" — both work (the provider's supported_channels lists
both), but this template is EXTERNAL mode (Twilio Content SID), so it's
vendor-locked anyway: pinning the channel makes that explicit instead of
implying a fallback that couldn't work. If you register a second WhatsApp
vendor later (e.g. Evolution API) with a LOCAL-only template, use the
generic channel="whatsapp" there to get automatic fallback.

Template: order_shipped_wa — its DB "body" column holds the Twilio Content SID
(HXxxx), NOT literal message text. The provider never renders it locally — it
reads it through NotificationTemplate.external_template_id and hands the SID
straight to Twilio's ContentTemplate API, which renders it on their end.

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
task = notifyfork.send(
    recipient=recipient,
    channel="twilio_whatsapp",  # explicit vendor — no fallback, matches this EXTERNAL-mode template
    template_id="order_shipped_wa",
    notification_type="transactional",
    context={
        "name": "Mario",
        "tracking_code": "BR999888777BR",
        "carrier": "Correios",
    },
)
print(f"✓ task_id={task.id}")
