"""
Send a system error alert to a Slack channel.
Template: system_error_slack — LOCAL mode with Markdown blocks

The recipient is a Slack channel ID (C012AB3CD) or user ID.
Your bot needs chat:write permission in that channel.
Requires: SLACK_BOT_TOKEN in .env (xoxb-...)

Run from inside a Django project that has NotifyFork installed, e.g.:
    python manage.py shell < examples/slack/send_system_error.py
"""
import notifyfork

recipient = "C012AB3CD"  # replace with your Slack channel ID

print(f"→ Slack alert to channel {recipient}")
task = notifyfork.send(
    recipient=recipient,
    channel="slack",
    template_id="system_error_slack",
    notification_type="alert",
    context={
        "service": "payment-api",
        "error": "Connection timeout after 30s — PostgreSQL unreachable",
        "env": "production",
    },
)
print(f"✓ task_id={task.id}")
