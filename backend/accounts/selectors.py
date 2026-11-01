from datetime import date, datetime, time
from datetime import timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.db.models import QuerySet

from .models import User, WeightEntry

KYIV_TZ = ZoneInfo("Europe/Kyiv")


def kyiv_date_range_to_utc(
    start_date: date, end_date: date
) -> tuple[datetime, datetime]:
    start_local = datetime.combine(start_date, time.min, tzinfo=KYIV_TZ)
    end_local = datetime.combine(end_date, time.min, tzinfo=KYIV_TZ)
    return start_local.astimezone(dt_timezone.utc), end_local.astimezone(
        dt_timezone.utc
    )


def list_user_weight_entries(
    *,
    user: User,
    start_date: date | None = None,
    end_date: date | None = None,
) -> QuerySet[WeightEntry]:
    queryset = WeightEntry.objects.filter(user=user)
    if start_date is not None and end_date is not None:
        start_utc, end_utc = kyiv_date_range_to_utc(start_date, end_date)
        queryset = queryset.filter(measured_at__gte=start_utc, measured_at__lt=end_utc)
    return queryset.order_by("-measured_at", "-id")
