"""
Send a push notification via Firebase Cloud Messaging.

Provider: Firebase (FirebasePushProvider, registered as "firebase_push" — see
notifyfork/core/infrastructure/providers/firebase_provider.py). channel below
is set to the explicit "firebase_push" rather than the generic "push" — both
work (supported_channels lists both), explicit just makes the vendor obvious
at the call site. Only push provider today either way.

Template: flash_sale_push — LOCAL mode
Requires: FIREBASE_CREDENTIALS_PATH pointing to your service account JSON.

The recipient is an FCM device token obtained from your mobile app SDK.

Run from inside a Django project that has NotifyFork installed, e.g.:
    python manage.py shell < examples/push/send_flash_sale.py
"""
import notifyfork

print("→ Push notification via Firebase")
task = notifyfork.send(
    recipient="FCM_DEVICE_TOKEN_HERE",  # replace with a real token
    channel="firebase_push",  # explicit vendor — see docstring
    template_id="flash_sale_push",
    notification_type="marketing",
    context={
        "discount": "40%",
        "expires_in": "3 hours",
    },
)
print(f"✓ task_id={task.id}")
