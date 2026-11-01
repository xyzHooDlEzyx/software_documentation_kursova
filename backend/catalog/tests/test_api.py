from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from catalog.models import (
    Exercise,
    ExerciseCategory,
    Workout,
    WorkoutExercise,
)

User = get_user_model()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(
        email="client@fitness.local",
        password="UserPass12345!",
        is_active=True,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def unauth_client():
    return APIClient()


@pytest.fixture
def catalog_fixture(db):
    ex_squat = Exercise.objects.create(
        name="Присідання",
        category=ExerciseCategory.STRENGTH,
        met_value=Decimal("5.00"),
        met_activity_code="02052",
        met_reference_version="Compendium 2024",
        met_activity_description="squats",
    )
    ex_run = Exercise.objects.create(
        name="Біг",
        category=ExerciseCategory.CARDIO,
        met_value=Decimal("9.80"),
        met_activity_code="12020",
        met_reference_version="Compendium 2024",
        met_activity_description="running",
    )
    ex_archived = Exercise.objects.create(
        name="Застаріла вправа",
        category=ExerciseCategory.YOGA,
        is_archived=True,
    )

    workout_active = Workout.objects.create(
        name="Силове А",
        category=ExerciseCategory.STRENGTH,
        description="Активне силове",
    )
    we = WorkoutExercise.objects.create(
        workout=workout_active,
        exercise=ex_squat,
        position=1,
        recommended_sets=4,
        recommended_reps=10,
        recommended_load_kg=Decimal("70.0"),
    )

    workout_archived = Workout.objects.create(
        name="Архівоване тренування",
        category=ExerciseCategory.CARDIO,
        is_archived=True,
    )
    WorkoutExercise.objects.create(
        workout=workout_archived,
        exercise=ex_run,
        position=1,
        recommended_duration_min=Decimal("20.00"),
    )

    return {
        "ex_squat": ex_squat,
        "ex_run": ex_run,
        "ex_archived": ex_archived,
        "workout_active": workout_active,
        "workout_archived": workout_archived,
        "workout_exercise": we,
    }


@pytest.mark.django_db
class TestCatalogAPI:
    """Tests C01–C04 endpoints, permissions, pagination, and filtering."""

    # --- C01: Categories ---
    def test_c01_unauthenticated_returns_401(self, unauth_client):
        res = unauth_client.get("/api/v1/categories/")
        assert res.status_code == 401

    def test_c01_returns_static_categories(self, auth_client):
        res = auth_client.get("/api/v1/categories/")
        assert res.status_code == 200
        assert "results" in res.data
        codes = [item["code"] for item in res.data["results"]]
        assert codes == ["cardio", "strength", "yoga"]

    def test_c01_rejects_query_parameters(self, auth_client):
        res = auth_client.get("/api/v1/categories/?foo=bar")
        assert res.status_code == 400
        assert res.data["error"]["code"] == "unknown_field"

    def test_c01_rejects_unsafe_methods(self, auth_client):
        res = auth_client.post("/api/v1/categories/", data={})
        assert res.status_code == 405

    # --- C02: Exercises ---
    def test_c02_unauthenticated_returns_401(self, unauth_client):
        res = unauth_client.get("/api/v1/exercises/")
        assert res.status_code == 401

    def test_c02_lists_active_exercises_and_excludes_archived(
        self, auth_client, catalog_fixture
    ):
        res = auth_client.get("/api/v1/exercises/")
        assert res.status_code == 200
        assert res.data["count"] == 2
        names = [item["name"] for item in res.data["results"]]
        assert "Присідання" in names
        assert "Біг" in names
        assert "Застаріла вправа" not in names

    def test_c02_filtering_by_category_and_search(self, auth_client, catalog_fixture):
        # Filter by category
        res = auth_client.get("/api/v1/exercises/?category=strength")
        assert res.status_code == 200
        assert res.data["count"] == 1
        assert res.data["results"][0]["name"] == "Присідання"

        # Search by name
        res = auth_client.get("/api/v1/exercises/?search=Біг")
        assert res.status_code == 200
        assert res.data["count"] == 1
        assert res.data["results"][0]["name"] == "Біг"

    def test_c02_rejects_invalid_category(self, auth_client):
        res = auth_client.get("/api/v1/exercises/?category=invalid")
        assert res.status_code == 400
        assert res.data["error"]["code"] == "validation_error"

    def test_c02_rejects_unknown_query_parameters(self, auth_client):
        res = auth_client.get("/api/v1/exercises/?unexpected=value")
        assert res.status_code == 400

    # --- C03: Workouts ---
    def test_c03_unauthenticated_returns_401(self, unauth_client):
        res = unauth_client.get("/api/v1/workouts/")
        assert res.status_code == 401

    def test_c03_lists_active_workouts_with_exercise_count(
        self, auth_client, catalog_fixture
    ):
        res = auth_client.get("/api/v1/workouts/")
        assert res.status_code == 200
        assert res.data["count"] == 1  # only active workout
        workout_data = res.data["results"][0]
        assert workout_data["name"] == "Силове А"
        assert workout_data["exercise_count"] == 1

    def test_c03_rejects_unsafe_methods(self, auth_client):
        res = auth_client.post("/api/v1/workouts/", data={"name": "Нове"})
        assert res.status_code == 405

    # --- C04: Workout Details ---
    def test_c04_unauthenticated_returns_401(self, unauth_client, catalog_fixture):
        w_id = catalog_fixture["workout_active"].pk
        res = unauth_client.get(f"/api/v1/workouts/{w_id}/")
        assert res.status_code == 401

    def test_c04_returns_workout_detail_and_composition(
        self, auth_client, catalog_fixture
    ):
        w_id = catalog_fixture["workout_active"].pk
        res = auth_client.get(f"/api/v1/workouts/{w_id}/")
        assert res.status_code == 200
        assert res.data["id"] == w_id
        assert res.data["name"] == "Силове А"
        assert len(res.data["exercises"]) == 1

        ex_item = res.data["exercises"][0]
        assert ex_item["position"] == 1
        assert ex_item["entry_id"] == catalog_fixture["workout_exercise"].pk
        assert ex_item["exercise"]["name"] == "Присідання"
        assert ex_item["recommended_sets"] == 4
        assert ex_item["recommended_reps"] == 10
        assert ex_item["recommended_load_kg"] == "70.0"

    def test_c04_archived_workout_returns_404(self, auth_client, catalog_fixture):
        w_id = catalog_fixture["workout_archived"].pk
        res = auth_client.get(f"/api/v1/workouts/{w_id}/")
        assert res.status_code == 404
        assert res.data["error"]["code"] == "not_found"

    def test_c04_non_existent_workout_returns_404(self, auth_client):
        res = auth_client.get("/api/v1/workouts/99999/")
        assert res.status_code == 404
        assert res.data["error"]["code"] == "not_found"

    def test_c04_rejects_query_parameters(self, auth_client, catalog_fixture):
        w_id = catalog_fixture["workout_active"].pk
        res = auth_client.get(f"/api/v1/workouts/{w_id}/?foo=bar")
        assert res.status_code == 400

    def test_c04_rejects_unsafe_methods(self, auth_client, catalog_fixture):
        w_id = catalog_fixture["workout_active"].pk
        res = auth_client.delete(f"/api/v1/workouts/{w_id}/")
        assert res.status_code == 405
