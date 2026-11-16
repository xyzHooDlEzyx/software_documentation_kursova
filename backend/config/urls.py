"""Root URL configuration."""

from django.contrib import admin
from django.urls import include, path

from reporting.admin_views import average_activity_report, workout_popularity_report

urlpatterns = [
    path(
        "admin/reports/workout-popularity/",
        admin.site.admin_view(workout_popularity_report),
        name="admin-workout-popularity-report",
    ),
    path(
        "admin/reports/average-activity/",
        admin.site.admin_view(average_activity_report),
        name="admin-average-activity-report",
    ),
    path("admin/", admin.site.urls),
    path("api/v1/", include("config.api_urls")),
]
