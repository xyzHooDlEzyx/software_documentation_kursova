"""Local HTTP development settings."""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

if not SECRET_KEY:  # noqa: F405
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY from .env before local startup.")

DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() in {"1", "true", "yes", "on"}
ALLOWED_HOSTS = csv_env(  # noqa: F405
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1"
)
CSRF_TRUSTED_ORIGINS = csv_env(  # noqa: F405
    "DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:5173"
)
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
