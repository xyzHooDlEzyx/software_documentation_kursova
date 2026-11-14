"""Phase 5 scheduling, activation, reminder, isolation, and atomicity tests."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connections, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Profile
from catalog.models import (
    ExerciseCategory,
    ProgramTemplate,
    ProgramTemplateStatus,
    Workout,
)
from planning.models import (
    Notification,
    NotificationStatus,
    ScheduledSession,
    UserProgram,
    UserProgramWorkout,
)
from planning.serializers import ScheduledSessionDetailSerializer
from planning.services import ProgramPlanningService, ReminderService

User = get_user_model()
SESSIONS_URL = "/api/v1/scheduled-sessions/"
NOTIFICATIONS_URL = "/api/v1/notifications/"


def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def phase5_data(db):
    owner = User.objects.create_user("phase5-owner@example.test", "SecurePass2026!")
    other = User.objects.create_user("phase5-other@example.test", "SecurePass2026!")
    Profile.objects.create(
        user=owner,
        date_of_birth=date(1995, 4, 12),
        weight_kg=Decimal("72.0"),
        height_cm=Decimal("174.0"),
        gender="female",
        fitness_goal="maintenance",
        experience_level="beginner",
        workouts_per_week=3,
    )
    workout = Workout.objects.create(
        name="Phase 5 workout", category=ExerciseCategory.CARDIO
    )
    template = ProgramTemplate.objects.create(
        name="Phase 5 template",
        fitness_goal="maintenance",
        experience_level="beginner",
        workouts_per_week=3,
        status=ProgramTemplateStatus.PUBLISHED,
    )

    def program_for(user, suffix):
        program = UserProgram.objects.create(
            user=user,
            source_program_template=template,
            name=f"Program {suffix}",
            fitness_goal="maintenance",
            source_program_template_name_snapshot=template.name,
        )
        entry = UserProgramWorkout.objects.create(
            user_program=program,
            source_workout=workout,
            position=1,
            name=workout.name,
            category=workout.category,
        )
        return program, entry

    program, entry = program_for(owner, "owner")
    foreign_program, foreign_entry = program_for(other, "other")
    return {
        "owner": owner,
        "other": other,
        "workout": workout,
        "program": program,
        "entry": entry,
        "foreign_program": foreign_program,
        "foreign_entry": foreign_entry,
    }


def create_program_slot(client, entry_id, *, hours=3):
    scheduled_at = timezone.now() + timedelta(hours=hours)
    return client.post(
        SESSIONS_URL,
        {
            "user_program_workout_id": entry_id,
            "source_workout_id": None,
            "scheduled_at": scheduled_at.isoformat(),
        },
        format="json",
    )


@pytest.mark.django_db
def test_draft_slots_activation_and_frozen_threshold(phase5_data):
    data = phase5_data
    client = api_client(data["owner"])
    activate_url = f"/api/v1/user-programs/{data['program'].pk}/activate/"
    empty = client.post(activate_url, {}, format="json")
    assert empty.status_code == 400
    assert data["program"].bonus_target_sessions is None
    ScheduledSession.objects.create(
        user=data["owner"],
        user_program=data["program"],
        user_program_workout=data["entry"],
        source_workout=data["workout"],
        scheduled_at=timezone.now() + timedelta(hours=1),
        status="cancelled",
    )
    cancelled_only = client.post(activate_url, {}, format="json")
    assert cancelled_only.status_code == 400
    assert cancelled_only.json()["error"]["code"] == "validation_error"

    data["program"].is_archived = True
    data["program"].save(update_fields=["is_archived"])
    archived = client.post(activate_url, {}, format="json")
    assert archived.status_code == 409
    assert archived.json()["error"]["code"] == "invalid_state"
    data["program"].is_archived = False
    data["program"].save(update_fields=["is_archived"])

    responses = [
        create_program_slot(client, data["entry"].pk, hours=offset)
        for offset in (2, 3, 4, 5)
    ]
    assert all(response.status_code == 201 for response in responses)
    assert all(response.json()["status"] == "planned" for response in responses)
    assert Notification.objects.count() == 4

    activated = client.post(activate_url, {}, format="json")
    assert activated.status_code == 200
    assert activated.json()["bonus_target_sessions"] == 4
    assert activated.json()["progress"] == {
        "total_planned": 4,
        "completed_planned": 0,
        "percent": "0.0",
    }
    assert create_program_slot(client, data["entry"].pk, hours=6).status_code == 201
    data["program"].refresh_from_db()
    assert data["program"].bonus_target_sessions == 4


@pytest.mark.django_db
def test_s02_one_reminder_s04_preserves_ids_and_updates_visible_at(phase5_data):
    data = phase5_data
    client = api_client(data["owner"])
    created = create_program_slot(client, data["entry"].pk)
    assert created.status_code == 201
    body = created.json()
    slot_id = body["id"]
    reminder_id = body["reminder"]["id"]
    assert Notification.objects.filter(scheduled_session_id=slot_id).count() == 1

    same_as_shown = client.patch(
        f"{SESSIONS_URL}{slot_id}/",
        {"scheduled_at": body["scheduled_at"]},
        format="json",
    )
    assert same_as_shown.status_code == 200
    assert same_as_shown.json()["reschedule_history"] == []

    old_time = ScheduledSession.objects.get(pk=slot_id).scheduled_at
    new_time = old_time + timedelta(days=1)
    Notification.objects.filter(pk=reminder_id).update(
        status=NotificationStatus.READ, read_at=timezone.now()
    )
    moved = client.patch(
        f"{SESSIONS_URL}{slot_id}/",
        {"scheduled_at": new_time.isoformat()},
        format="json",
    )
    assert moved.status_code == 200
    assert moved.json()["id"] == slot_id
    assert moved.json()["reminder"]["id"] == reminder_id
    assert moved.json()["reschedule_history"] == [body["scheduled_at"]]
    assert "." not in moved.json()["reschedule_history"][0]
    reminder = Notification.objects.get(pk=reminder_id)
    assert reminder.visible_at == new_time - timedelta(hours=1)
    assert reminder.status == NotificationStatus.PENDING
    assert reminder.read_at is None

    same = client.patch(
        f"{SESSIONS_URL}{slot_id}/",
        {"scheduled_at": new_time.isoformat()},
        format="json",
    )
    assert same.status_code == 200
    assert same.json()["reschedule_history"] == moved.json()["reschedule_history"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "invalid_value",
    [
        "2026-02-30T10:00:00Z",
        12345,
        True,
        ["x"],
        {"a": 1},
        "2026-12-01T10:00:00",
    ],
)
def test_s02_s04_invalid_scheduled_at_returns_400(phase5_data, invalid_value):
    data = phase5_data
    client = api_client(data["owner"])
    slot = create_program_slot(client, data["entry"].pk)
    assert slot.status_code == 201

    create_response = client.post(
        SESSIONS_URL,
        {
            "user_program_workout_id": data["entry"].pk,
            "source_workout_id": None,
            "scheduled_at": invalid_value,
        },
        format="json",
    )
    patch_response = client.patch(
        f"{SESSIONS_URL}{slot.json()['id']}/",
        {"scheduled_at": invalid_value},
        format="json",
    )
    for response in (create_response, patch_response):
        assert response.status_code == 400
        error = response.json()["error"]
        assert error["code"] == "validation_error"
        assert "scheduled_at" in error["fields"]


@pytest.mark.django_db
def test_s02_past_rejected_and_short_lead_reminder_visible(phase5_data):
    data = phase5_data
    client = api_client(data["owner"])
    past = client.post(
        SESSIONS_URL,
        {
            "user_program_workout_id": data["entry"].pk,
            "source_workout_id": None,
            "scheduled_at": (timezone.now() - timedelta(seconds=1)).isoformat(),
        },
        format="json",
    )
    assert past.status_code == 400
    assert past.json()["error"]["code"] == "validation_error"

    short_lead = create_program_slot(client, data["entry"].pk, hours=0.5)
    assert short_lead.status_code == 201
    listed_ids = {
        item["id"] for item in client.get(NOTIFICATIONS_URL).json()["results"]
    }
    assert short_lead.json()["reminder"]["id"] in listed_ids


@pytest.mark.django_db
def test_s02_rejects_closed_program_and_archived_source_workout(phase5_data):
    data = phase5_data
    client = api_client(data["owner"])
    program = data["program"]

    program.is_archived = True
    program.save(update_fields=["is_archived"])
    archived = create_program_slot(client, data["entry"].pk)
    assert archived.status_code == 409
    assert archived.json()["error"]["code"] == "invalid_state"

    now = timezone.now()
    UserProgram.objects.filter(pk=program.pk).update(
        is_archived=False,
        status="completed",
        activated_at=now,
        bonus_target_sessions=3,
        completed_at=now,
        total_planned_at_completion=1,
        completed_planned_at_completion=1,
        progress_percent_at_completion=Decimal("100.0"),
    )
    completed = create_program_slot(client, data["entry"].pk)
    assert completed.status_code == 409
    assert completed.json()["error"]["code"] == "invalid_state"

    data["workout"].is_archived = True
    data["workout"].save(update_fields=["is_archived"])
    standalone = client.post(
        SESSIONS_URL,
        {
            "user_program_workout_id": None,
            "source_workout_id": data["workout"].pk,
            "scheduled_at": (timezone.now() + timedelta(hours=2)).isoformat(),
        },
        format="json",
    )
    assert standalone.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("slot_status", ["cancelled", "completed"])
def test_s04_rejects_cancelled_and_completed_slots(phase5_data, slot_status):
    data = phase5_data
    client = api_client(data["owner"])
    created = create_program_slot(client, data["entry"].pk)
    slot_id = created.json()["id"]
    ScheduledSession.objects.filter(pk=slot_id).update(status=slot_status)

    response = client.patch(
        f"{SESSIONS_URL}{slot_id}/",
        {"scheduled_at": (timezone.now() + timedelta(days=1)).isoformat()},
        format="json",
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_state"


@pytest.mark.django_db
def test_s04_reschedules_overdue_planned_slot(phase5_data):
    data = phase5_data
    client = api_client(data["owner"])
    overdue = ScheduledSession.objects.create(
        user=data["owner"],
        source_workout=data["workout"],
        scheduled_at=timezone.now() - timedelta(minutes=5),
    )
    Notification.objects.create(
        user=data["owner"],
        scheduled_session=overdue,
        visible_at=overdue.scheduled_at - timedelta(hours=1),
    )
    response = client.patch(
        f"{SESSIONS_URL}{overdue.pk}/",
        {"scheduled_at": (timezone.now() + timedelta(hours=2)).isoformat()},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["is_missed"] is False


@pytest.mark.django_db
def test_s04_after_n03_resets_read_reminder(phase5_data):
    data = phase5_data
    client = api_client(data["owner"])
    created = create_program_slot(client, data["entry"].pk, hours=0.5).json()
    reminder_id = created["reminder"]["id"]
    read = client.post(f"{NOTIFICATIONS_URL}{reminder_id}/read/", {}, format="json")
    assert read.status_code == 200
    assert read.json()["status"] == "read"
    assert read.json()["read_at"] is not None

    moved = client.patch(
        f"{SESSIONS_URL}{created['id']}/",
        {"scheduled_at": (timezone.now() + timedelta(hours=3)).isoformat()},
        format="json",
    )
    assert moved.status_code == 200
    reminder = Notification.objects.get(pk=reminder_id)
    assert reminder.status == NotificationStatus.PENDING
    assert reminder.read_at is None


@pytest.mark.django_db
def test_s01_s02_s03_support_standalone_and_derived_missed(
    phase5_data, django_assert_num_queries
):
    data = phase5_data
    client = api_client(data["owner"])
    created = client.post(
        SESSIONS_URL,
        {
            "user_program_workout_id": None,
            "source_workout_id": data["workout"].pk,
            "scheduled_at": (timezone.now() + timedelta(hours=2)).isoformat(),
        },
        format="json",
    )
    assert created.status_code == 201
    assert created.json()["user_program_id"] is None
    assert created.json()["user_program_workout_id"] is None
    detail = client.get(f"{SESSIONS_URL}{created.json()['id']}/")
    assert detail.status_code == 200
    assert detail.json()["completed_session_id"] is None
    loaded = ProgramPlanningService.get_scheduled_session(
        data["owner"], created.json()["id"]
    )
    with django_assert_num_queries(0):
        assert ScheduledSessionDetailSerializer(loaded).data["reminder"]["id"]

    overdue = ScheduledSession.objects.create(
        user=data["owner"],
        source_workout=data["workout"],
        scheduled_at=timezone.now() - timedelta(minutes=5),
    )
    Notification.objects.create(
        user=data["owner"],
        scheduled_session=overdue,
        visible_at=overdue.scheduled_at - timedelta(hours=1),
    )
    listed = client.get(SESSIONS_URL)
    assert listed.status_code == 200
    by_id = {item["id"]: item for item in listed.json()["results"]}
    assert by_id[overdue.pk]["status"] == "planned"
    assert by_id[overdue.pk]["is_missed"] is True
    assert client.get(f"{SESSIONS_URL}?status=missed").status_code == 400


@pytest.mark.django_db
def test_s01_uses_kyiv_local_period_and_dst_boundary(phase5_data):
    data = phase5_data
    client = api_client(data["owner"])

    after_midnight_kyiv = ScheduledSession.objects.create(
        user=data["owner"],
        source_workout=data["workout"],
        scheduled_at=datetime(2026, 10, 28, 22, 30, tzinfo=dt_timezone.utc),
    )
    october_29 = client.get(f"{SESSIONS_URL}?start_date=2026-10-29&end_date=2026-10-30")
    october_28 = client.get(f"{SESSIONS_URL}?start_date=2026-10-28&end_date=2026-10-29")
    assert after_midnight_kyiv.pk in {
        item["id"] for item in october_29.json()["results"]
    }
    assert after_midnight_kyiv.pk not in {
        item["id"] for item in october_28.json()["results"]
    }

    early_dst_day = ScheduledSession.objects.create(
        user=data["owner"],
        source_workout=data["workout"],
        scheduled_at=datetime(2026, 10, 24, 21, 30, tzinfo=dt_timezone.utc),
    )
    late_dst_day = ScheduledSession.objects.create(
        user=data["owner"],
        source_workout=data["workout"],
        scheduled_at=datetime(2026, 10, 25, 21, 30, tzinfo=dt_timezone.utc),
    )
    next_local_day = ScheduledSession.objects.create(
        user=data["owner"],
        source_workout=data["workout"],
        scheduled_at=datetime(2026, 10, 25, 22, 30, tzinfo=dt_timezone.utc),
    )
    dst_day = client.get(f"{SESSIONS_URL}?start_date=2026-10-25&end_date=2026-10-26")
    dst_ids = {item["id"] for item in dst_day.json()["results"]}
    assert {early_dst_day.pk, late_dst_day.pk} <= dst_ids
    assert next_local_day.pk not in dst_ids


@pytest.mark.django_db
def test_notifications_hide_future_and_cancelled_and_read_is_idempotent(
    phase5_data,
):
    data = phase5_data
    client = api_client(data["owner"])
    future = create_program_slot(client, data["entry"].pk, hours=3).json()
    visible = create_program_slot(client, data["entry"].pk, hours=0.5).json()
    cancelled = create_program_slot(client, data["entry"].pk, hours=0.5).json()
    Notification.objects.filter(pk=cancelled["reminder"]["id"]).update(
        status=NotificationStatus.CANCELLED
    )

    listed = client.get(NOTIFICATIONS_URL)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["results"]] == [
        visible["reminder"]["id"]
    ]
    for hidden_id in (future["reminder"]["id"], cancelled["reminder"]["id"]):
        assert client.get(f"{NOTIFICATIONS_URL}{hidden_id}/").status_code == 404

    read_url = f"{NOTIFICATIONS_URL}{visible['reminder']['id']}/read/"
    first = client.post(read_url, {}, format="json")
    second = client.post(read_url, {}, format="json")
    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == second.json()["status"] == "read"
    assert first.json()["read_at"] == second.json()["read_at"]


@pytest.mark.django_db
def test_n01_strict_is_current_filter(phase5_data):
    data = phase5_data
    client = api_client(data["owner"])
    current = create_program_slot(client, data["entry"].pk, hours=0.5).json()
    cancelled = create_program_slot(client, data["entry"].pk, hours=0.5).json()
    completed = create_program_slot(client, data["entry"].pk, hours=0.5).json()
    ScheduledSession.objects.filter(pk=cancelled["id"]).update(status="cancelled")
    ScheduledSession.objects.filter(pk=completed["id"]).update(status="completed")

    current_ids = {
        item["id"]
        for item in client.get(f"{NOTIFICATIONS_URL}?is_current=true").json()["results"]
    }
    inactive_ids = {
        item["id"]
        for item in client.get(f"{NOTIFICATIONS_URL}?is_current=false").json()[
            "results"
        ]
    }
    assert current["reminder"]["id"] in current_ids
    for inactive in (cancelled, completed):
        assert inactive["reminder"]["id"] not in current_ids
        assert inactive["reminder"]["id"] in inactive_ids

    invalid = client.get(f"{NOTIFICATIONS_URL}?is_current=1")
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "validation_error"


@pytest.mark.django_db
def test_reminder_failure_rolls_back_slot(phase5_data):
    data = phase5_data
    client = api_client(data["owner"])
    with patch.object(
        ReminderService, "create_for_session", side_effect=RuntimeError("reminder fail")
    ):
        with pytest.raises(RuntimeError, match="reminder fail"):
            create_program_slot(client, data["entry"].pk)
    assert ScheduledSession.objects.count() == 0
    assert Notification.objects.count() == 0


@pytest.mark.django_db
def test_owner_scoping_returns_404_for_program_slot_and_notification(phase5_data):
    data = phase5_data
    owner_client = api_client(data["owner"])
    other_client = api_client(data["other"])
    foreign_slot = create_program_slot(
        other_client, data["foreign_entry"].pk, hours=0.5
    )
    assert foreign_slot.status_code == 201
    slot_id = foreign_slot.json()["id"]
    reminder_id = foreign_slot.json()["reminder"]["id"]

    assert (
        create_program_slot(owner_client, data["foreign_entry"].pk).status_code == 404
    )
    assert owner_client.get(f"{SESSIONS_URL}{slot_id}/").status_code == 404
    assert owner_client.get(f"{NOTIFICATIONS_URL}{reminder_id}/").status_code == 404
    assert owner_client.get(f"{SESSIONS_URL}999999999/").status_code == 404
    assert owner_client.get(f"{NOTIFICATIONS_URL}999999999/").status_code == 404
    assert (
        owner_client.get(
            f"{SESSIONS_URL}?user_program_id={data['foreign_program'].pk}"
        ).status_code
        == 404
    )
    assert (
        owner_client.get(
            f"/api/v1/user-programs/{data['foreign_program'].pk}/progress/"
        ).status_code
        == 404
    )
    assert (
        owner_client.get("/api/v1/user-programs/999999999/progress/").status_code == 404
    )


@pytest.mark.django_db
def test_g02_g04_g08_show_real_total_planned(phase5_data):
    data = phase5_data
    client = api_client(data["owner"])
    assert create_program_slot(client, data["entry"].pk, hours=2).status_code == 201
    assert create_program_slot(client, data["entry"].pk, hours=3).status_code == 201

    summary = client.get("/api/v1/user-programs/").json()["results"][0]
    detail = client.get(f"/api/v1/user-programs/{data['program'].pk}/").json()
    progress = client.get(
        f"/api/v1/user-programs/{data['program'].pk}/progress/"
    ).json()
    assert summary["progress_percent"] == "0.0"
    assert detail["progress"] == {
        "total_planned": 2,
        "completed_planned": 0,
        "percent": "0.0",
    }
    assert progress["total_planned"] == 2
    assert progress["completed_planned"] == 0
    assert progress["percent"] == "0.0"
    assert progress["bonus_earned"] is False


@pytest.mark.django_db
def test_phase5_mutations_require_csrf_for_session_auth(phase5_data):
    data = phase5_data
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(data["owner"])
    payload = {
        "user_program_workout_id": data["entry"].pk,
        "source_workout_id": None,
        "scheduled_at": (timezone.now() + timedelta(hours=2)).isoformat(),
    }
    forbidden = client.post(SESSIONS_URL, payload, format="json")
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "csrf_failed"

    assert client.get("/api/v1/auth/csrf/").status_code == 200
    created = client.post(
        SESSIONS_URL,
        payload,
        format="json",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )
    assert created.status_code == 201


@pytest.mark.django_db(transaction=True)
def test_concurrent_reminder_creation_leaves_one_row(phase5_data):
    data = phase5_data
    session = ScheduledSession.objects.create(
        user=data["owner"],
        source_workout=data["workout"],
        scheduled_at=timezone.now() + timedelta(hours=2),
    )
    barrier = Barrier(2)

    def create_reminder():
        connections.close_all()
        try:
            with transaction.atomic():
                barrier.wait(timeout=5)
                current = ScheduledSession.objects.get(pk=session.pk)
                ReminderService.create_for_session(current)
            return "created"
        except IntegrityError:
            return "duplicate"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: create_reminder(), range(2)))

    assert sorted(results) == ["created", "duplicate"]
    assert Notification.objects.filter(scheduled_session=session).count() == 1
