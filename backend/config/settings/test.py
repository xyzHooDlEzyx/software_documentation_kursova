"""Test settings for Phase 1 authentication and domain tests."""

from .base import *  # noqa: F403

SECRET_KEY = "phase-0-test-only-secret"
ALLOWED_HOSTS = ["testserver", "localhost"]
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
