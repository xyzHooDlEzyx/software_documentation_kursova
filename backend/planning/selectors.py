"""Read-only projections for program progress, sessions, and reminders."""

from decimal import Decimal
from typing import Any

from django.db.models import Count, Q, QuerySet
from django.utils import timezone
from rest_framework.exceptions import NotFound

from accounts.selectors import kyiv_date_range_to_utc

from .models import (
    Notification,
    NotificationStatus,
    ScheduledSession,
    ScheduledSessionStatus,
    UserProgram,
)


def with_program_progress(queryset: QuerySet[UserProgram]) -> QuerySet[UserProgram]:
    return queryset.annotate(
        total_planned_count=Count(
            "scheduled_sessions",
            filter=~Q(scheduled_sessions__status=ScheduledSessionStatus.CANCELLED),
            distinct=True,
        ),
        completed_planned_count=Count(
            "scheduled_sessions",
            filter=Q(scheduled_sessions__status=ScheduledSessionStatus.COMPLETED),
            distinct=True,
        ),
    )


def program_progress(program: UserProgram) -> dict[str, Any]:
    total = getattr(program, "total_planned_count", None)
    completed = getattr(program, "completed_planned_count", None)
    if total is None or completed is None:
        counts = program.scheduled_sessions.aggregate(
            total=Count("id", filter=~Q(status=ScheduledSessionStatus.CANCELLED)),
            completed=Count("id", filter=Q(status=ScheduledSessionStatus.COMPLETED)),
        )
        total = counts["total"]
        completed = counts["completed"]
    percent = Decimal("0.0")
    if total:
        percent = (Decimal(completed) * Decimal("100.0") / Decimal(total)).quantize(
            Decimal("0.1")
        )
    return {
        "total_planned": total,
        "completed_planned": completed,
        "percent": str(percent),
    }


def owner_sessions(user: Any) -> QuerySet[ScheduledSession]:
    return ScheduledSession.objects.filter(user=user).select_related(
        "user_program", "user_program_workout", "source_workout"
    )


def owner_program_exists(user: Any, program_id: int) -> bool:
    return UserProgram.objects.filter(user=user, pk=program_id).exists()


def filter_sessions_in_local_period(
    queryset: QuerySet[ScheduledSession], *, start_date, end_date
) -> QuerySet[ScheduledSession]:
    start_utc, end_utc = kyiv_date_range_to_utc(start_date, end_date)
    return queryset.filter(scheduled_at__gte=start_utc, scheduled_at__lt=end_utc)


def visible_notifications(user: Any) -> QuerySet[Notification]:
    return Notification.objects.filter(
        user=user,
        visible_at__lte=timezone.now(),
        status__in=[NotificationStatus.PENDING, NotificationStatus.READ],
    ).select_related("scheduled_session")


def filter_notifications_by_current(
    queryset: QuerySet[Notification], *, is_current: bool
) -> QuerySet[Notification]:
    current = Q(scheduled_session__status=ScheduledSessionStatus.PLANNED)
    return queryset.filter(current) if is_current else queryset.exclude(current)


def get_visible_notification(user: Any, notification_id: int) -> Notification:
    notification = visible_notifications(user).filter(pk=notification_id).first()
    if not notification:
        raise NotFound()
    return notification
