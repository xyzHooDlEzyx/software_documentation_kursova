"""Project smoke tests: settings wiring and database-tagged system checks."""

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.urls import get_resolver


def test_django_project_initializes_without_database() -> None:
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
    assert "django.middleware.csrf.CsrfViewMiddleware" in settings.MIDDLEWARE
    assert settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] == [
        "accounts.authentication.APISessionAuthentication"
    ]
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert {"accounts", "catalog", "planning", "execution", "engagement"} <= {
        app.label for app in apps.get_app_configs()
    }
    assert "reporting" not in {app.label for app in apps.get_app_configs()}
    assert any(
        str(pattern.pattern) == "api/v1/" for pattern in get_resolver().url_patterns
    )


def test_database_system_checks_pass(db) -> None:
    """``check`` without ``--database`` skips database-tagged checks.

    ``migrate`` runs them (e.g. models.E034 index name length), so run them
    here to fail in the suite instead of on the first ``migrate``.
    """
    call_command("check", databases=["default"], fail_level="ERROR")
