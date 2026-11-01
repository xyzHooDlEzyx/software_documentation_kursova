"""G01–G06 REST, isolation, copy, rollback and PostgreSQL concurrency tests."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Barrier, Event
from time import sleep
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import connections, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Profile
from catalog.models import (
    Exercise,
    ExerciseCategory,
    ProgramTemplate,
    ProgramTemplateStatus,
    ProgramTemplateWorkout,
    Workout,
    WorkoutExercise,
)
from planning.models import UserProgram, UserProgramExercise, UserProgramWorkout
from planning.services import ProgramPlanningService, ProgramSelectionService

User = get_user_model()
RECOMMEND_URL = "/api/v1/program-recommendation/"
PROGRAMS_URL = "/api/v1/user-programs/"


def client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def composition_url(program_id, entry_id):
    return f"/api/v1/user-programs/{program_id}/workouts/{entry_id}/"


def strength_item(exercise_id, *, position=1, sets=3):
    return {
        "position": position,
        "exercise_id": exercise_id,
        "recommended_sets": sets,
        "recommended_reps": 8,
        "recommended_load_kg": "20.0",
        "recommended_duration_min": None,
        "recommended_distance_km": None,
    }


@pytest.fixture
def catalog_and_users(db):
    owner = User.objects.create_user("owner@example.test", "SafePassword2026!")
    other = User.objects.create_user("other@example.test", "SafePassword2026!")
    Profile.objects.create(
        user=owner,
        date_of_birth=date(1998, 5, 14),
        weight_kg=Decimal("75.0"),
        height_cm=Decimal("175.0"),
        gender="female",
        fitness_goal="weight_loss",
        experience_level="beginner",
        workouts_per_week=3,
    )
    strength = Exercise.objects.create(
        name="Присідання", category=ExerciseCategory.STRENGTH
    )
    extra_strength = Exercise.objects.create(
        name="Випади", category=ExerciseCategory.STRENGTH
    )
    cardio = Exercise.objects.create(name="Біг", category=ExerciseCategory.CARDIO)
    strength_workout = Workout.objects.create(
        name="Силовий блок", category=ExerciseCategory.STRENGTH
    )
    cardio_workout = Workout.objects.create(
        name="Кардіо блок", category=ExerciseCategory.CARDIO
    )
    WorkoutExercise.objects.create(
        workout=strength_workout,
        exercise=strength,
        position=1,
        recommended_sets=3,
        recommended_reps=8,
        recommended_load_kg=Decimal("20.0"),
    )
    WorkoutExercise.objects.create(
        workout=strength_workout,
        exercise=strength,
        position=2,
        recommended_sets=4,
        recommended_reps=6,
        recommended_load_kg=Decimal("30.0"),
    )
    WorkoutExercise.objects.create(
        workout=cardio_workout,
        exercise=cardio,
        position=1,
        recommended_duration_min=Decimal("20.00"),
    )
    winner = ProgramTemplate.objects.create(
        name="Кардіо перевага",
        description="Перший опис",
        fitness_goal="weight_loss",
        experience_level="beginner",
        workouts_per_week=3,
        status=ProgramTemplateStatus.PUBLISHED,
    )
    ProgramTemplateWorkout.objects.create(
        program_template=winner, workout=cardio_workout, position=1
    )
    ProgramTemplateWorkout.objects.create(
        program_template=winner, workout=strength_workout, position=2
    )
    ProgramTemplateWorkout.objects.create(
        program_template=winner, workout=cardio_workout, position=3
    )
    loser = ProgramTemplate.objects.create(
        name="Силова перевага",
        fitness_goal="weight_loss",
        experience_level="beginner",
        workouts_per_week=3,
        status=ProgramTemplateStatus.PUBLISHED,
    )
    ProgramTemplateWorkout.objects.create(
        program_template=loser, workout=strength_workout, position=1
    )
    return {
        "owner": owner,
        "other": other,
        "winner": winner,
        "loser": loser,
        "strength": strength,
        "extra_strength": extra_strength,
        "cardio": cardio,
        "strength_workout": strength_workout,
        "cardio_workout": cardio_workout,
    }


def create_personal_program(data):
    return ProgramSelectionService.create_user_program_from_template(
        data["owner"], data["winner"].pk
    )


@pytest.mark.django_db
def test_g01_uses_profile_and_strategy_without_writes(catalog_and_users):
    data = catalog_and_users
    client = client_for(data["owner"])
    before = UserProgram.objects.count()
    response = client.get(RECOMMEND_URL)
    assert response.status_code == 200
    body = response.json()
    assert body["program_template"]["id"] == data["winner"].pk
    assert body["reason"] == {
        "exact_goal": True,
        "exact_level": True,
        "frequency_difference": 0,
        "strategy": "WeightLossSelectionStrategy",
        "composition_criterion": "Максимальна частка вправ cardio",
    }
    assert UserProgram.objects.count() == before
    assert client.get(RECOMMEND_URL).json() == body
    assert client.get(RECOMMEND_URL + "?fitness_goal=muscle_gain").status_code == 400


@pytest.mark.django_db
def test_g01_missing_profile_and_no_candidate(catalog_and_users):
    data = catalog_and_users
    missing = client_for(data["other"]).get(RECOMMEND_URL)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "profile_missing"
    ProgramTemplate.objects.update(status=ProgramTemplateStatus.ARCHIVED)
    unavailable = client_for(data["owner"]).get(RECOMMEND_URL)
    assert unavailable.status_code == 404
    assert unavailable.json()["error"]["code"] == "recommendation_unavailable"
    assert UserProgram.objects.count() == 0


@pytest.mark.django_db
def test_g03_deep_copy_preserves_repeated_occurrences_and_snapshots(catalog_and_users):
    data = catalog_and_users
    response = client_for(data["owner"]).post(
        PROGRAMS_URL, {"program_template_id": data["winner"].pk}, format="json"
    )
    assert response.status_code == 201
    body = response.json()
    program = UserProgram.objects.get(pk=body["id"])
    assert program.status == "draft"
    assert program.fitness_goal == "weight_loss"
    assert body["source_program_template_id"] == data["winner"].pk
    assert body["source_program_template_name_snapshot"] == "Кардіо перевага"
    assert [entry["position"] for entry in body["workouts"]] == [1, 2, 3]
    assert (
        body["workouts"][0]["source_workout_id"]
        == body["workouts"][2]["source_workout_id"]
    )
    strength_copy = body["workouts"][1]
    assert [entry["exercise_id"] for entry in strength_copy["exercises"]] == [
        data["strength"].pk,
        data["strength"].pk,
    ]
    assert strength_copy["exercises"][1]["recommended_load_kg"] == "30.0"

    data["winner"].name = "Змінена назва шаблону"
    data["winner"].save(update_fields=["name"])
    data["strength_workout"].name = "Змінена назва тренування"
    data["strength_workout"].save(update_fields=["name"])
    WorkoutExercise.objects.filter(workout=data["strength_workout"], position=2).update(
        recommended_load_kg=Decimal("99.0")
    )
    detail = client_for(data["owner"]).get(f"{PROGRAMS_URL}{program.pk}/")
    assert detail.status_code == 200
    assert detail.json()["source_program_template_name_snapshot"] == "Кардіо перевага"
    assert detail.json()["workouts"][1]["name"] == "Силовий блок"
    assert detail.json()["workouts"][1]["exercises"][1]["recommended_load_kg"] == "30.0"


@pytest.mark.django_db
def test_g03_rejects_stale_missing_and_archived_template(catalog_and_users):
    data = catalog_and_users
    client = client_for(data["owner"])
    stale = client.post(
        PROGRAMS_URL, {"program_template_id": data["loser"].pk}, format="json"
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "recommendation_mismatch"
    assert (
        client.post(
            PROGRAMS_URL, {"program_template_id": 999999}, format="json"
        ).status_code
        == 404
    )
    data["loser"].status = ProgramTemplateStatus.ARCHIVED
    data["loser"].save(update_fields=["status"])
    assert (
        client.post(
            PROGRAMS_URL, {"program_template_id": data["loser"].pk}, format="json"
        ).status_code
        == 404
    )
    assert UserProgram.objects.count() == 0


@pytest.mark.django_db
def test_g03_copy_rolls_back_when_child_insert_fails(catalog_and_users):
    data = catalog_and_users
    with patch.object(
        UserProgramExercise.objects, "create", side_effect=RuntimeError("copy failed")
    ):
        with pytest.raises(RuntimeError, match="copy failed"):
            create_personal_program(data)
    assert UserProgram.objects.count() == 0
    assert UserProgramWorkout.objects.count() == 0
    assert UserProgramExercise.objects.count() == 0


@pytest.mark.django_db
def test_g02_filters_paginates_and_isolates_owner(catalog_and_users):
    data = catalog_and_users
    first = create_personal_program(data)
    second = create_personal_program(data)
    UserProgram.objects.filter(pk=first.pk).update(is_archived=True)
    client = client_for(data["owner"])
    visible = client.get(PROGRAMS_URL)
    assert visible.status_code == 200
    assert visible.json()["count"] == 1
    assert visible.json()["results"][0]["id"] == second.pk
    assert visible.json()["results"][0]["progress_percent"] == "0.0"
    assert visible.json()["results"][0]["bonus_earned"] is False
    archived = client.get(PROGRAMS_URL + "?archived=true")
    assert archived.json()["results"][0]["id"] == first.pk
    assert client.get(PROGRAMS_URL + "?status=completed").json()["count"] == 0
    assert client.get(PROGRAMS_URL + "?page_size=0").status_code == 400
    assert client.get(PROGRAMS_URL + "?unknown=1").status_code == 400
    assert client_for(data["other"]).get(PROGRAMS_URL).json()["count"] == 0


@pytest.mark.django_db
def test_g02_descending_id_pagination(catalog_and_users):
    data = catalog_and_users
    first = create_personal_program(data)
    second = create_personal_program(data)
    client = client_for(data["owner"])
    page_one = client.get(PROGRAMS_URL + "?page=1&page_size=1")
    page_two = client.get(PROGRAMS_URL + "?page=2&page_size=1")
    assert page_one.status_code == page_two.status_code == 200
    assert page_one.json()["count"] == page_two.json()["count"] == 2
    assert [item["id"] for item in page_one.json()["results"]] == [second.pk]
    assert [item["id"] for item in page_two.json()["results"]] == [first.pk]
    assert page_one.json()["next"] is not None
    assert page_two.json()["previous"] is not None
    assert client.get(PROGRAMS_URL + "?page=3&page_size=1").status_code == 400


@pytest.mark.django_db
def test_g04_detail_is_private_and_shows_draft_zero_state(catalog_and_users):
    data = catalog_and_users
    program = create_personal_program(data)
    path = f"{PROGRAMS_URL}{program.pk}/"
    detail = client_for(data["owner"]).get(path)
    assert detail.status_code == 200
    assert detail.json()["progress"] == {
        "total_planned": 0,
        "completed_planned": 0,
        "percent": "0.0",
    }
    assert detail.json()["completion_snapshot"] is None
    assert detail.json()["bonus_earned"] is False
    assert client_for(data["other"]).get(path).status_code == 404
    assert client_for(data["owner"]).get(f"{PROGRAMS_URL}999999/").status_code == 404


@pytest.mark.django_db
def test_g05_only_edits_owned_metadata(catalog_and_users):
    data = catalog_and_users
    program = create_personal_program(data)
    path = f"{PROGRAMS_URL}{program.pk}/"
    owner_client = client_for(data["owner"])
    changed = owner_client.patch(path, {"name": "Новий план"}, format="json")
    assert changed.status_code == 200
    program.refresh_from_db()
    assert program.name == "Новий план"
    assert program.description == "Перший опис"
    assert (
        owner_client.patch(path, {"status": "completed"}, format="json").status_code
        == 400
    )
    assert owner_client.patch(path, {"name": "   "}, format="json").status_code == 400
    assert (
        client_for(data["other"])
        .patch(path, {"name": "Злам"}, format="json")
        .status_code
        == 404
    )
    program.refresh_from_db()
    assert program.name == "Новий план"


@pytest.mark.django_db
def test_g05_and_g06_reject_archived_program(catalog_and_users):
    data = catalog_and_users
    program = create_personal_program(data)
    occurrence = program.workouts.get(position=2)
    UserProgram.objects.filter(pk=program.pk).update(is_archived=True)
    client = client_for(data["owner"])
    edit = client.patch(
        f"{PROGRAMS_URL}{program.pk}/", {"name": "Не дозволено"}, format="json"
    )
    replace = client.put(
        composition_url(program.pk, occurrence.pk),
        {"name": "Не дозволено", "exercises": [strength_item(data["strength"].pk)]},
        format="json",
    )
    assert edit.status_code == replace.status_code == 409
    assert edit.json()["error"]["code"] == "invalid_state"
    assert replace.json()["error"]["code"] == "invalid_state"
    occurrence.refresh_from_db()
    assert occurrence.name == "Силовий блок"


@pytest.mark.django_db
def test_g06_replaces_only_personal_composition(catalog_and_users):
    data = catalog_and_users
    program = create_personal_program(data)
    occurrence = program.workouts.get(position=2)
    path = composition_url(program.pk, occurrence.pk)
    original_source_id = occurrence.source_workout_id
    original_category = occurrence.category
    original_shared = list(
        WorkoutExercise.objects.filter(workout=data["strength_workout"]).values_list(
            "exercise_id", "position", "recommended_sets"
        )
    )
    changed = client_for(data["owner"]).put(
        path,
        {
            "name": "Особистий блок",
            "exercises": [strength_item(data["extra_strength"].pk)],
        },
        format="json",
    )
    assert changed.status_code == 200
    assert changed.json()["name"] == "Особистий блок"
    occurrence.refresh_from_db()
    assert occurrence.source_workout_id == original_source_id
    assert occurrence.category == original_category
    assert list(occurrence.exercises.values_list("exercise_id", flat=True)) == [
        data["extra_strength"].pk
    ]
    assert (
        list(
            WorkoutExercise.objects.filter(
                workout=data["strength_workout"]
            ).values_list("exercise_id", "position", "recommended_sets")
        )
        == original_shared
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        {"name": "x", "exercises": []},
        {"name": "x", "exercises": [{"position": 1, "exercise_id": 999999}]},
        {"name": "x", "exercises": [{"position": 2, "exercise_id": 1}]},
        {
            "name": "x",
            "exercises": [{"position": 1, "exercise_id": 1, "unexpected": 2}],
        },
        {"name": "x", "exercises": [], "source_workout_id": 1},
    ],
)
def test_g06_rejects_invalid_payload_without_mutation(catalog_and_users, payload):
    data = catalog_and_users
    program = create_personal_program(data)
    occurrence = program.workouts.get(position=2)
    path = composition_url(program.pk, occurrence.pk)
    before = list(occurrence.exercises.values_list("exercise_id", "position"))
    response = client_for(data["owner"]).put(path, payload, format="json")
    assert response.status_code == 400
    occurrence.refresh_from_db()
    assert occurrence.name == "Силовий блок"
    assert list(occurrence.exercises.values_list("exercise_id", "position")) == before


@pytest.mark.django_db
def test_g06_category_validation_and_foreign_entries(catalog_and_users):
    data = catalog_and_users
    program = create_personal_program(data)
    occurrence = program.workouts.get(position=2)
    path = composition_url(program.pk, occurrence.pk)
    invalid = client_for(data["owner"]).put(
        path,
        {
            "name": "Не валідний",
            "exercises": [
                {**strength_item(data["strength"].pk), "recommended_sets": None}
            ],
        },
        format="json",
    )
    assert invalid.status_code == 400
    other_client = client_for(data["other"])
    assert (
        other_client.put(
            path,
            {"name": "x", "exercises": [strength_item(data["strength"].pk)]},
            format="json",
        ).status_code
        == 404
    )
    assert (
        client_for(data["owner"])
        .put(
            composition_url(program.pk, 999999),
            {"name": "x", "exercises": [strength_item(data["strength"].pk)]},
            format="json",
        )
        .status_code
        == 404
    )


@pytest.mark.django_db
def test_g06_rejects_archived_exercise_without_changing_personal_copy(
    catalog_and_users,
):
    data = catalog_and_users
    program = create_personal_program(data)
    occurrence = program.workouts.get(position=2)
    before = list(occurrence.exercises.values_list("exercise_id", "position"))
    data["extra_strength"].is_archived = True
    data["extra_strength"].save(update_fields=["is_archived"])

    response = client_for(data["owner"]).put(
        composition_url(program.pk, occurrence.pk),
        {
            "name": "Архівована вправа",
            "exercises": [strength_item(data["extra_strength"].pk)],
        },
        format="json",
    )
    assert response.status_code == 400
    occurrence.refresh_from_db()
    assert occurrence.name == "Силовий блок"
    assert list(occurrence.exercises.values_list("exercise_id", "position")) == before


@pytest.mark.django_db
def test_g05_g06_reject_completed_and_entry_from_another_program(catalog_and_users):
    data = catalog_and_users
    first = create_personal_program(data)
    second = create_personal_program(data)
    foreign_entry = second.workouts.get(position=2)
    first_entry = first.workouts.get(position=2)
    client = client_for(data["owner"])
    request = {
        "name": "Інший склад",
        "exercises": [strength_item(data["strength"].pk)],
    }
    assert (
        client.put(
            composition_url(first.pk, foreign_entry.pk), request, format="json"
        ).status_code
        == 404
    )

    now = timezone.now()
    UserProgram.objects.filter(pk=first.pk).update(
        status="completed",
        activated_at=now,
        bonus_target_sessions=3,
        completed_at=now,
        total_planned_at_completion=1,
        completed_planned_at_completion=1,
        progress_percent_at_completion=Decimal("100.0"),
    )
    metadata = client.patch(
        f"{PROGRAMS_URL}{first.pk}/", {"name": "Закрита"}, format="json"
    )
    composition = client.put(
        composition_url(first.pk, first_entry.pk), request, format="json"
    )
    assert metadata.status_code == composition.status_code == 409
    assert metadata.json()["error"]["code"] == "invalid_state"
    assert composition.json()["error"]["code"] == "invalid_state"
    first_entry.refresh_from_db()
    assert first_entry.name == "Силовий блок"


@pytest.mark.django_db
def test_g06_requires_explicit_nullable_fields(catalog_and_users):
    data = catalog_and_users
    program = create_personal_program(data)
    occurrence = program.workouts.get(position=2)
    item = strength_item(data["strength"].pk)
    item.pop("recommended_distance_km")
    response = client_for(data["owner"]).put(
        composition_url(program.pk, occurrence.pk),
        {"name": "Силовий блок", "exercises": [item]},
        format="json",
    )
    assert response.status_code == 400
    assert occurrence.exercises.count() == 2


@pytest.mark.django_db
def test_g06_positions_define_order_independent_of_request_order(catalog_and_users):
    data = catalog_and_users
    program = create_personal_program(data)
    occurrence = program.workouts.get(position=2)
    response = client_for(data["owner"]).put(
        composition_url(program.pk, occurrence.pk),
        {
            "name": "Силовий блок",
            "exercises": [
                strength_item(data["extra_strength"].pk, position=2),
                strength_item(data["strength"].pk, position=1),
            ],
        },
        format="json",
    )
    assert response.status_code == 200
    assert [entry["exercise_id"] for entry in response.json()["exercises"]] == [
        data["strength"].pk,
        data["extra_strength"].pk,
    ]


@pytest.mark.django_db
def test_g06_rolls_back_name_and_children_on_insert_failure(catalog_and_users):
    data = catalog_and_users
    program = create_personal_program(data)
    occurrence = program.workouts.get(position=2)
    before = list(occurrence.exercises.values_list("exercise_id", "position"))
    with patch.object(
        UserProgramExercise.objects, "create", side_effect=RuntimeError("insert failed")
    ):
        with pytest.raises(RuntimeError, match="insert failed"):
            ProgramPlanningService.replace_workout_composition(
                data["owner"],
                program.pk,
                occurrence.pk,
                name="Змінена назва",
                exercises_data=[strength_item(data["extra_strength"].pk)],
            )
    occurrence.refresh_from_db()
    assert occurrence.name == "Силовий блок"
    assert list(occurrence.exercises.values_list("exercise_id", "position")) == before


@pytest.mark.django_db
def test_g01_to_g06_authentication_and_csrf(catalog_and_users):
    data = catalog_and_users
    anon = APIClient()
    assert anon.get(RECOMMEND_URL).status_code == 401
    assert anon.get(PROGRAMS_URL).status_code == 401
    assert anon.post(PROGRAMS_URL, {}, format="json").status_code == 401
    program = create_personal_program(data)
    assert anon.get(f"{PROGRAMS_URL}{program.pk}/").status_code == 401

    client = APIClient(enforce_csrf_checks=True)
    client.force_login(data["owner"])
    forbidden = client.patch(
        f"{PROGRAMS_URL}{program.pk}/", {"name": "Без токена"}, format="json"
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "csrf_failed"
    assert client.get("/api/v1/auth/csrf/").status_code == 200
    allowed = client.patch(
        f"{PROGRAMS_URL}{program.pk}/",
        {"name": "Із токеном"},
        format="json",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )
    assert allowed.status_code == 200


@pytest.mark.django_db(transaction=True)
def test_concurrent_g03_requests_create_two_complete_copies(catalog_and_users):
    data = catalog_and_users
    barrier = Barrier(2)

    def create_copy():
        connections.close_all()
        try:
            barrier.wait(timeout=5)
            return ProgramSelectionService.create_user_program_from_template(
                User.objects.get(pk=data["owner"].pk), data["winner"].pk
            ).pk
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(lambda _: create_copy(), range(2)))
    assert len(set(ids)) == 2
    for program in UserProgram.objects.filter(pk__in=ids):
        assert program.workouts.count() == 3
        assert (
            UserProgramExercise.objects.filter(
                user_program_workout__user_program=program
            ).count()
            == 4
        )


@pytest.mark.django_db(transaction=True)
def test_concurrent_g06_replacements_are_serialized(catalog_and_users):
    data = catalog_and_users
    program = create_personal_program(data)
    occurrence = program.workouts.get(position=2)
    barrier = Barrier(2)

    def replace(name, exercise_id):
        connections.close_all()
        try:
            barrier.wait(timeout=5)
            ProgramPlanningService.replace_workout_composition(
                User.objects.get(pk=data["owner"].pk),
                program.pk,
                occurrence.pk,
                name=name,
                exercises_data=[strength_item(exercise_id)],
            )
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(replace, "Перший", data["strength"].pk),
            pool.submit(replace, "Другий", data["extra_strength"].pk),
        ]
        for future in futures:
            future.result(timeout=15)
    occurrence.refresh_from_db()
    assert occurrence.name in {"Перший", "Другий"}
    assert occurrence.exercises.count() == 1
    assert occurrence.exercises.get().exercise_id in {
        data["strength"].pk,
        data["extra_strength"].pk,
    }


@pytest.mark.django_db(transaction=True)
def test_g03_waits_for_catalog_change_and_copies_one_committed_version(
    catalog_and_users,
):
    """A template/workout update commits before G03 reads a coherent source."""
    data = catalog_and_users
    locked = Event()
    release = Event()
    copy_started = Event()

    def change_catalog():
        connections.close_all()
        try:
            with transaction.atomic():
                template = ProgramTemplate.objects.select_for_update().get(
                    pk=data["winner"].pk
                )
                list(
                    Workout.objects.select_for_update().filter(
                        pk=data["strength_workout"].pk
                    )
                )
                locked.set()
                assert release.wait(timeout=10)
                template.name = "Оновлений шаблон"
                template.save(update_fields=["name"])
                WorkoutExercise.objects.filter(
                    workout_id=data["strength_workout"].pk, position=1
                ).update(recommended_sets=7)
        finally:
            connections.close_all()

    def copy_program():
        connections.close_all()
        try:
            copy_started.set()
            return ProgramSelectionService.create_user_program_from_template(
                User.objects.get(pk=data["owner"].pk), data["winner"].pk
            ).pk
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        writer = pool.submit(change_catalog)
        assert locked.wait(timeout=5)
        copier = pool.submit(copy_program)
        assert copy_started.wait(timeout=5)
        try:
            sleep(0.08)
            assert not copier.done(), "G03 must wait for the locked source template"
        finally:
            release.set()
        writer.result(timeout=10)
        program_id = copier.result(timeout=10)

    program = UserProgram.objects.get(pk=program_id)
    assert program.source_program_template_name_snapshot == "Оновлений шаблон"
    assert program.name == "Оновлений шаблон"
    copied_workout = program.workouts.get(position=2)
    assert copied_workout.exercises.get(position=1).recommended_sets == 7
    assert copied_workout.exercises.get(position=2).recommended_sets == 4


@pytest.mark.django_db(transaction=True)
def test_g06_waits_for_exercise_archive_and_rejects_without_mutation(
    catalog_and_users,
):
    """An archived Exercise must not enter a personal copy after a row-lock race."""
    data = catalog_and_users
    program = create_personal_program(data)
    occurrence = program.workouts.get(position=2)
    before = list(occurrence.exercises.values_list("exercise_id", "position"))
    locked = Event()
    release = Event()
    replace_started = Event()

    def archive_exercise():
        connections.close_all()
        try:
            with transaction.atomic():
                exercise = Exercise.objects.select_for_update().get(
                    pk=data["extra_strength"].pk
                )
                locked.set()
                assert release.wait(timeout=10)
                exercise.is_archived = True
                exercise.save(update_fields=["is_archived"])
        finally:
            connections.close_all()

    def replace_composition():
        connections.close_all()
        try:
            replace_started.set()
            client = client_for(User.objects.get(pk=data["owner"].pk))
            return client.put(
                composition_url(program.pk, occurrence.pk),
                {
                    "name": "Нова назва",
                    "exercises": [strength_item(data["extra_strength"].pk)],
                },
                format="json",
            ).status_code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        archiver = pool.submit(archive_exercise)
        assert locked.wait(timeout=5)
        replacer = pool.submit(replace_composition)
        assert replace_started.wait(timeout=5)
        try:
            sleep(0.08)
            assert not replacer.done(), "G06 must wait for the locked Exercise"
        finally:
            release.set()
        archiver.result(timeout=10)
        assert replacer.result(timeout=10) == 400

    occurrence.refresh_from_db()
    assert occurrence.name == "Силовий блок"
    assert list(occurrence.exercises.values_list("exercise_id", "position")) == before
