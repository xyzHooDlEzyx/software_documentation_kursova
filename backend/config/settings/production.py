"""HTTPS production baseline; deployment details arrive later."""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

if not SECRET_KEY:  # noqa: F405
    raise ImproperlyConfigured("DJANGO_SECRET_KEY is required in production.")
if not ALLOWED_HOSTS:  # noqa: F405
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS is required in production.")
if not DATABASES["default"]["PASSWORD"]:  # noqa: F405
    raise ImproperlyConfigured("POSTGRES_PASSWORD is required in production.")
if not os.getenv("DJANGO_FRONTEND_ORIGIN"):
    raise ImproperlyConfigured("DJANGO_FRONTEND_ORIGIN is required in production.")

DEBUG = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
