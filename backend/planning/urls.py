"""URL routes for personal program selection and planning API (G01–G06)."""

from django.urls import path

from .views import (
    ProgramRecommendationView,
    UserProgramDetailView,
    UserProgramListCreateView,
    UserProgramWorkoutCompositionView,
)

urlpatterns = [
    path(
        "program-recommendation/",
        ProgramRecommendationView.as_view(),
        name="program-recommendation",
    ),
    path(
        "user-programs/",
        UserProgramListCreateView.as_view(),
        name="user-program-list-create",
    ),
    path(
        "user-programs/<int:program_id>/",
        UserProgramDetailView.as_view(),
        name="user-program-detail",
    ),
    path(
        "user-programs/<int:program_id>/workouts/<int:entry_id>/",
        UserProgramWorkoutCompositionView.as_view(),
        name="user-program-workout-composition",
    ),
]
