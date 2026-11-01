"""Read-only selectors for the shared fitness catalog (C01–C04)."""

from django.db.models import Count, Prefetch, QuerySet
from rest_framework.exceptions import NotFound

from .models import Exercise, ExerciseCategory, Workout, WorkoutExercise


def list_categories() -> list[dict[str, str]]:
    """Return static exercise/workout category choices for C01."""
    return [
        {"code": choice.value, "label": str(choice.label)}
        for choice in ExerciseCategory
    ]


def list_active_exercises(
    *,
    category: str | None = None,
    search: str | None = None,
) -> QuerySet[Exercise]:
    """Return non-archived exercises filtered by category/search and ordered by name."""
    queryset = Exercise.objects.filter(is_archived=False)
    if category:
        queryset = queryset.filter(category=category)
    if search is not None and search.strip():
        queryset = queryset.filter(name__icontains=search.strip())
    return queryset.order_by("name", "id")


def list_active_workouts(
    *,
    category: str | None = None,
    search: str | None = None,
) -> QuerySet[Workout]:
    """Return non-archived workouts with annotated exercise count ordered by name."""
    queryset = Workout.objects.filter(is_archived=False).annotate(
        exercise_count=Count("workout_exercises")
    )
    if category:
        queryset = queryset.filter(category=category)
    if search is not None and search.strip():
        queryset = queryset.filter(name__icontains=search.strip())
    return queryset.order_by("name", "id")


def get_active_workout_detail(*, workout_id: int) -> Workout:
    """Return a non-archived workout with ordered exercises or raise NotFound."""
    ordered_entries = Prefetch(
        "workout_exercises",
        queryset=WorkoutExercise.objects.select_related("exercise").order_by(
            "position", "id"
        ),
    )
    workout = (
        Workout.objects.filter(is_archived=False, pk=workout_id)
        .prefetch_related(ordered_entries)
        .first()
    )
    if workout is None:
        raise NotFound()
    return workout
