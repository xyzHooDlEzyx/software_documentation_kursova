from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from threading import Barrier
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.db import connections
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Profile, WeightEntry
from catalog.models import (
    Exercise,
    ExerciseCategory,
    ProgramTemplate,
    Workout,
    WorkoutExercise,
)
from engagement.models import Achievement, AchievementCode, PointKind, PointTransaction
from execution.models import CompletedSession, ExerciseResult
from planning.models import (
    Notification,
    ScheduledSession,
    UserProgram,
    UserProgramExercise,
    UserProgramWorkout,
)

User = get_user_model()
URL = "/api/v1/completed-sessions/"


def client(user):
    value = APIClient()
    value.force_authenticate(user=user)
    return value


@pytest.fixture
def phase7(db):
    user = User.objects.create_user("phase7@example.test", "SecurePass2026!")
    Profile.objects.create(
        user=user,
        date_of_birth=date(1990, 1, 1),
        weight_kg=Decimal("70.0"),
        height_cm=Decimal("170.0"),
        gender="other",
        fitness_goal="maintenance",
        experience_level="beginner",
        workouts_per_week=3,
    )
    WeightEntry.objects.create(
        user=user, measured_at=timezone.now() - timedelta(days=1), weight_kg="70.0"
    )
    exercise = Exercise.objects.create(
        name="Squat",
        category=ExerciseCategory.STRENGTH,
        met_value="5.00",
        met_activity_code="02052",
        met_reference_version="C2024",
        met_activity_description="Resistance",
    )
    workout = Workout.objects.create(name="Strength", category="strength")
    WorkoutExercise.objects.create(
        workout=workout,
        exercise=exercise,
        position=1,
        recommended_sets=3,
        recommended_reps=8,
    )
    template = ProgramTemplate.objects.create(
        name="Template",
        fitness_goal="maintenance",
        experience_level="beginner",
        workouts_per_week=3,
    )
    program = UserProgram.objects.create(
        user=user,
        source_program_template=template,
        name="Program",
        fitness_goal="maintenance",
        source_program_template_name_snapshot="Template",
        status="active",
        activated_at=timezone.now(),
        bonus_target_sessions=3,
    )
    entry = UserProgramWorkout.objects.create(
        user_program=program,
        source_workout=workout,
        position=1,
        name="Personal strength",
        category="strength",
    )
    UserProgramExercise.objects.create(
        user_program_workout=entry,
        exercise=exercise,
        position=1,
        recommended_sets=3,
        recommended_reps=8,
    )
    slot = ScheduledSession.objects.create(
        user=user,
        user_program=program,
        user_program_workout=entry,
        source_workout=workout,
        scheduled_at=timezone.now() - timedelta(minutes=5),
    )
    Notification.objects.create(
        user=user,
        scheduled_session=slot,
        visible_at=timezone.now() - timedelta(hours=1),
    )
    return locals()


def payload(phase7):
    return {
        "scheduled_session_id": phase7["slot"].pk,
        "source_workout_id": None,
        "duration_min": "45.00",
        "results": [
            {
                "position": 1,
                "exercise_id": phase7["exercise"].pk,
                "actual_sets": 3,
                "actual_reps": 8,
                "actual_load_kg": "20.0",
                "actual_duration_min": "45.00",
                "actual_distance_km": None,
            }
        ],
    }


def seed_achievements():
    for code in AchievementCode.values:
        Achievement.objects.get_or_create(
            code=code,
            defaults={"name": code, "description": "", "rule_code": code},
        )


def concurrent_post(*, user_id, url, body, barrier, key=None):
    connections.close_all()
    user = User.objects.get(pk=user_id)
    api = client(user)
    barrier.wait(timeout=10)
    kwargs = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
    response = api.post(url, body, format="json", **kwargs)
    connections.close_all()
    return response.status_code


@pytest.mark.django_db
def test_e01_atomic_fact_snapshots_ledger_and_idempotency(phase7):
    api = client(phase7["user"])
    key = str(uuid4())
    first = api.post(URL, payload(phase7), format="json", HTTP_IDEMPOTENCY_KEY=key)
    assert first.status_code == 201
    assert first["Location"].endswith(f"/{first.json()['id']}/")
    assert CompletedSession.objects.count() == ExerciseResult.objects.count() == 1
    assert (
        PointTransaction.objects.filter(point_kind=PointKind.WORKOUT_COMPLETION).count()
        == 1
    )
    phase7["slot"].refresh_from_db()
    phase7["program"].refresh_from_db()
    assert phase7["slot"].status == "completed"
    assert phase7["program"].status == "completed"

    retry = api.post(URL, payload(phase7), format="json", HTTP_IDEMPOTENCY_KEY=key)
    assert retry.status_code == 200
    assert retry.json()["id"] == first.json()["id"]
    changed = payload(phase7)
    changed["duration_min"] = "44.00"
    conflict = api.post(URL, changed, format="json", HTTP_IDEMPOTENCY_KEY=key)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "key", [None, "not-a-uuid", "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"]
)
def test_e01_rejects_missing_or_noncanonical_key(phase7, key):
    kwargs = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
    response = client(phase7["user"]).post(
        URL, payload(phase7), format="json", **kwargs
    )
    assert response.status_code == 400
    assert CompletedSession.objects.count() == 0


