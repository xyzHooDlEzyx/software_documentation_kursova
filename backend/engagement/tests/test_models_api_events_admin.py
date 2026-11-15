import importlib
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import IntegrityError, connections, transaction
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from catalog.models import (
    Exercise,
    ExerciseCategory,
    ProgramTemplate,
    ProgramTemplateStatus,
    Workout,
)
from engagement.events import WorkoutCompleted, WorkoutCompletedDispatcher
from engagement.handlers import default_workout_completed_dispatcher
from engagement.models import (
    Achievement,
    AchievementCode,
    Challenge,
    ChallengeParticipation,
    PointKind,
    PointTransaction,
    UserAchievement,
)
from execution.models import CompletedSession, ExerciseResult
from planning.models import ScheduledSession, UserProgram

User = get_user_model()


@pytest.fixture
def base_data(db):
    user = User.objects.create_user("phase6@example.test", "SecurePass2026!")
    other = User.objects.create_user("phase6-other@example.test", "SecurePass2026!")
    workout = Workout.objects.create(name="Phase 6", category=ExerciseCategory.CARDIO)
    exercise = Exercise.objects.create(
        name="Біг", category=ExerciseCategory.CARDIO, tracks_distance=True
    )
    return user, other, workout, exercise


@pytest.fixture
def seeded_achievements(db):
    """Re-run the 0003 seed: a preceding transaction=True test flushes the
    database, which also deletes rows created by data migrations."""
    from django.apps import apps

    seed = importlib.import_module("engagement.migrations.0003_seed_achievements")
    seed.seed_achievements(apps, None)


def completed(user, workout, *, key="key", duration="30", completed_at=None):
    return CompletedSession.objects.create(
        user=user,
        source_workout=workout,
        source_workout_id_snapshot=workout.pk,
        source_workout_name_snapshot=workout.name,
        performed_workout_name_snapshot=workout.name,
        performed_workout_category_snapshot=workout.category,
        completed_at=completed_at or timezone.now(),
        duration_min=Decimal(duration),
        missing_calorie_reason="missing_met",
        idempotency_key=key,
        request_payload_sha256="a" * 64,
    )


def user_program(user):
    template = ProgramTemplate.objects.create(
        name="Phase 6 template",
        fitness_goal="maintenance",
        experience_level="beginner",
        workouts_per_week=3,
        status=ProgramTemplateStatus.PUBLISHED,
    )
    return UserProgram.objects.create(
        user=user,
        source_program_template=template,
        source_program_template_name_snapshot=template.name,
        name="Phase 6 program",
        fitness_goal="maintenance",
    )


@pytest.mark.django_db
def test_execution_unique_key_per_user_and_same_key_for_other(base_data):
    user, other, workout, _ = base_data
    completed(user, workout)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            completed(user, workout)
    assert completed(other, workout).pk


