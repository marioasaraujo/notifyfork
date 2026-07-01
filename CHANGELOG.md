# Changelog

All notable changes to NotifyFork will be documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