@pytest.mark.django_db
def test_e01_rejects_server_owned_fields(phase7):
    body = payload(phase7)
    body["points"] = 999
    response = client(phase7["user"]).post(
        URL, body, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4())
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unknown_field"


@pytest.mark.django_db
def test_e01_requires_profile_without_any_partial_write(phase7):
    Profile.objects.filter(user=phase7["user"]).delete()
    response = client(phase7["user"]).post(
        URL,
        payload(phase7),
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "profile_missing"
    assert not CompletedSession.objects.exists()
    assert not PointTransaction.objects.exists()
    phase7["slot"].refresh_from_db()
    assert phase7["slot"].status == "planned"


@pytest.mark.django_db
def test_e01_standalone_uses_shared_composition_and_has_no_program(phase7):
    body = payload(phase7)
    body["scheduled_session_id"] = None
    body["source_workout_id"] = phase7["workout"].pk
    response = client(phase7["user"]).post(
        URL, body, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4())
    )
    assert response.status_code == 201
    assert response.json()["scheduled_session_id"] is None
    assert response.json()["program"] is None
    phase7["slot"].refresh_from_db()
    assert phase7["slot"].status == "planned"


@pytest.mark.django_db
@pytest.mark.parametrize("set_null_personal_entry", [False, True])
def test_e01_program_slot_lock_handles_present_and_set_null_entry(
    phase7, set_null_personal_entry
):
    if set_null_personal_entry:
        phase7["entry"].delete()
        phase7["slot"].refresh_from_db()
        assert phase7["slot"].user_program_workout_id is None
    response = client(phase7["user"]).post(
        URL,
        payload(phase7),
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    assert response.status_code == 201
    fact = CompletedSession.objects.get(pk=response.json()["id"])
    assert fact.source_workout_id == phase7["workout"].pk
    assert fact.exercise_results.count() == 1


@pytest.mark.django_db
def test_e01_missing_historical_weight_returns_error_envelope_without_writes(phase7):
    WeightEntry.objects.filter(user=phase7["user"]).delete()
    response = client(phase7["user"]).post(
        URL,
        payload(phase7),
        format="json",
        HTTP_IDEMPOTENCY_KEY=str(uuid4()),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    assert "request_id" in response.json()["error"]
    assert not CompletedSession.objects.exists()
    assert not ExerciseResult.objects.exists()
    assert not PointTransaction.objects.exists()
    phase7["slot"].refresh_from_db()
    assert phase7["slot"].status == "planned"


@pytest.mark.django_db
def test_required_observer_failure_rolls_back_fact_slot_program_and_ledger(phase7):
    failing = Mock()
    failing.dispatch.side_effect = RuntimeError("required handler failed")
    with patch(
        "execution.services.default_workout_completed_dispatcher",
        return_value=failing,
    ):
        with pytest.raises(RuntimeError, match="required handler failed"):
            client(phase7["user"]).post(
                URL,
                payload(phase7),
                format="json",
                HTTP_IDEMPOTENCY_KEY=str(uuid4()),
            )
    assert not CompletedSession.objects.exists()
    assert not ExerciseResult.objects.exists()
    assert not PointTransaction.objects.exists()
    phase7["slot"].refresh_from_db()
    phase7["program"].refresh_from_db()
    assert phase7["slot"].status == "planned"
    assert phase7["program"].status == "active"


@pytest.mark.django_db
def test_s05_closes_zero_denominator_neither_program_nor_bonus(phase7):
    response = client(phase7["user"]).post(
        f"/api/v1/scheduled-sessions/{phase7['slot'].pk}/cancel/", {}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["reminder"]["status"] == "pending"
    assert response.json()["reminder"]["is_current"] is False
    phase7["program"].refresh_from_db()
    assert phase7["program"].status == "active"
    assert not PointTransaction.objects.exists()
    assert (
        client(phase7["user"])
        .post(
            f"/api/v1/scheduled-sessions/{phase7['slot'].pk}/cancel/", {}, format="json"
        )
        .status_code
        == 200
    )


@pytest.mark.django_db
def test_s05_before_visible_at_cancels_reminder(phase7):
    Notification.objects.filter(scheduled_session=phase7["slot"]).update(
        visible_at=timezone.now() + timedelta(hours=1)
    )
    response = client(phase7["user"]).post(
        f"/api/v1/scheduled-sessions/{phase7['slot'].pk}/cancel/", {}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["reminder"]["status"] == "cancelled"
    assert response.json()["reminder"]["is_current"] is False


@pytest.mark.django_db
def test_g09_planned_rejected_then_s05_allows_archive(phase7):
    program = phase7["program"]
    program.status = "draft"
    program.activated_at = None
    program.bonus_target_sessions = None
    program.save(update_fields=["status", "activated_at", "bonus_target_sessions"])
    url = f"/api/v1/user-programs/{program.pk}/archive/"
    api = client(phase7["user"])
    blocked = api.post(url, {}, format="json")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "planned_sessions_exist"
    assert (
        api.post(
            f"/api/v1/scheduled-sessions/{phase7['slot'].pk}/cancel/", {}, format="json"
        ).status_code
        == 200
    )
    assert api.post(url, {}, format="json").status_code == 200
    assert api.post(url, {}, format="json").status_code == 200


@pytest.mark.django_db(transaction=True)
def test_race_same_slot_two_keys_has_one_fact(phase7):
    seed_achievements()
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                concurrent_post,
                user_id=phase7["user"].pk,
                url=URL,
                body=payload(phase7),
                barrier=barrier,
                key=str(uuid4()),
            )
            for _ in range(2)
        ]
    assert sorted(item.result() for item in futures) == [201, 409]
    assert (
        CompletedSession.objects.filter(scheduled_session=phase7["slot"]).count() == 1
    )


@pytest.mark.django_db(transaction=True)
def test_race_same_key_returns_one_created_and_one_retry(phase7):
    seed_achievements()
    barrier = Barrier(2)
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                concurrent_post,
                user_id=phase7["user"].pk,
                url=URL,
                body=payload(phase7),
                barrier=barrier,
                key=key,
            )
            for _ in range(2)
        ]
    assert sorted(item.result() for item in futures) == [200, 201]
    assert CompletedSession.objects.filter(idempotency_key=key).count() == 1


