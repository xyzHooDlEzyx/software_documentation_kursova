from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.utils import timezone

from accounts.models import Profile
from catalog.models import Exercise, WorkoutExercise
from engagement.models import PointKind, PointTransaction, UserAchievement
from execution.models import CompletedSession, ExerciseResult
from planning.models import (
    Notification,
    ScheduledSession,
    UserProgram,
    UserProgramExercise,
    UserProgramWorkout,
)

from .test_phase7_api import URL, client, payload


def add_slot(data, *, status="planned", scheduled_at=None):
    slot = ScheduledSession.objects.create(
        user=data["user"],
        user_program=data["program"],
        user_program_workout=data["entry"],
        source_workout=data["workout"],
        scheduled_at=scheduled_at or timezone.now() - timedelta(minutes=5),
        status=status,
    )
    Notification.objects.create(
        user=data["user"],
        scheduled_session=slot,
        visible_at=timezone.now() - timedelta(hours=1),
    )
    return slot


def completion_body(data, slot=None, *, exercise=None):
    body = deepcopy(payload(data))
    body["scheduled_session_id"] = (slot or data["slot"]).pk
    if exercise is not None:
        body["results"][0]["exercise_id"] = exercise.pk
    return body


def complete(data, slot=None, *, body=None, key=None):
    return client(data["user"]).post(
        URL,
        body or completion_body(data, slot),
        format="json",
        HTTP_IDEMPOTENCY_KEY=key or str(uuid4()),
    )


def assert_no_execution_rows(data):
    assert not CompletedSession.objects.filter(user=data["user"]).exists()
    assert not ExerciseResult.objects.filter(
        completed_session__user=data["user"]
    ).exists()
    assert not PointTransaction.objects.filter(user=data["user"]).exists()


def bonus_count(data):
    return PointTransaction.objects.filter(
        user=data["user"],
        user_program=data["program"],
        point_kind=PointKind.PROGRAM_COMPLETION,
    ).count()


def assert_completed_snapshot(data, *, total, completed):
    data["program"].refresh_from_db()
    assert data["program"].status == "completed"
    assert data["program"].total_planned_at_completion == total
    assert data["program"].completed_planned_at_completion == completed
    assert data["program"].progress_percent_at_completion == Decimal("100.0")
    assert data["program"].completed_at is not None


def new_program(data, *, status="draft", archived=False, target=None):
    values = {
        "user": data["user"],
        "source_program_template": data["template"],
        "name": f"Matrix {status} {uuid4()}",
        "fitness_goal": "maintenance",
        "source_program_template_name_snapshot": data["template"].name,
        "status": status,
        "is_archived": archived,
    }
    if status in {"active", "completed"}:
        values.update(activated_at=timezone.now(), bonus_target_sessions=target or 3)
    if status == "completed":
        values.update(
            completed_at=timezone.now(),
            total_planned_at_completion=1,
            completed_planned_at_completion=1,
            progress_percent_at_completion=Decimal("100.0"),
        )
    return UserProgram.objects.create(**values)


@pytest.mark.django_db
def test_t14_empty_results_rejected_without_fact_or_points(phase7):
    body = completion_body(phase7)
    body["results"] = []
    response = complete(phase7, body=body)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
    assert_no_execution_rows(phase7)
    phase7["slot"].refresh_from_db()
    assert phase7["slot"].status == "planned"


@pytest.mark.django_db
def test_t15_one_of_multiple_planned_results_creates_only_performed_result(phase7):
    second = Exercise.objects.create(name="Deadlift", category="strength")
    UserProgramExercise.objects.create(
        user_program_workout=phase7["entry"],
        exercise=second,
        position=2,
        recommended_sets=3,
        recommended_reps=5,
    )
    response = complete(phase7)
    assert response.status_code == 201
    fact = CompletedSession.objects.get(pk=response.json()["id"])
    assert list(fact.exercise_results.values_list("source_exercise_id", flat=True)) == [
        phase7["exercise"].pk
    ]
    assert (
        fact.point_transactions.filter(point_kind=PointKind.WORKOUT_COMPLETION).count()
        == 1
    )


