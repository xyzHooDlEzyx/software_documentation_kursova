"""URL routes for the shared fitness catalog API (C01–C04)."""

from django.urls import path

from .views import (
    CategoryListView,
    ExerciseListView,
    WorkoutDetailView,
    WorkoutListView,
)

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("exercises/", ExerciseListView.as_view(), name="exercise-list"),
    path("workouts/", WorkoutListView.as_view(), name="workout-list"),
    path(
        "workouts/<int:workout_id>/",
        WorkoutDetailView.as_view(),
        name="workout-detail",
    ),
]
