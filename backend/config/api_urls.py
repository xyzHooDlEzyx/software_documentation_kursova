"""Versioned API routes implemented in the current phase."""

from django.urls import include, path

urlpatterns = [
    path("", include("accounts.urls")),
    path("", include("catalog.urls")),
    path("", include("planning.urls")),
]