@pytest.mark.django_db
def test_t16_identical_key_and_body_returns_same_fact_and_one_ledger_row(phase7):
    key = str(uuid4())
    first = complete(phase7, key=key)
    retry = complete(phase7, key=key)
    assert (first.status_code, retry.status_code) == (201, 200)
    assert first.json()["id"] == retry.json()["id"]
    assert CompletedSession.objects.filter(user=phase7["user"]).count() == 1
    assert (
        PointTransaction.objects.filter(
            user=phase7["user"], point_kind=PointKind.WORKOUT_COMPLETION
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_t17_same_key_with_different_body_returns_idempotency_conflict(phase7):
    key = str(uuid4())
    assert complete(phase7, key=key).status_code == 201
    changed = completion_body(phase7)
    changed["duration_min"] = "44.00"
    response = complete(phase7, body=changed, key=key)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "idempotency_conflict"
    assert CompletedSession.objects.count() == 1
    assert (
        PointTransaction.objects.filter(point_kind=PointKind.WORKOUT_COMPLETION).count()
        == 1
    )


@pytest.mark.django_db
def test_t18_same_slot_with_different_key_returns_duplicate_completion(phase7):
    assert complete(phase7).status_code == 201
    response = complete(phase7, key=str(uuid4()))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_completion"
    assert (
        CompletedSession.objects.filter(scheduled_session=phase7["slot"]).count() == 1
    )
    assert (
        PointTransaction.objects.filter(point_kind=PointKind.WORKOUT_COMPLETION).count()
        == 1
    )


@pytest.mark.django_db
def test_t20_profile_and_met_absence_have_distinct_atomic_outcomes(phase7):
    Profile.objects.filter(user=phase7["user"]).delete()
    missing_profile = complete(phase7)
    assert missing_profile.status_code == 404
    assert missing_profile.json()["error"]["code"] == "profile_missing"
    assert_no_execution_rows(phase7)

    Profile.objects.create(
        user=phase7["user"],
        date_of_birth=date(1990, 1, 1),
        weight_kg=Decimal("70.0"),
        height_cm=Decimal("170.0"),
        gender="other",
        fitness_goal="maintenance",
        experience_level="beginner",
        workouts_per_week=3,
    )
    Exercise.objects.filter(pk=phase7["exercise"].pk).update(
        met_value=None,
        met_activity_code=None,
        met_reference_version=None,
        met_activity_description=None,
    )
    response = complete(phase7)
    assert response.status_code == 201
    fact = CompletedSession.objects.get(pk=response.json()["id"])
    assert fact.estimated_calories is None
    assert fact.missing_calorie_reason == "missing_met"
    assert fact.exercise_results.count() == 1
    assert (
        fact.point_transactions.filter(point_kind=PointKind.WORKOUT_COMPLETION).count()
        == 1
    )


@pytest.mark.django_db
def test_t21_age_sixty_saves_null_calories_and_stable_reason(phase7):
    Profile.objects.filter(user=phase7["user"]).update(date_of_birth=date(1960, 1, 1))
    response = complete(phase7)
    assert response.status_code == 201
    fact = CompletedSession.objects.get(pk=response.json()["id"])
    assert fact.estimated_calories is None
    assert fact.missing_calorie_reason == "unsupported_age_for_reference"
    Profile.objects.filter(user=phase7["user"]).update(date_of_birth=date(1990, 1, 1))
    fact.refresh_from_db()
    assert fact.estimated_calories is None
    assert fact.missing_calorie_reason == "unsupported_age_for_reference"
    assert (
        fact.point_transactions.filter(point_kind=PointKind.WORKOUT_COMPLETION).count()
        == 1
    )


@pytest.mark.django_db
def test_t22_one_of_one_completes_without_bonus_and_uses_fact_timestamp(phase7):
    response = complete(phase7)
    assert response.status_code == 201
    fact = CompletedSession.objects.get(pk=response.json()["id"])
    assert_completed_snapshot(phase7, total=1, completed=1)
    assert phase7["program"].completed_at == fact.completed_at
    progress = client(phase7["user"]).get(
        f"/api/v1/user-programs/{phase7['program'].pk}/progress/"
    )
    assert progress.status_code == 200
    assert progress.json()["percent"] == "100.0"
    assert progress.json()["bonus_earned"] is False
    assert bonus_count(phase7) == 0


@pytest.mark.django_db
def test_t23_three_of_three_awards_exactly_one_program_bonus(phase7):
    slots = [phase7["slot"], add_slot(phase7), add_slot(phase7)]
    assert [complete(phase7, slot).status_code for slot in slots] == [201, 201, 201]
    assert_completed_snapshot(phase7, total=3, completed=3)
    assert bonus_count(phase7) == 1
    bonus = PointTransaction.objects.get(
        user_program=phase7["program"], point_kind=PointKind.PROGRAM_COMPLETION
    )
    assert bonus.points == 50
    progress = client(phase7["user"]).get(
        f"/api/v1/user-programs/{phase7['program'].pk}/progress/"
    )
    assert progress.json()["bonus_earned"] is True
    assert (
        PointTransaction.objects.filter(
            user=phase7["user"], point_kind=PointKind.WORKOUT_COMPLETION
        ).count()
        == 3
    )


@pytest.mark.django_db
def test_t30_cancel_after_two_of_three_completes_two_of_two_without_bonus(phase7):
    slots = [phase7["slot"], add_slot(phase7), add_slot(phase7)]
    assert complete(phase7, slots[0]).status_code == 201
    assert complete(phase7, slots[1]).status_code == 201
    cancelled_at = timezone.now()
    with patch("planning.services.timezone.now", return_value=cancelled_at):
        response = client(phase7["user"]).post(
            f"/api/v1/scheduled-sessions/{slots[2].pk}/cancel/", {}, format="json"
        )
    assert response.status_code == 200
    assert response.json()["reminder"]["is_current"] is False
    assert_completed_snapshot(phase7, total=2, completed=2)
    assert phase7["program"].completed_at == cancelled_at
    assert bonus_count(phase7) == 0
    assert CompletedSession.objects.count() == 2
    assert ExerciseResult.objects.count() == 2


@pytest.mark.django_db
def test_t31_cancel_after_three_of_four_keeps_frozen_four_and_no_bonus(phase7):
    phase7["program"].bonus_target_sessions = 4
    phase7["program"].save(update_fields=["bonus_target_sessions"])
    slots = [phase7["slot"], add_slot(phase7), add_slot(phase7), add_slot(phase7)]
    assert [complete(phase7, slot).status_code for slot in slots[:3]] == [201] * 3
    response = client(phase7["user"]).post(
        f"/api/v1/scheduled-sessions/{slots[3].pk}/cancel/", {}, format="json"
    )
    assert response.status_code == 200
    assert_completed_snapshot(phase7, total=3, completed=3)
    assert phase7["program"].bonus_target_sessions == 4
    assert bonus_count(phase7) == 0
    assert (
        PointTransaction.objects.filter(point_kind=PointKind.WORKOUT_COMPLETION).count()
        == 3
    )


@pytest.mark.django_db
def test_t32_added_fourth_cancelled_after_three_awards_one_bonus_without_fact(phase7):
    slots = [phase7["slot"], add_slot(phase7), add_slot(phase7), add_slot(phase7)]
    assert [complete(phase7, slot).status_code for slot in slots[:3]] == [201] * 3
    facts_before = CompletedSession.objects.count()
    achievements_before = UserAchievement.objects.count()
    response = client(phase7["user"]).post(
        f"/api/v1/scheduled-sessions/{slots[3].pk}/cancel/", {}, format="json"
    )
    assert response.status_code == 200
    assert_completed_snapshot(phase7, total=3, completed=3)
    assert bonus_count(phase7) == 1
    assert CompletedSession.objects.count() == facts_before == 3
    assert UserAchievement.objects.count() == achievements_before


@pytest.mark.django_db
def test_t33_personal_composition_accepts_replacement_and_persists_source_snapshots(
    phase7,
):
    removed = Exercise.objects.create(name="Removed", category="strength")
    replacement = Exercise.objects.create(name="Replacement", category="strength")
    WorkoutExercise.objects.create(
        workout=phase7["workout"],
        exercise=removed,
        position=2,
        recommended_sets=2,
        recommended_reps=5,
    )
    phase7["entry"].exercises.all().delete()
    UserProgramExercise.objects.create(
        user_program_workout=phase7["entry"],
        exercise=replacement,
        position=1,
        recommended_sets=3,
        recommended_reps=8,
    )
    rejected = complete(phase7, body=completion_body(phase7, exercise=removed))
    assert rejected.status_code == 400
    assert_no_execution_rows(phase7)
    accepted = complete(phase7, body=completion_body(phase7, exercise=replacement))
    assert accepted.status_code == 201
    fact = CompletedSession.objects.get(pk=accepted.json()["id"])
    result = fact.exercise_results.get()
    assert fact.source_workout_id == phase7["workout"].pk
    assert fact.source_workout_id_snapshot == phase7["workout"].pk
    assert result.source_exercise_id == replacement.pk
    assert result.exercise_name_snapshot == "Replacement"
    assert (
        PointTransaction.objects.filter(
            completed_session=fact, point_kind=PointKind.WORKOUT_COMPLETION
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_t34_program_states_reject_new_completion_while_standalone_succeeds(phase7):
    program = phase7["program"]
    UserProgram.objects.filter(pk=program.pk).update(
        status="draft", activated_at=None, bonus_target_sessions=None
    )
    assert complete(phase7).status_code == 409
    UserProgram.objects.filter(pk=program.pk).update(
        status="completed",
        activated_at=timezone.now(),
        bonus_target_sessions=3,
        completed_at=timezone.now(),
        total_planned_at_completion=1,
        completed_planned_at_completion=1,
        progress_percent_at_completion=Decimal("100.0"),
    )
    assert complete(phase7).status_code == 409
    UserProgram.objects.filter(pk=program.pk).update(
        status="active",
        is_archived=True,
        completed_at=None,
        total_planned_at_completion=None,
        completed_planned_at_completion=None,
        progress_percent_at_completion=None,
    )
    assert complete(phase7).status_code == 409
    assert_no_execution_rows(phase7)
    standalone = completion_body(phase7)
    standalone["scheduled_session_id"] = None
    standalone["source_workout_id"] = phase7["workout"].pk
    response = complete(phase7, body=standalone)
    assert response.status_code == 201
    assert response.json()["program"] is None
    assert CompletedSession.objects.count() == 1
    assert (
        PointTransaction.objects.filter(point_kind=PointKind.WORKOUT_COMPLETION).count()
        == 1
    )


@pytest.mark.django_db
def test_t35_committed_retry_precedes_completed_state_validation(phase7):
    key = str(uuid4())
    first = complete(phase7, key=key)
    assert first.status_code == 201
    phase7["program"].is_archived = True
    phase7["program"].save(update_fields=["is_archived"])
    retry = complete(phase7, key=key)
    assert retry.status_code == 200
    assert retry.json()["id"] == first.json()["id"]
    changed = completion_body(phase7)
    changed["duration_min"] = "40.00"
    conflict = complete(phase7, body=changed, key=key)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"
    assert CompletedSession.objects.count() == 1
    assert (
        PointTransaction.objects.filter(point_kind=PointKind.WORKOUT_COMPLETION).count()
        == 1
    )


@pytest.mark.django_db
def test_t36_overdue_planned_blocks_archive_then_cancel_allows_it(phase7):
    UserProgram.objects.filter(pk=phase7["program"].pk).update(
        status="draft", activated_at=None, bonus_target_sessions=None
    )
    phase7["slot"].scheduled_at = timezone.now() - timedelta(days=1)
    phase7["slot"].save(update_fields=["scheduled_at"])
    assert phase7["slot"].is_missed is True
    archive_url = f"/api/v1/user-programs/{phase7['program'].pk}/archive/"
    blocked = client(phase7["user"]).post(archive_url, {}, format="json")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "planned_sessions_exist"
    phase7["slot"].refresh_from_db()
    assert phase7["slot"].status == "planned"
    assert (
        client(phase7["user"])
        .post(
            f"/api/v1/scheduled-sessions/{phase7['slot'].pk}/cancel/", {}, format="json"
        )
        .status_code
        == 200
    )
    archived = client(phase7["user"]).post(archive_url, {}, format="json")
    assert archived.status_code == 200
    assert archived.json()["is_archived"] is True
    assert not CompletedSession.objects.exists()
    assert not PointTransaction.objects.exists()


@pytest.mark.django_db
def test_t37_archive_allowed_states_and_active_rejection_leave_reminders_untouched(
    phase7,
):
    api = client(phase7["user"])
    empty = new_program(phase7)
    assert (
        api.post(
            f"/api/v1/user-programs/{empty.pk}/archive/", {}, format="json"
        ).status_code
        == 200
    )

    cancelled_program = new_program(phase7)
    cancelled_entry = UserProgramWorkout.objects.create(
        user_program=cancelled_program,
        source_workout=phase7["workout"],
        position=1,
        name="Cancelled",
        category="strength",
    )
    cancelled_slot = ScheduledSession.objects.create(
        user=phase7["user"],
        user_program=cancelled_program,
        user_program_workout=cancelled_entry,
        source_workout=phase7["workout"],
        scheduled_at=timezone.now() + timedelta(hours=2),
        status="cancelled",
    )
    reminder = Notification.objects.create(
        user=phase7["user"],
        scheduled_session=cancelled_slot,
        visible_at=timezone.now() + timedelta(hours=1),
    )
    assert (
        api.post(
            f"/api/v1/user-programs/{cancelled_program.pk}/archive/", {}, format="json"
        ).status_code
        == 200
    )
    reminder.refresh_from_db()
    assert reminder.status == "pending"

    completed = new_program(phase7, status="completed")
    assert (
        api.post(
            f"/api/v1/user-programs/{completed.pk}/archive/", {}, format="json"
        ).status_code
        == 200
    )
    active = new_program(phase7, status="active")
    active_response = api.post(
        f"/api/v1/user-programs/{active.pk}/archive/", {}, format="json"
    )
    assert active_response.status_code == 409
    assert active_response.json()["error"]["code"] == "invalid_state"
    assert (
        api.post(
            f"/api/v1/user-programs/{empty.pk}/archive/", {}, format="json"
        ).status_code
        == 200
    )


@pytest.mark.django_db
def test_t38_cancelling_only_slot_keeps_zero_denominator_program_active(phase7):
    response = client(phase7["user"]).post(
        f"/api/v1/scheduled-sessions/{phase7['slot'].pk}/cancel/", {}, format="json"
    )
    assert response.status_code == 200
    phase7["program"].refresh_from_db()
    assert phase7["program"].status == "active"
    assert phase7["program"].completed_at is None
    assert phase7["program"].total_planned_at_completion is None
    assert bonus_count(phase7) == 0
    progress = client(phase7["user"]).get(
        f"/api/v1/user-programs/{phase7['program'].pk}/progress/"
    )
    assert progress.status_code == 200
    assert progress.json()["total_planned"] == 0
    assert progress.json()["completed_planned"] == 0
    assert progress.json()["percent"] == "0.0"
    assert not CompletedSession.objects.exists()


@pytest.mark.django_db
def test_t40_latest_personal_composition_is_used_and_fact_snapshot_stays_immutable(
    phase7,
):
    replacement = Exercise.objects.create(name="Latest", category="strength")
    replace_url = (
        f"/api/v1/user-programs/{phase7['program'].pk}/workouts/{phase7['entry'].pk}/"
    )
    replace_body = {
        "name": "Latest personal workout",
        "exercises": [
            {
                "position": 1,
                "exercise_id": replacement.pk,
                "recommended_sets": 3,
                "recommended_reps": 8,
                "recommended_load_kg": "20.0",
                "recommended_duration_min": None,
                "recommended_distance_km": None,
            }
        ],
    }
    assert (
        client(phase7["user"]).put(replace_url, replace_body, format="json").status_code
        == 200
    )
    response = complete(phase7, body=completion_body(phase7, exercise=replacement))
    assert response.status_code == 201
    fact = CompletedSession.objects.get(pk=response.json()["id"])
    result = fact.exercise_results.get()
    assert result.source_exercise_id == replacement.pk
    assert result.exercise_name_snapshot == "Latest"
    assert fact.performed_workout_name_snapshot == "Latest personal workout"
    assert fact.source_workout_id == phase7["workout"].pk
    Exercise.objects.filter(pk=replacement.pk).update(name="Changed later")
    phase7["entry"].exercises.all().delete()
    result.refresh_from_db()
    fact.refresh_from_db()
    assert result.exercise_name_snapshot == "Latest"
    assert result.source_exercise_id_snapshot == replacement.pk
    assert fact.performed_workout_name_snapshot == "Latest personal workout"
    assert (
        PointTransaction.objects.filter(
            completed_session=fact, point_kind=PointKind.WORKOUT_COMPLETION
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_t41_repeated_cancel_after_completion_is_a_strict_noop(phase7):
    slots = [phase7["slot"], add_slot(phase7), add_slot(phase7)]
    assert complete(phase7, slots[0]).status_code == 201
    assert complete(phase7, slots[1]).status_code == 201
    api = client(phase7["user"])
    url = f"/api/v1/scheduled-sessions/{slots[2].pk}/cancel/"
    first = api.post(url, {}, format="json")
    assert first.status_code == 200
    assert_completed_snapshot(phase7, total=2, completed=2)
    slots[2].refresh_from_db()
    reminder = Notification.objects.get(scheduled_session=slots[2])
    snapshot = (
        phase7["program"].completed_at,
        phase7["program"].total_planned_at_completion,
        phase7["program"].completed_planned_at_completion,
        phase7["program"].progress_percent_at_completion,
    )
    counts = (
        CompletedSession.objects.count(),
        ExerciseResult.objects.count(),
        PointTransaction.objects.count(),
        UserAchievement.objects.count(),
    )
    reminder_state = (reminder.status, reminder.read_at, reminder.visible_at)
    second = api.post(url, {}, format="json")
    assert second.status_code == 200
    assert second.json() == first.json()
    phase7["program"].refresh_from_db()
    slots[2].refresh_from_db()
    reminder.refresh_from_db()
    assert slots[2].status == "cancelled"
    assert snapshot == (
        phase7["program"].completed_at,
        phase7["program"].total_planned_at_completion,
        phase7["program"].completed_planned_at_completion,
        phase7["program"].progress_percent_at_completion,
    )
    assert counts == (
        CompletedSession.objects.count(),
        ExerciseResult.objects.count(),
        PointTransaction.objects.count(),
        UserAchievement.objects.count(),
    )
    assert reminder_state == (reminder.status, reminder.read_at, reminder.visible_at)
    progress = api.get(f"/api/v1/user-programs/{phase7['program'].pk}/progress/")
    assert progress.json()["status"] == "completed"
    assert progress.json()["total_planned"] == 2
    assert progress.json()["completed_planned"] == 2
    assert progress.json()["bonus_earned"] is False
