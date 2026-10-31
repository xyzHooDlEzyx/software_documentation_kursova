"""Phase 0 tests deliberately avoid database access and migrations."""

from django.apps import apps
from django.conf import settings
from django.urls import get_resolver


def test_django_project_initializes_without_database() -> None:
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
    assert "django.middleware.csrf.CsrfViewMiddleware" in settings.MIDDLEWARE
    assert settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] == [
        "rest_framework.authentication.SessionAuthentication"
    ]
    assert {"accounts", "catalog", "planning", "execution", "engagement"} <= {
        app.label for app in apps.get_app_configs()
    }
    assert "reporting" not in {app.label for app in apps.get_app_configs()}
    assert any(
        str(pattern.pattern) == "api/v1/" for pattern in get_resolver().url_patterns
    )