@pytest.mark.django_db(transaction=True)
def test_t19_two_concurrent_slots_write_one_snapshot_and_at_most_one_bonus(phase7):
    seed_achievements()
    second = ScheduledSession.objects.create(
        user=phase7["user"],
        user_program=phase7["program"],
        user_program_workout=phase7["entry"],
        source_workout=phase7["workout"],
        scheduled_at=timezone.now() - timedelta(minutes=4),
    )
    Notification.objects.create(
        user=phase7["user"],
        scheduled_session=second,
        visible_at=timezone.now() - timedelta(hours=1),
    )
    bodies = [payload(phase7), payload(phase7)]
    bodies[1]["scheduled_session_id"] = second.pk
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                concurrent_post,
                user_id=phase7["user"].pk,
                url=URL,
                body=body,
                barrier=barrier,
                key=str(uuid4()),
            )
            for body in bodies
        ]
    assert [item.result() for item in futures].count(201) == 2
    phase7["program"].refresh_from_db()
    assert phase7["program"].status == "completed"
    assert phase7["program"].total_planned_at_completion == 2
    assert phase7["program"].completed_planned_at_completion == 2
    assert (
        PointTransaction.objects.filter(
            user_program=phase7["program"], point_kind=PointKind.PROGRAM_COMPLETION
        ).count()
        <= 1
    )


@pytest.mark.django_db(transaction=True)
def test_t39_g09_and_s02_are_serialized_by_program_lock(phase7):
    phase7["slot"].delete()
    program = phase7["program"]
    program.status = "draft"
    program.activated_at = None
    program.bonus_target_sessions = None
    program.save(update_fields=["status", "activated_at", "bonus_target_sessions"])
    barrier = Barrier(2)
    schedule_body = {
        "user_program_workout_id": phase7["entry"].pk,
        "source_workout_id": None,
        "scheduled_at": (timezone.now() + timedelta(hours=2)).isoformat(),
    }
    with ThreadPoolExecutor(max_workers=2) as pool:
        schedule = pool.submit(
            concurrent_post,
            user_id=phase7["user"].pk,
            url="/api/v1/scheduled-sessions/",
            body=schedule_body,
            barrier=barrier,
        )
        archive = pool.submit(
            concurrent_post,
            user_id=phase7["user"].pk,
            url=f"/api/v1/user-programs/{program.pk}/archive/",
            body={},
            barrier=barrier,
        )
    statuses = {schedule.result(), archive.result()}
    assert statuses in ({200, 409}, {201, 409})
    program.refresh_from_db()
    assert not (
        program.is_archived
        and program.scheduled_sessions.filter(status="planned").exists()
    )