@pytest.mark.django_db
def test_ledger_xor_and_workout_uniqueness(base_data):
    user, _, workout, _ = base_data
    session = completed(user, workout)
    PointTransaction.objects.create(
        user=user,
        completed_session=session,
        point_kind=PointKind.WORKOUT_COMPLETION,
        points=10,
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PointTransaction.objects.create(
                user=user,
                completed_session=session,
                point_kind=PointKind.WORKOUT_COMPLETION,
                points=10,
            )


@pytest.mark.django_db
def test_one_completed_session_per_slot_and_one_bonus_per_program(base_data):
    user, _, workout, _ = base_data
    program = user_program(user)
    slot = ScheduledSession.objects.create(
        user=user,
        user_program=program,
        source_workout=workout,
        scheduled_at=timezone.now(),
    )
    first = completed(user, workout, key="slot-1")
    first.scheduled_session = slot
    first.save(update_fields=["scheduled_session"])
    second = completed(user, workout, key="slot-2")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            second.scheduled_session = slot
            second.save(update_fields=["scheduled_session"])

    PointTransaction.objects.create(
        user=user,
        user_program=program,
        point_kind=PointKind.PROGRAM_COMPLETION,
        points=50,
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PointTransaction.objects.create(
                user=user,
                user_program=program,
                point_kind=PointKind.PROGRAM_COMPLETION,
                points=50,
            )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PointTransaction.objects.create(
                user=user,
                point_kind=PointKind.WORKOUT_COMPLETION,
                points=10,
            )


@pytest.mark.django_db
def test_unique_user_achievement_and_participation(base_data):
    user, _, _, _ = base_data
    achievement = Achievement.objects.get(code=AchievementCode.FIRST_WORKOUT)
    UserAchievement.objects.create(
        user=user,
        achievement=achievement,
        name_snapshot=achievement.name,
        rule_code_snapshot=achievement.rule_code,
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            UserAchievement.objects.create(
                user=user,
                achievement=achievement,
                name_snapshot=achievement.name,
                rule_code_snapshot=achievement.rule_code,
            )
    challenge = Challenge.objects.create(
        name="Test",
        start_at=timezone.now() - timedelta(days=1),
        end_at=timezone.now() + timedelta(days=1),
        goal_kind="workouts",
        goal_value=1,
    )
    ChallengeParticipation.objects.create(user=user, challenge=challenge)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ChallengeParticipation.objects.create(user=user, challenge=challenge)


@pytest.mark.django_db
def test_seed_contains_exact_confirmed_codes_and_is_idempotent():
    expected = set(AchievementCode.values)
    assert set(Achievement.objects.values_list("code", flat=True)) == expected
    before = Achievement.objects.count()
    for achievement in Achievement.objects.all():
        Achievement.objects.update_or_create(
            code=achievement.code,
            defaults={
                "name": achievement.name,
                "description": achievement.description,
                "rule_code": achievement.rule_code,
                "is_archived": False,
            },
        )
    assert Achievement.objects.count() == before == 5


@pytest.mark.django_db
def test_seed_migration_function_is_idempotent():
    migration = importlib.import_module("engagement.migrations.0003_seed_achievements")
    from django.apps import apps

    migration.seed_achievements(apps, None)
    migration.seed_achievements(apps, None)
    assert Achievement.objects.count() == 5


@pytest.mark.django_db
def test_dispatcher_required_order_and_rollback(base_data):
    user, _, workout, _ = base_data
    calls = []

    class Handler:
        def __init__(self, name, fail=False):
            self.name = name
            self.fail = fail

        def handle(self, event):
            calls.append(self.name)
            if self.fail:
                raise RuntimeError("required failure")

    dispatcher = WorkoutCompletedDispatcher()
    dispatcher.register(Handler("points"))
    dispatcher.register(Handler("achievement", fail=True))
    dispatcher.register(Handler("challenge"))
    with pytest.raises(RuntimeError):
        with transaction.atomic():
            session = completed(user, workout)
            dispatcher.dispatch(
                WorkoutCompleted(
                    session.pk, user.pk, session.completed_at, session.duration_min
                )
            )
    assert calls == ["points", "achievement"]
    assert CompletedSession.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_dispatcher_optional_failure_does_not_rollback(base_data):
    user, _, workout, _ = base_data

    class Noop:
        def handle(self, event):
            return None

    class Fail:
        def handle(self, event):
            raise RuntimeError("optional failure")

    with transaction.atomic():
        session = completed(user, workout)
        dispatcher = WorkoutCompletedDispatcher()
        dispatcher.register(Noop())
        dispatcher.register(Noop())
        dispatcher.register(Noop())
        dispatcher.register(Fail(), required=False)
        dispatcher.dispatch(
            WorkoutCompleted(
                session.pk, user.pk, session.completed_at, session.duration_min
            )
        )
    assert CompletedSession.objects.filter(pk=session.pk).exists()


@pytest.mark.django_db
def test_handlers_award_categories_without_double_award(base_data):
    user, _, workout, exercise = base_data
    session = completed(user, workout, duration="100")
    ExerciseResult.objects.create(
        completed_session=session,
        source_exercise=exercise,
        source_exercise_id_snapshot=exercise.pk,
        exercise_name_snapshot=exercise.name,
        exercise_category_snapshot="cardio",
        position=1,
        actual_distance_km=Decimal("42.200"),
    )
    event = WorkoutCompleted(
        session.pk, user.pk, session.completed_at, session.duration_min
    )
    dispatcher = default_workout_completed_dispatcher()
    with transaction.atomic():
        dispatcher.dispatch(event)
        dispatcher.dispatch(event)
    assert PointTransaction.objects.filter(completed_session=session).count() == 1
    assert set(
        UserAchievement.objects.filter(user=user).values_list(
            "achievement__code", flat=True
        )
    ) == {
        AchievementCode.FIRST_WORKOUT,
        AchievementCode.ONE_HUNDRED_MINUTES,
        AchievementCode.MARATHONER,
    }


@pytest.mark.django_db(transaction=True)
def test_concurrent_dispatch_serializes_achievement_facts(
    base_data, seeded_achievements
):
    user, _, workout, _ = base_data
    for index in range(3):
        completed(user, workout, key=f"existing-{index}", duration="1")
    barrier = Barrier(2)

    def complete_and_dispatch(index):
        connections["default"].close()
        try:
            with transaction.atomic():
                thread_user = User.objects.get(pk=user.pk)
                thread_workout = Workout.objects.get(pk=workout.pk)
                session = completed(
                    thread_user,
                    thread_workout,
                    key=f"concurrent-{index}",
                    duration="1",
                )
                barrier.wait(timeout=10)
                default_workout_completed_dispatcher().dispatch(
                    WorkoutCompleted(
                        session.pk,
                        thread_user.pk,
                        session.completed_at,
                        session.duration_min,
                    )
                )
        finally:
            connections["default"].close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(complete_and_dispatch, index) for index in range(2)]
        for future in futures:
            future.result(timeout=20)

    assert CompletedSession.objects.filter(user=user).count() == 5
    assert (
        UserAchievement.objects.filter(
            user=user, achievement__code=AchievementCode.FIVE_WORKOUTS
        ).count()
        == 1
    )


def auth_client(user, *, csrf=False):
    client = APIClient(enforce_csrf_checks=csrf)
    if csrf:
        client.force_login(user)
    else:
        client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_h01_h02_auth_visibility_and_filter(base_data):
    user, _, _, _ = base_data
    now = timezone.now()
    active = Challenge.objects.create(
        name="Active",
        start_at=now - timedelta(hours=1),
        end_at=now + timedelta(hours=1),
        goal_kind="workouts",
        goal_value=2,
    )
    hidden = Challenge.objects.create(
        name="Hidden",
        start_at=now,
        end_at=now + timedelta(hours=1),
        goal_kind="minutes",
        goal_value=10,
        is_archived=True,
    )
    assert APIClient().get("/api/v1/challenges/").status_code == 401
    client = auth_client(user)
    response = client.get("/api/v1/challenges/?state=active")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["results"]] == [active.pk]
    assert client.get(f"/api/v1/challenges/{hidden.pk}/").status_code == 404


@pytest.mark.django_db
def test_h03_csrf_retry_and_expired(base_data):
    user, _, workout, _ = base_data
    now = timezone.now()
    challenge = Challenge.objects.create(
        name="Join",
        start_at=now - timedelta(hours=1),
        end_at=now + timedelta(hours=1),
        goal_kind="workouts",
        goal_value=3,
    )
    client = auth_client(user, csrf=True)
    url = f"/api/v1/challenges/{challenge.pk}/join/"
    denied = client.post(url, {}, format="json")
    assert denied.status_code == 403
    client.get("/api/v1/auth/csrf/")
    token = client.cookies["csrftoken"].value
    first = client.post(url, {}, format="json", HTTP_X_CSRFTOKEN=token)
    retry = client.post(url, {}, format="json", HTTP_X_CSRFTOKEN=token)
    assert first.status_code == 201
    assert retry.status_code == 200
    assert retry.json()["id"] == first.json()["id"]
    participation = ChallengeParticipation.objects.get(pk=first.json()["id"])
    participation.joined_at = timezone.now() - timedelta(minutes=10)
    participation.save(update_fields=["joined_at"])
    completed(
        user,
        workout,
        key="joined-fact-1",
        duration="20",
        completed_at=participation.joined_at + timedelta(minutes=1),
    )
    completed(
        user,
        workout,
        key="joined-fact-2",
        duration="20",
        completed_at=participation.joined_at + timedelta(minutes=2),
    )
    retry_with_facts = client.post(url, {}, format="json", HTTP_X_CSRFTOKEN=token)
    assert retry_with_facts.status_code == 200
    assert retry_with_facts.json()["progress_value"] == 2
    assert retry_with_facts.json()["status"] == "joined"
    challenge.end_at = timezone.now() - timedelta(seconds=1)
    challenge.save(update_fields=["end_at"])
    expired_retry = client.post(url, {}, format="json", HTTP_X_CSRFTOKEN=token)
    assert expired_retry.status_code == 200
    assert expired_retry.json()["progress_value"] == 2
    assert expired_retry.json()["status"] == "expired"
    expired = Challenge.objects.create(
        name="Expired",
        start_at=now - timedelta(days=2),
        end_at=now - timedelta(days=1),
        goal_kind="minutes",
        goal_value=10,
    )
    response = client.post(
        f"/api/v1/challenges/{expired.pk}/join/",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_state"


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_join_returns_one_participation(base_data):
    user, _, _, _ = base_data
    challenge = Challenge.objects.create(
        name="Concurrent join",
        start_at=timezone.now() - timedelta(hours=1),
        end_at=timezone.now() + timedelta(hours=1),
        goal_kind="workouts",
        goal_value=3,
    )
    barrier = Barrier(2)

    def join():
        from engagement.services import ChallengeParticipationService

        connections["default"].close()
        try:
            thread_user = User.objects.get(pk=user.pk)
            barrier.wait(timeout=10)
            participation, created = ChallengeParticipationService.join(
                user=thread_user, challenge_id=challenge.pk
            )
            return participation.pk, created
        finally:
            connections["default"].close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(join) for _ in range(2)]
        results = [future.result(timeout=20) for future in futures]

    assert len({participation_id for participation_id, _ in results}) == 1
    assert sorted(created for _, created in results) == [False, True]
    assert (
        ChallengeParticipation.objects.filter(user=user, challenge=challenge).count()
        == 1
    )


@pytest.mark.django_db
def test_admin_permissions_and_private_models_not_registered(base_data):
    user, _, _, _ = base_data
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    client = APIClient()
    client.force_login(user)
    assert (
        client.get(reverse("admin:engagement_challenge_changelist")).status_code == 403
    )

    user.groups.add(Group.objects.get(name="Administrator"))
    assert client.get(reverse("admin:engagement_challenge_add")).status_code == 200
    assert (
        client.get(reverse("admin:engagement_achievement_changelist")).status_code
        == 200
    )
    assert admin.site.is_registered(Challenge)
    assert admin.site.is_registered(Achievement)
    for model in (
        CompletedSession,
        ExerciseResult,
        PointTransaction,
        UserAchievement,
        ChallengeParticipation,
    ):
        assert not admin.site.is_registered(model)


@pytest.mark.django_db
def test_view_only_staff_cannot_run_challenge_publish_actions(base_data):
    user, _, _, _ = base_data
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="engagement", codename="view_challenge"
        )
    )
    request = RequestFactory().get(reverse("admin:engagement_challenge_changelist"))
    request.user = user
    actions = admin.site.get_model_admin(Challenge).get_actions(request)
    assert "publish_selected" not in actions
    assert "unpublish_selected" not in actions


