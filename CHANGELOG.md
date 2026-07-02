# Changelog

All notable changes to NotifyFork will be documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- `@notifyfork.provider` decorator to register a custom provider from outside the lib, no `NotificationProvider` subclassing required (duck-typed, same as everything else in the container)
- `notifyfork.send()`, replacing `send_event()`. You pass `channel`, `template_id` and `notification_type` straight through instead of registering an event type first
- `examples/custom_provider/register_xpto_provider.py` showing the provider decorator end to end

### Changed
- `examples/email/send_sendgrid_external.py` now actually hits the `order_confirmed_sg` template it documents. Under the old event routing it was silently sharing `order.confirmed`'s rule and sending through `order_confirmed` instead, so the SendGrid Dynamic Template path in that example never really ran
- `channel` and `notification_type` are plain strings now, not the closed `NotificationChannel` / `NotificationType` enums, all the way through `SendNotificationDTO`, the `Notification` entity and the repository. A provider registered for a channel NotifyFork doesn't ship out of the box (Telegram, say) now works end to end through `notifyfork.send(channel="telegram", ...)` — previously pydantic rejected it before the provider was ever consulted. The enums are still there and still used by the built-in providers, they're just no longer enforced on the way in

### Removed
- `event_router.py`, `EventType` and `EVENT_ROUTING_TABLE`. That layer only translated an `event_type` string into `channel` + `template_id` before queueing, and the queue already accepted those fields directly. Every caller already knows the channel and template it wants, so there was nothing left for the router to decide
- `send_event()`, replaced by `send()`

## [0.1.0] - 2024-06-01

### Added
- Provider-agnostic notification gateway with event-driven routing
- Channels: SMS (Twilio), Email (SMTP + SendGrid), WhatsApp (Twilio), Push (Firebase), Slack
- LOCAL and EXTERNAL template modes with `VariableMapping` for provider-specific variable translation
- Celery async dispatch with `acks_late`, exponential backoff, and periodic retry sweep
- Django ORM repositories with full async support (`aupdate_or_create`, `aget`)
- Dependency container that only registers providers with credentials configured
- Django migrations with seed data for default templates
- Full unit test suite with pytest + conftest shared fixtures
- Runnable examples for every channel
- Bilingual README (English + Portuguese)
