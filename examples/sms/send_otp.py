"""
Send an OTP via SMS (Twilio).
Template: otp_sms — LOCAL mode
Requires: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER

Run from inside a Django project that has NotifyFork installed, e.g.:
    python manage.py shell < examples/sms/send_otp.py
"""
import notifyfork

recipient = "+5511999990001"  # replace with a real number

print(f"→ SMS OTP to {recipient}")
task = notifyfork.send(
    recipient=recipient,
    channel="sms",
    template_id="otp_sms",
    notification_type="transactional",
    context={"code": "847291"},
)
print(f"✓ task_id={task.id}")