@pytest.mark.django_db
def test_administrator_cannot_delete_or_change_achievement(base_data):
    user, _, _, _ = base_data
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    user.groups.add(Group.objects.get(name="Administrator"))
    client = APIClient()
    client.force_login(user)
    achievement = Achievement.objects.get(code=AchievementCode.FIRST_WORKOUT)
    change_url = reverse("admin:engagement_achievement_change", args=[achievement.pk])
    delete_url = reverse("admin:engagement_achievement_delete", args=[achievement.pk])
    before = achievement.name
    response = client.post(change_url, {"name": "Змінено"})
    achievement.refresh_from_db()
    assert response.status_code == 403
    assert achievement.name == before
    assert client.get(delete_url).status_code == 403


@pytest.mark.django_db
def test_administrator_can_add_change_and_publish_challenge(base_data):
    user, _, _, _ = base_data
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    user.groups.add(Group.objects.get(name="Administrator"))
    client = APIClient()
    client.force_login(user)
    now = timezone.localtime().replace(second=0, microsecond=0)
    response = client.post(
        reverse("admin:engagement_challenge_add"),
        {
            "name": "Адмін-челендж",
            "start_at_0": now.date().isoformat(),
            "start_at_1": now.time().isoformat(timespec="minutes"),
            "end_at_0": (now + timedelta(days=2)).date().isoformat(),
            "end_at_1": now.time().isoformat(timespec="minutes"),
            "goal_kind": "workouts",
            "goal_value": "3",
            "_save": "Зберегти",
        },
    )
    assert response.status_code == 302
    challenge = Challenge.objects.get(name="Адмін-челендж")
    change = client.post(
        reverse("admin:engagement_challenge_change", args=[challenge.pk]),
        {
            "name": "Оновлений челендж",
            "start_at_0": timezone.localtime(challenge.start_at).date().isoformat(),
            "start_at_1": timezone.localtime(challenge.start_at)
            .time()
            .isoformat(timespec="minutes"),
            "end_at_0": timezone.localtime(challenge.end_at).date().isoformat(),
            "end_at_1": timezone.localtime(challenge.end_at)
            .time()
            .isoformat(timespec="minutes"),
            "goal_kind": challenge.goal_kind,
            "goal_value": str(challenge.goal_value),
            "_save": "Зберегти",
        },
    )
    assert change.status_code == 302
    challenge.refresh_from_db()
    assert challenge.name == "Оновлений челендж"
    assert not admin.site.get_model_admin(Challenge).has_delete_permission(
        response.wsgi_request, challenge
    )
