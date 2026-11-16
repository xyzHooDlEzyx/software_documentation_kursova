from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import Count, Max, Q, Sum, Value
from django.db.models.functions import Coalesce

from accounts.models import WeightEntry
from accounts.selectors import kyiv_date_range_to_utc
from config.timezones import KYIV_TZ
from engagement.models import PointKind, PointTransaction
from execution.models import CompletedSession, ExerciseResult

User = get_user_model()
ZERO = Decimal("0.00")


def decimal_2(value) -> Decimal:
    return Decimal(value or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class StatisticsQueryService:
    @staticmethod
    def weight_chart(*, user, start_date: date, end_date: date):
        start_utc, end_utc = kyiv_date_range_to_utc(start_date, end_date)
        return WeightEntry.objects.filter(
            user=user, measured_at__gte=start_utc, measured_at__lt=end_utc
        ).order_by("measured_at", "id")

    @staticmethod
    def overview(*, user, start_date: date, end_date: date) -> dict:
        start_utc, end_utc = kyiv_date_range_to_utc(start_date, end_date)
        sessions = CompletedSession.objects.filter(
            user=user, completed_at__gte=start_utc, completed_at__lt=end_utc
        )
        totals = sessions.aggregate(
            completed_workouts=Count("id"),
            total_duration=Coalesce(Sum("duration_min"), Value(ZERO)),
            calories=Coalesce(Sum("estimated_calories"), Value(ZERO)),
            missing_calories=Count("id", filter=Q(estimated_calories__isnull=True)),
        )
        totals["performed_exercises"] = ExerciseResult.objects.filter(
            completed_session__in=sessions
        ).count()
        totals["weekly_activity"] = StatisticsQueryService.weekly_activity(
            user=user,
            start_date=start_date,
            end_date=end_date,
            start_utc=start_utc,
            end_utc=end_utc,
        )
        return totals

    @staticmethod
    def weekly_activity(
        *,
        user,
        start_date: date,
        end_date: date,
        start_utc: datetime | None = None,
        end_utc: datetime | None = None,
    ) -> list[dict]:
        if start_utc is None or end_utc is None:
            start_utc, end_utc = kyiv_date_range_to_utc(start_date, end_date)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH weeks AS (
                    SELECT generate_series(
                        date_trunc('week', %s::date)::date,
                        date_trunc('week', (%s::date - 1))::date,
                        interval '1 week'
                    )::date AS week_start
                )
                SELECT
                    weeks.week_start,
                    COUNT(completed_sessions.id)::integer AS completed_workouts,
                    COALESCE(SUM(completed_sessions.duration_min), 0)::numeric
                        AS total_duration_min
                FROM weeks
                LEFT JOIN completed_sessions
                    ON completed_sessions.user_id = %s
                    AND completed_sessions.completed_at >= GREATEST(
                        %s::timestamptz,
                        weeks.week_start::timestamp
                            AT TIME ZONE 'Europe/Kyiv'
                    )
                    AND completed_sessions.completed_at < LEAST(
                        %s::timestamptz,
                        (weeks.week_start + 7)::timestamp
                            AT TIME ZONE 'Europe/Kyiv'
                    )
                GROUP BY weeks.week_start
                ORDER BY weeks.week_start
                """,
                [start_date, end_date, user.pk, start_utc, end_utc],
            )
            return [
                {
                    "week_start": week_start,
                    "completed_workouts": completed_workouts,
                    "total_duration_min": decimal_2(total_duration_min),
                }
                for week_start, completed_workouts, total_duration_min in (
                    cursor.fetchall()
                )
            ]

    @staticmethod
    def points_summary(
        *, user, start_date: date | None = None, end_date: date | None = None
    ):
        queryset = PointTransaction.objects.filter(user=user)
        if start_date is not None and end_date is not None:
            start_utc, end_utc = kyiv_date_range_to_utc(start_date, end_date)
            queryset = queryset.filter(
                awarded_at__gte=start_utc, awarded_at__lt=end_utc
            )
        return queryset.aggregate(
            total_points=Coalesce(Sum("points"), 0),
            workout_points=Coalesce(
                Sum("points", filter=Q(point_kind=PointKind.WORKOUT_COMPLETION)), 0
            ),
            program_bonus_points=Coalesce(
                Sum("points", filter=Q(point_kind=PointKind.PROGRAM_COMPLETION)), 0
            ),
        )


class ReportQueryService:
    @staticmethod
    def workout_popularity(*, start_at: datetime, end_at: datetime):
        return (
            CompletedSession.objects.filter(
                completed_at__gte=start_at, completed_at__lt=end_at
            )
            .values(
                "source_workout_id",
                "source_workout__name",
                "source_workout__is_archived",
            )
            .annotate(completed_count=Count("id"))
            .order_by("-completed_count", "source_workout__name", "source_workout_id")
        )

    @staticmethod
    def average_activity(*, start_at: datetime, end_at: datetime) -> dict:
        total_users = User.objects.filter(registered_at__lt=end_at).count()
        sessions = CompletedSession.objects.filter(
            completed_at__gte=start_at, completed_at__lt=end_at
        )
        totals = sessions.aggregate(
            total_completed=Count("id"),
            total_minutes=Coalesce(Sum("duration_min"), Value(ZERO)),
            active_users=Count("user_id", distinct=True),
        )
        completed = totals["total_completed"]
        minutes = totals["total_minutes"]
        active = totals["active_users"]
        return {
            "total_users": total_users,
            **totals,
            "average_workouts": decimal_2(
                Decimal(completed) / total_users if total_users else 0
            ),
            "average_duration_min": decimal_2(
                minutes / total_users if total_users else 0
            ),
            "average_among_active": decimal_2(
                Decimal(completed) / active if active else 0
            ),
        }


@dataclass(frozen=True)
class LeaderboardPeriod:
    kind: str
    start_at: datetime | None
    end_at: datetime | None


class LeaderboardQueryService:
    @staticmethod
    def period(kind: str, anchor_date: date | None) -> LeaderboardPeriod:
        if kind == "all":
            return LeaderboardPeriod(kind, None, None)
        anchor = anchor_date or datetime.now(KYIV_TZ).date()
        if kind == "week":
            start = anchor - timedelta(days=anchor.weekday())
            end = start + timedelta(days=7)
        else:
            start = anchor.replace(day=1)
            end = start + timedelta(days=monthrange(start.year, start.month)[1])
        start_at, end_at = kyiv_date_range_to_utc(start, end)
        return LeaderboardPeriod(kind, start_at, end_at)

    @classmethod
    def rows(cls, *, period: LeaderboardPeriod):
        tx_filter = Q(point_transactions__isnull=False)
        if period.start_at is not None:
            tx_filter &= Q(
                point_transactions__awarded_at__gte=period.start_at,
                point_transactions__awarded_at__lt=period.end_at,
            )
        return list(
            User.objects.filter(
                is_active=True,
                leaderboard_opt_in=True,
                public_alias__isnull=False,
            )
            .exclude(public_alias__exact="")
            .annotate(
                points=Coalesce(Sum("point_transactions__points", filter=tx_filter), 0),
                completion_count=Count(
                    "point_transactions__completed_session_id",
                    filter=tx_filter
                    & Q(point_transactions__point_kind=PointKind.WORKOUT_COMPLETION),
                    distinct=True,
                ),
                reached_at=Max("point_transactions__awarded_at", filter=tx_filter),
            )
            .values("id", "public_alias", "points", "completion_count", "reached_at")
            .order_by("-points", "-completion_count", "reached_at", "id")
        )

    @staticmethod
    def own_points(*, user, period: LeaderboardPeriod) -> int:
        queryset = PointTransaction.objects.filter(user=user)
        if period.start_at is not None:
            queryset = queryset.filter(
                awarded_at__gte=period.start_at, awarded_at__lt=period.end_at
            )
        return queryset.aggregate(total=Coalesce(Sum("points"), 0))["total"]
