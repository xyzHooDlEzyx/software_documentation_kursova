from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import WeightEntry
from accounts.selectors import kyiv_date_range_to_utc
from catalog.models import Exercise, Workout
from config.timezones import KYIV_TZ
from engagement.models import (
    Achievement,
    Challenge,
    ChallengeParticipation,
    PointKind,
    PointTransaction,
    UserAchievement,
)
from execution.models import CompletedSession, ExerciseResult
from reporting.selectors import StatisticsQueryService

User = get_user_model()


def api_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def fact(user, workout, *, when, key, duration="30.00", calories="120.00"):
    session = CompletedSession.objects.create(
        user=user,
        source_workout=workout,
        source_workout_id_snapshot=workout.pk,
        source_workout_name_snapshot=workout.name,
        performed_workout_name_snapshot=workout.name,
        performed_workout_category_snapshot=workout.category,
        completed_at=when,
        duration_min=duration,
        estimated_calories=calories,
        missing_calorie_reason=None if calories is not None else "missing_met",
        idempotency_key=key,
        request_payload_sha256="a" * 64,
    )
    PointTransaction.objects.create(
        user=user,
        completed_session=session,
        point_kind=PointKind.WORKOUT_COMPLETION,
        points=20,
        awarded_at=when,
    )
    return session


@pytest.fixture
def phase8(db):
    user = User.objects.create_user("phase8@example.test", "SecurePass2026!")
    other = User.objects.create_user("phase8-other@example.test", "SecurePass2026!")
    workout = Workout.objects.create(name="Ранкова руханка", category="cardio")
    exercise = Exercise.objects.create(
        name="Біг", category="cardio", tracks_distance=True
    )
    return user, other, workout, exercise


@pytest.mark.django_db
def test_weight_chart_empty_order_and_same_timestamp_last_created(phase8):
    user, _, _, _ = phase8
    api = api_for(user)
    url = "/api/v1/statistics/weight-chart/?start_date=2026-10-01&end_date=2026-11-01"
    assert api.get(url).json()["points"] == []
    when = datetime(2026, 10, 25, 1, tzinfo=dt_timezone.utc)
    WeightEntry.objects.create(user=user, measured_at=when, weight_kg="70.0")
    WeightEntry.objects.create(user=user, measured_at=when, weight_kg="69.0")
    points = api.get(url).json()["points"]
    assert [row["weight_kg"] for row in points] == ["70.0", "69.0"]


@pytest.mark.django_db
def test_kyiv_dst_boundaries_use_real_offsets():
    spring = kyiv_date_range_to_utc(date(2026, 3, 29), date(2026, 3, 30))
    autumn = kyiv_date_range_to_utc(date(2026, 10, 25), date(2026, 10, 26))
    assert spring[1] - spring[0] == timedelta(hours=23)
    assert autumn[1] - autumn[0] == timedelta(hours=25)


