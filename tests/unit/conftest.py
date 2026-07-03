"""
Django test client and settings setup — shared by the api/ and webhooks/ suites.
"""
import pytest
import django
from django.conf import settings


def pytest_configure():
    if not settings.configured:
        settings.configure(
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
                "django.contrib.admin",
                "rest_framework",
                "notifyfork.core.infrastructure",
            ],
            ROOT_URLCONF="tests.urls",
            REST_FRAMEWORK={
                "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
                "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
            },
        )
        django.setup()


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()
