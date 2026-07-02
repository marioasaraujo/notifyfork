"""
Register a custom provider from outside the lib and use it to deliver an
SMS OTP, without touching
notifyfork/core/infrastructure/container/providers.py.

No NotificationProvider subclassing required — @notifyfork.provider is
duck-typed, same as every built-in provider: the container only ever
reads .name and calls .send_with_template(), and the result only needs
.success / .error. No notifyfork types needed to write one.

Run from inside a Django project that has NotifyFork installed, e.g.:
    python manage.py shell < examples/custom_provider/register_xpto_provider.py
"""
from types import SimpleNamespace

import notifyfork


@notifyfork.provider
class XptoProvider:
    name = "xpto"
    supported_channels = ["sms"]

    def supports(self, channel):
        return channel in self.supported_channels

    async def send_with_template(self, recipient, template, context):
        body = template.render(context)
        print(f"[xpto] would send to {recipient}: {body}")
        return SimpleNamespace(success=True, error=None)


recipient = "+5511999990001"  # replace with a real number

print(f"→ SMS OTP to {recipient} via custom Xpto provider")
task = notifyfork.send(
    recipient=recipient,
    channel="sms",
    template_id="otp_sms",
    notification_type="transactional",
    context={"code": "482913"},
)
print(f"✓ task_id={task.id}")