@pytest.mark.django_db
def test_overview_counts_null_calories_separately_and_get_is_read_only(phase8):
    user, _, workout, exercise = phase8
    when = datetime(2026, 10, 10, 10, tzinfo=dt_timezone.utc)
    first = fact(user, workout, when=when, key="one", duration="45", calories="100")
    fact(user, workout, when=when + timedelta(hours=1), key="two", calories=None)
    ExerciseResult.objects.create(
        completed_session=first,
        source_exercise=exercise,
        source_exercise_id_snapshot=exercise.pk,
        exercise_name_snapshot=exercise.name,
        exercise_category_snapshot=exercise.category,
        position=1,
        actual_duration_min="45",
    )
    before = (CompletedSession.objects.count(), PointTransaction.objects.count())
    response = api_for(user).get(
        "/api/v1/statistics/overview/?start_date=2026-10-01&end_date=2026-11-01"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["completed_workouts"] == 2
    assert payload["performed_exercises"] == 1
    assert payload["workouts_without_calorie_estimate"] == 1
    assert before == (
        CompletedSession.objects.count(),
        PointTransaction.objects.count(),
    )


@pytest.mark.django_db
def test_overview_empty_period_has_zero_weekly_buckets_without_gaps(phase8):
    user, _, _, _ = phase8
    response = api_for(user).get(
        "/api/v1/statistics/overview/?start_date=2026-10-22&end_date=2026-11-03"
    )
    assert response.status_code == 200
    assert response.json()["weekly_activity"] == [
        {
            "week_start": "2026-10-19",
            "completed_workouts": 0,
            "total_duration_min": "0.00",
        },
        {
            "week_start": "2026-10-26",
            "completed_workouts": 0,
            "total_duration_min": "0.00",
        },
        {
            "week_start": "2026-11-02",
            "completed_workouts": 0,
            "total_duration_min": "0.00",
        },
    ]


@pytest.mark.django_db
def test_overview_dst_week_assigns_sunday_2330_kyiv_to_that_week(phase8):
    user, _, workout, _ = phase8
    sunday_late = datetime(2026, 10, 25, 23, 30, tzinfo=KYIV_TZ)
    fact(
        user,
        workout,
        when=sunday_late.astimezone(dt_timezone.utc),
        key="dst-sunday",
        duration="35.00",
    )
    response = api_for(user).get(
        "/api/v1/statistics/overview/?start_date=2026-10-19&end_date=2026-10-26"
    )
    assert response.status_code == 200
    assert response.json()["weekly_activity"] == [
        {
            "week_start": "2026-10-19",
            "completed_workouts": 1,
            "total_duration_min": "35.00",
        }
    ]


@pytest.mark.django_db
def test_weekly_activity_clips_unaligned_period_in_one_sql_query(
    phase8, django_assert_num_queries
):
    user, _, workout, _ = phase8
    before_period = datetime(2026, 10, 21, 12, tzinfo=KYIV_TZ)
    first_intersection = datetime(2026, 10, 22, 0, tzinfo=KYIV_TZ)
    second_week = datetime(2026, 10, 26, 10, tzinfo=KYIV_TZ)
    fact(
        user,
        workout,
        when=before_period.astimezone(dt_timezone.utc),
        key="before-clipped-period",
        duration="90.00",
    )
    fact(
        user,
        workout,
        when=first_intersection.astimezone(dt_timezone.utc),
        key="first-intersection",
        duration="20.00",
    )
    fact(
        user,
        workout,
        when=second_week.astimezone(dt_timezone.utc),
        key="second-week",
        duration="30.00",
    )
    with django_assert_num_queries(1):
        buckets = StatisticsQueryService.weekly_activity(
            user=user,
            start_date=date(2026, 10, 22),
            end_date=date(2026, 10, 27),
        )
    assert buckets == [
        {
            "week_start": date(2026, 10, 19),
            "completed_workouts": 1,
            "total_duration_min": Decimal("20.00"),
        },
        {
            "week_start": date(2026, 10, 26),
            "completed_workouts": 1,
            "total_duration_min": Decimal("30.00"),
        },
    ]


@pytest.mark.django_db
def test_e02_e03_owner_scope_and_snapshots_survive_catalog_change(phase8):
    user, other, workout, exercise = phase8
    session = fact(user, workout, when=timezone.now(), key="history")
    ExerciseResult.objects.create(
        completed_session=session,
        source_exercise=exercise,
        source_exercise_id_snapshot=exercise.pk,
        exercise_name_snapshot="Біг snapshot",
        exercise_category_snapshot="cardio",
        position=1,
        actual_duration_min="30",
    )
    workout.name = "Змінена назва"
    workout.is_archived = True
    workout.save(update_fields=["name", "is_archived"])
    own = api_for(user).get(f"/api/v1/completed-sessions/{session.pk}/")
    assert own.status_code == 200
    assert own.json()["source_workout_name_snapshot"] == "Ранкова руханка"
    assert own.json()["results"][0]["exercise_name_snapshot"] == "Біг snapshot"
    assert (
        api_for(other).get(f"/api/v1/completed-sessions/{session.pk}/").status_code
        == 404
    )


@pytest.mark.django_db
def test_points_achievements_and_unlock_snapshots(phase8):
    user, _, workout, _ = phase8
    session = fact(user, workout, when=timezone.now(), key="points")
    # Seeded by engagement.0003; creating it again violates the unique code.
    achievement = Achievement.objects.get(code="first_workout")
    UserAchievement.objects.create(
        user=user,
        achievement=achievement,
        name_snapshot="Перше тренування",
        rule_code_snapshot="first_workout",
    )
    api = api_for(user)
    assert api.get("/api/v1/points/summary/").json()["total_points"] == 20
    assert (
        api.get("/api/v1/point-transactions/?point_kind=workout_completion").json()[
            "count"
        ]
        == 1
    )
    assert api.get("/api/v1/achievements/").json()["results"][0]["earned"] is True
    achievement.is_archived = True
    achievement.name = "Змінено"
    achievement.save()
    unlocked = api.get("/api/v1/user-achievements/").json()["results"][0]
    assert unlocked["name_snapshot"] == "Перше тренування"
    assert PointTransaction.objects.get(completed_session=session).points == 20


@pytest.mark.django_db
def test_h04_keeps_archived_joined_challenge_and_derives_expired(phase8):
    user, _, _, _ = phase8
    now = timezone.now()
    challenge = Challenge.objects.create(
        name="Осінь",
        start_at=now - timedelta(days=10),
        end_at=now - timedelta(days=1),
        goal_kind="workouts",
        goal_value=5,
        is_archived=True,
    )
    ChallengeParticipation.objects.create(
        user=user, challenge=challenge, joined_at=now - timedelta(days=9)
    )
    response = api_for(user).get("/api/v1/challenge-participations/?status=expired")
    assert response.status_code == 200
    assert response.json()["results"][0]["status"] == "expired"
    assert response.json()["results"][0]["challenge_name"] == "Осінь"


@pytest.mark.django_db
def test_leaderboard_privacy_self_and_confirmed_tie_break(phase8):
    user, other, workout, _ = phase8
    third = User.objects.create_user(
        "third@example.test",
        "SecurePass2026!",
        public_alias="Third",
        leaderboard_opt_in=True,
    )
    fourth = User.objects.create_user(
        "fourth@example.test",
        "SecurePass2026!",
        public_alias="Fourth",
        leaderboard_opt_in=True,
    )
    fifth = User.objects.create_user(
        "fifth@example.test",
        "SecurePass2026!",
        public_alias="Fifth",
        leaderboard_opt_in=True,
    )
    other.public_alias = "Other"
    other.leaderboard_opt_in = True
    other.save(update_fields=["public_alias", "leaderboard_opt_in"])
    now = timezone.now()
    fact(other, workout, when=now - timedelta(hours=2), key="o1")
    fact(fourth, workout, when=now - timedelta(hours=3), key="f1")
    fact(fifth, workout, when=now - timedelta(hours=3), key="f2")
    third_first = fact(third, workout, when=now - timedelta(hours=1), key="t1")
    third_second = fact(third, workout, when=now, key="t2")
    PointTransaction.objects.filter(
        completed_session__in=(third_first, third_second)
    ).update(points=10)
    result = api_for(user).get("/api/v1/leaderboard/?period=all").json()
    assert [row["public_alias"] for row in result["results"]] == [
        "Third",
        "Fourth",
        "Fifth",
        "Other",
    ]
    assert set(result["results"][0]) == {"rank", "public_alias", "points"}
    assert result["self"] == {"opted_in": False, "points": 0, "rank": None}
    assert "email" not in str(result)


@pytest.mark.django_db
def test_leaderboard_excludes_deactivated_opted_in_accounts(phase8):
    user, other, workout, _ = phase8
    other.public_alias = "InactiveAlias"
    other.leaderboard_opt_in = True
    other.save(update_fields=["public_alias", "leaderboard_opt_in"])
    fact(other, workout, when=timezone.now(), key="inactive-points")
    other.is_active = False
    other.save(update_fields=["is_active"])
    result = api_for(user).get("/api/v1/leaderboard/?period=all").json()
    assert result["results"] == []
    assert result["count"] == 0


@pytest.mark.django_db
def test_strict_query_params_return_400(phase8):
    user, _, _, _ = phase8
    api = api_for(user)
    assert api.get("/api/v1/statistics/overview/?unexpected=1").status_code == 400
    assert (
        api.get("/api/v1/leaderboard/?period=all&anchor_date=2026-10-01").status_code
        == 400
    )
    assert (
        api.get("/api/v1/completed-sessions/?start_date=2026-10-01").status_code == 400
    )


def grant_report_permission(user):
    permission = Permission.objects.get(
        content_type__app_label="reporting", codename="view_reports"
    )
    group, _ = Group.objects.get_or_create(name="Administrator")
    group.permissions.add(permission)
    user.groups.add(group)


@pytest.mark.django_db
def test_admin_reports_permission_and_empty_denominators(client):
    staff = User.objects.create_user(
        "staff@example.test", "SecurePass2026!", is_staff=True
    )
    client.force_login(staff)
    url = reverse("admin-average-activity-report")
    assert (
        client.get(
            url, {"start_date": "2026-10-01", "end_date": "2026-11-01"}
        ).status_code
        == 403
    )
    grant_report_permission(staff)
    index = client.get(reverse("admin:index"))
    assert reverse("admin-workout-popularity-report").encode() in index.content
    assert reverse("admin-average-activity-report").encode() in index.content
    response = client.get(url, {"start_date": "2020-01-01", "end_date": "2020-02-01"})
    assert response.status_code == 200
    # HTML is localised for uk (decimal comma); CSV stays machine-readable.
    assert "0,00" in response.content.decode()
    assert b"<svg" in response.content
    csv_response = client.get(
        url, {"start_date": "2020-01-01", "end_date": "2020-02-01", "format": "csv"}
    )
    assert "0.00" in csv_response.content.decode("utf-8-sig")


@pytest.mark.django_db
def test_popularity_archived_order_csv_bom_and_formula_escape(phase8, client):
    user, _, workout, _ = phase8
    workout.name = "=Небезпечна назва"
    workout.is_archived = True
    workout.save()
    fact(user, workout, when=datetime(2026, 10, 10, tzinfo=dt_timezone.utc), key="csv")
    staff = User.objects.create_user(
        "admin@example.test", "SecurePass2026!", is_staff=True
    )
    grant_report_permission(staff)
    client.force_login(staff)
    url = reverse("admin-workout-popularity-report")
    params = {"start_date": "2026-10-01", "end_date": "2026-11-01", "format": "csv"}
    response = client.get(url, params)
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert response.content.startswith("\ufeff".encode())
    assert "'=Небезпечна назва" in response.content.decode("utf-8-sig")


@pytest.mark.django_db
def test_average_activity_includes_deactivated_user_and_half_up(phase8, client):
    user, other, workout, _ = phase8
    user.registered_at = datetime(2026, 10, 1, tzinfo=dt_timezone.utc)
    user.save(update_fields=["registered_at"])
    other.registered_at = datetime(2026, 10, 31, tzinfo=dt_timezone.utc)
    other.is_active = False
    other.save(update_fields=["registered_at", "is_active"])
    fact(
        user,
        workout,
        when=datetime(2026, 10, 10, tzinfo=dt_timezone.utc),
        key="avg",
        duration="1",
    )
    staff = User.objects.create_user(
        "report@example.test", "SecurePass2026!", is_staff=True
    )
    staff.registered_at = datetime(2027, 1, 1, tzinfo=dt_timezone.utc)
    staff.save(update_fields=["registered_at"])
    grant_report_permission(staff)
    client.force_login(staff)
    response = client.get(
        reverse("admin-average-activity-report"),
        {"start_date": "2026-10-01", "end_date": "2026-11-01"},
    )
    assert response.status_code == 200
    assert "0,50" in response.content.decode()
