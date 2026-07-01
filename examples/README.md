# NotifyFork Examples

Each example calls `notifyfork.send_event(...)` directly, no HTTP server
required. They need to run inside a Django project that has NotifyFork
installed and configured (see the main [README](../README.md) for setup),
with a Celery worker up to actually process the queued task:

```bash
python manage.py migrate
celery -A yourproject worker --loglevel=info

# in another terminal, from your project's directory
python manage.py shell < path/to/examples/sms/send_otp.py
```
