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

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # React reads csrftoken for X-CSRFToken.
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
LANGUAGE_CODE = "uk"
TIME_ZONE = "Europe/Kyiv"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
