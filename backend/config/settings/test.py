"""No database is accessed by the Phase 0 smoke tests."""

from .base import *  # noqa: F403

SECRET_KEY = "phase-0-test-only-secret"
ALLOWED_HOSTS = ["testserver", "localhost"]
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
