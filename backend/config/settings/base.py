"""Shared settings. Phase 0 must not apply migrations before the custom User exists."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def csv_env(name: str, default: str = "") -> list[str]:
    return [
        part.strip() for part in os.getenv(name, default).split(",") if part.strip()
    ]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
DEBUG = False
ALLOWED_HOSTS = csv_env("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = csv_env("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "accounts.apps.AccountsConfig",
    "catalog.apps.CatalogConfig",
    "planning.apps.PlanningConfig",
    "execution.apps.ExecutionConfig",
    "engagement.apps.EngagementConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "fitness_dev"),
        "USER": os.getenv("POSTGRES_USER", "fitness_app"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    },
}

# Multi-worker production deployments can set
# DJANGO_CACHE_BACKEND=django.core.cache.backends.db.DatabaseCache
# (or another shared cache backend) so rate limiting is shared across processes
# without requiring Redis.
CACHES = {
    "default": {
        "BACKEND": os.getenv(
            "DJANGO_CACHE_BACKEND",
            "django.core.cache.backends.locmem.LocMemCache",
        ),
        "LOCATION": os.getenv("DJANGO_CACHE_LOCATION", "fitness-default-cache"),
    },
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.APISessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "password_reset_ip": os.getenv("DJANGO_THROTTLE_PASSWORD_RESET_IP", "10/hour"),
        "password_reset_email": os.getenv(
            "DJANGO_THROTTLE_PASSWORD_RESET_EMAIL", "5/hour"
        ),
        "password_reset_confirm_ip": os.getenv(
            "DJANGO_THROTTLE_PASSWORD_RESET_CONFIRM_IP", "10/hour"
        ),
    },
    "EXCEPTION_HANDLER": "accounts.errors.exception_handler",
}

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["accounts.authentication.CaseInsensitiveEmailBackend"]
# Django checks only the field-level unique flag. The database has
# UNIQUE(LOWER(email)), and the custom backend uses a case-insensitive lookup.
SILENCED_SYSTEM_CHECKS = ["auth.W004"]
_PASSWORD_VALIDATORS = "django.contrib.auth.password_validation."
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": _PASSWORD_VALIDATORS + "UserAttributeSimilarityValidator"},
    {
        "NAME": _PASSWORD_VALIDATORS + "MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": _PASSWORD_VALIDATORS + "CommonPasswordValidator"},
    {"NAME": _PASSWORD_VALIDATORS + "NumericPasswordValidator"},
]
CSRF_FAILURE_VIEW = "accounts.errors.csrf_failure"
SESSION_COOKIE_AGE = 7 * 24 * 60 * 60
SESSION_SAVE_EVERY_REQUEST = False
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # React reads csrftoken for X-CSRFToken.
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_REFERRER_POLICY = "no-referrer"
PASSWORD_RESET_TIMEOUT = int(os.getenv("DJANGO_PASSWORD_RESET_TIMEOUT", str(60 * 60)))
FRONTEND_ORIGIN = os.getenv("DJANGO_FRONTEND_ORIGIN", "http://localhost:5173").rstrip(
    "/"
)
EMAIL_BACKEND = os.getenv(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.getenv("DJANGO_DEFAULT_FROM_EMAIL", "noreply@fitness.local")
EMAIL_HOST = os.getenv("DJANGO_EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("DJANGO_EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("DJANGO_EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("DJANGO_EMAIL_USE_TLS", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
EMAIL_TIMEOUT = int(os.getenv("DJANGO_EMAIL_TIMEOUT", "10"))
EMAIL_FILE_PATH = os.getenv("DJANGO_EMAIL_FILE_PATH", "")
LANGUAGE_CODE = "uk"
TIME_ZONE = "Europe/Kyiv"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
