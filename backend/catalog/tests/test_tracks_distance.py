"""Exercise.tracks_distance: which cardio exercises may carry a distance (BR-004)."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient

from catalog.models import Exercise, ExerciseCategory, Workout, WorkoutExercise
from catalog.services import CatalogPublicationService

User = get_user_model()


def cardio_workout_with(exercise, **params):
    workout = Workout.objects.create(name="Кардіо", category=ExerciseCategory.CARDIO)
    WorkoutExercise.objects.create(
        workout=workout, exercise=exercise, position=1, **params
    )
    return workout


@pytest.mark.django_db
def test_database_allows_distance_tracking_only_for_cardio():
    with pytest.raises(IntegrityError), transaction.atomic():
        Exercise.objects.create(
            name="Жим", category=ExerciseCategory.STRENGTH, tracks_distance=True
        )
    assert Exercise.objects.create(
        name="Біг", category=ExerciseCategory.CARDIO, tracks_distance=True
    ).tracks_distance


@pytest.mark.django_db
def test_distance_is_rejected_for_duration_only_cardio():
    rope = Exercise.objects.create(name="Скакалка", category=ExerciseCategory.CARDIO)
    workout = Workout.objects.create(name="Кардіо", category=ExerciseCategory.CARDIO)
    entry = WorkoutExercise(
        workout=workout,
        exercise=rope,
        position=1,
        recommended_distance_km=Decimal("2.000"),
    )
    with pytest.raises(ValidationError) as exc:
        CatalogPublicationService.validate_workout_exercise_parameters(entry)
    assert "recommended_distance_km" in exc.value.message_dict

    entry.recommended_distance_km = None
    entry.recommended_duration_min = Decimal("10.00")
    CatalogPublicationService.validate_workout_exercise_parameters(entry)


@pytest.mark.django_db
def test_turning_off_distance_is_blocked_while_active_workouts_use_it():
    run = Exercise.objects.create(
        name="Біг", category=ExerciseCategory.CARDIO, tracks_distance=True
    )
    workout = cardio_workout_with(run, recommended_distance_km=Decimal("5.000"))

    with pytest.raises(ValidationError) as exc:
        CatalogPublicationService.validate_exercise_distance_change(
            run, tracks_distance=False
        )
    assert "tracks_distance" in exc.value.message_dict

    workout.is_archived = True
    workout.save(update_fields=["is_archived"])
    CatalogPublicationService.validate_exercise_distance_change(
        run, tracks_distance=False
    )


@pytest.mark.django_db
def test_admin_form_rejects_turning_off_distance_in_use(client: Client):
    admin = User.objects.create_user(
        email="admin@fitness.local", password="AdminSecurePassword123!", is_staff=True
    )
    admin.groups.add(Group.objects.get(name="Administrator"))
    run = Exercise.objects.create(
        name="Біг", category=ExerciseCategory.CARDIO, tracks_distance=True
    )
    cardio_workout_with(run, recommended_distance_km=Decimal("5.000"))
    client.force_login(admin)

    response = client.post(
        reverse("admin:catalog_exercise_change", args=[run.pk]),
        {
            "name": "Біг",
            "description": "",
            "category": ExerciseCategory.CARDIO,
            "_save": "Save",
        },
    )
    assert response.status_code == 200
    assert "tracks_distance" in response.context["adminform"].form.errors
    run.refresh_from_db()
    assert run.tracks_distance


@pytest.mark.django_db
def test_seed_marks_running_and_cycling_but_not_rope_jumping():
    call_command("seed_catalog", stdout=open("/dev/null", "w"))
    flags = dict(
        Exercise.objects.filter(category=ExerciseCategory.CARDIO).values_list(
            "name", "tracks_distance"
        )
    )
    assert flags == {
        "Біг на біговій доріжці": True,
        "Велотренажер": True,
        "Стрибки на скакалці": False,
    }


@pytest.mark.django_db
def test_catalog_api_exposes_tracks_distance():
    user = User.objects.create_user("reader@example.test", "SafePassword2026!")
    client = APIClient()
    client.force_authenticate(user)
    run = Exercise.objects.create(
        name="Біг", category=ExerciseCategory.CARDIO, tracks_distance=True
    )
    workout = cardio_workout_with(run, recommended_distance_km=Decimal("5.000"))

    exercises = client.get("/api/v1/exercises/").json()["results"]
    assert exercises[0]["tracks_distance"] is True
    detail = client.get(f"/api/v1/workouts/{workout.pk}/").json()
    assert detail["exercises"][0]["exercise"]["tracks_distance"] is True


@pytest.mark.django_db(transaction=True)
def test_migration_marks_exercises_that_already_have_a_distance():
    executor = MigrationExecutor(connection)
    before = [("catalog", "0001_initial")]
    after = [("catalog", "0002_exercise_tracks_distance")]
    executor.migrate(before)
    old_apps = executor.loader.project_state(before).apps
    try:
        OldExercise = old_apps.get_model("catalog", "Exercise")
        OldWorkout = old_apps.get_model("catalog", "Workout")
        OldEntry = old_apps.get_model("catalog", "WorkoutExercise")
        run = OldExercise.objects.create(name="Біг", category="cardio")
        rope = OldExercise.objects.create(name="Скакалка", category="cardio")
        workout = OldWorkout.objects.create(name="Кардіо", category="cardio")
        OldEntry.objects.create(
            workout=workout,
            exercise=run,
            position=1,
            recommended_distance_km=Decimal("5.000"),
        )
        OldEntry.objects.create(
            workout=workout,
            exercise=rope,
            position=2,
            recommended_duration_min=Decimal("10.00"),
        )

        executor = MigrationExecutor(connection)
        executor.migrate(after)
        new_apps = executor.loader.project_state(after).apps
        NewExercise = new_apps.get_model("catalog", "Exercise")
        assert NewExercise.objects.get(name="Біг").tracks_distance is True
        assert NewExercise.objects.get(name="Скакалка").tracks_distance is False
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
