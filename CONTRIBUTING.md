# Contributing to NotifyFork

First off, thank you for taking the time to contribute! 🎉

## Ways to contribute

- 🐛 **Report a bug**: open an [issue](https://github.com/marioasaraujo/notifyfork/issues) with steps to reproduce
- 💡 **Suggest a feature**: open an issue with the `enhancement` label
- 📖 **Improve documentation**: typos, clarity, translations
- 🔌 **Add a new provider**: see guide below
- ✅ **Fix a bug**: check open issues labeled `good first issue`

## Development setup

```bash
git clone https://github.com/marioasaraujo/notifyfork
cd notifyfork
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Running tests

```bash
pytest tests/unit -v --cov=notifyfork --cov-report=term-missing
```

Coverage must stay above **80%**. PRs that drop coverage will not be merged.

## Adding a new provider

1. Create `notifyfork/core/infrastructure/providers/your_provider.py`
2. Extend `NotificationProvider`, implementing `name`, `supported_channels`, `send_with_template`
3. Register in `notifyfork/core/infrastructure/container/providers.py`
4. Add tests in `tests/unit/providers/test_your_provider.py`
5. Add a runnable example in `examples/your_channel/`
6. Update the channel table in `README.md`

## Adding a new event type

1. Add the rule to `EVENT_ROUTING_TABLE` in `notifyfork/api/routing/event_router.py`
2. Add the template via a new migration in `notifyfork/core/infrastructure/migrations/`

## Pull Request checklist

- [ ] Tests pass (`pytest tests/unit`)
- [ ] Coverage ≥ 80%
- [ ] New provider has at least one example in `examples/`
- [ ] README updated if a new channel or event type was added
- [ ] `CHANGELOG.md` updated

## Code style

```bash
ruff check notifyfork tests   # lint
ruff format notifyfork tests  # format
mypy notifyfork                # type check
```

## Questions?

Open an issue or reach out directly, see the [README](README.md#contact) for contact info.
