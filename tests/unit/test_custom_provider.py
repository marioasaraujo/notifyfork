import pytest

import notifyfork
from notifyfork.core.infrastructure.container import providers as providers_module
from notifyfork.core.infrastructure.container.providers import Container


@pytest.fixture(autouse=True)
def clean_extra_providers():
    """
    _extra_providers is module-level state — reset it around every test so
    a provider registered here doesn't leak into other test modules.
    """
    original = providers_module._extra_providers[:]
    yield
    providers_module._extra_providers[:] = original
    Container.providers.cache_clear()


class TestCustomProviderDecorator:
    def test_decorator_is_exported_from_top_level_package(self):
        assert notifyfork.provider is providers_module.provider

    def test_registered_provider_appears_in_container_providers(self, monkeypatch):
        monkeypatch.delenv("NOTIFYFORK_PROVIDER_ORDER", raising=False)

        @notifyfork.provider
        class XptoProvider:
            name = "xpto"

            def send(self, *args, **kwargs):
                return "sent"

        names = [p.name for p in Container.providers()]
        assert "xpto" in names

    def test_decorated_class_does_not_need_to_inherit_from_anything(self):
        @notifyfork.provider
        class PlainProvider:
            name = "plain"

            def send(self, *args, **kwargs):
                return "sent"

        assert PlainProvider.__bases__ == (object,)
        instance = next(p for p in providers_module._extra_providers if p.name == "plain")
        assert isinstance(instance, PlainProvider)

    def test_decorator_instantiates_with_no_arguments(self):
        @notifyfork.provider
        class CountingProvider:
            name = "counting"

            def __init__(self):
                self.calls = 0

            def send(self, *args, **kwargs):
                self.calls += 1

        instance = next(p for p in providers_module._extra_providers if p.name == "counting")
        assert instance.calls == 0

    def test_decorator_clears_the_providers_cache(self, monkeypatch):
        monkeypatch.delenv("NOTIFYFORK_PROVIDER_ORDER", raising=False)

        # Prime the cache before registering, like a caller who read
        # Container.providers() before the decorator ran.
        Container.providers()

        @notifyfork.provider
        class LateProvider:
            name = "late"

            def send(self, *args, **kwargs):
                return "sent"

        names = [p.name for p in Container.providers()]
        assert "late" in names

    def test_decorator_returns_the_original_class(self):
        @notifyfork.provider
        class ReturnedProvider:
            name = "returned"

            def send(self, *args, **kwargs):
                return "sent"

        assert ReturnedProvider.name == "returned"
        assert callable(ReturnedProvider)
