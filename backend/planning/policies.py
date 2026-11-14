"""Pure planning policies shared by services and read projections."""

from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

REMINDER_LEAD_TIME = timedelta(hours=1)


def session_is_missed(*, status: str, scheduled_at: datetime, now: datetime) -> bool:
    """BR-008: missed is derived; it is never a persisted session status."""
    return status == "planned" and scheduled_at < now


def should_record_reschedule(
    *, current_scheduled_at: datetime, requested_scheduled_at: datetime
) -> bool:
    """BR-008 REST policy: an identical reschedule is an idempotent no-op."""
    return current_scheduled_at != requested_scheduled_at


def reminder_visible_at(scheduled_at: datetime) -> datetime:
    """BR-026: short-lead sessions retain scheduled_at - one hour."""
    return scheduled_at - REMINDER_LEAD_TIME


def can_schedule(*, scheduled_at: datetime, now: datetime) -> bool:
    """BR-026: a slot must be future-facing, even when its reminder is visible."""
    return scheduled_at > now


def normalize_scheduled_at(value: datetime) -> datetime:
    """Use the API's whole-second precision as the scheduling domain boundary."""
    return value.replace(microsecond=0)


def format_utc_seconds(value: datetime) -> str:
    """Render a timestamp in the canonical REST representation."""
    return value.astimezone(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
