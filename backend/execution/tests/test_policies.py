from datetime import date, datetime
from datetime import timezone as dt_timezone
from decimal import Decimal

import pytest

from execution.errors import ExecutionDomainError
from execution.policies import (
    CalorieEstimate,
    CalorieSegment,
    CaloriesEstimator,
    PointsPolicy,
    validate_duration,
)


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=dt_timezone.utc)


def test_calories_decimal_half_up():
    value = CaloriesEstimator.estimate(
        weight_kg=Decimal("70.0"),
        birth_date=date(1990, 1, 1),
        completed_at=utc("2026-11-14T10:00:00"),
        duration_min=Decimal("31"),
        segments=(CalorieSegment(Decimal("30"), Decimal("5.00")),),
        workout_met_value=Decimal("3.00"),
    )
    assert value == CalorieEstimate(Decimal("178.50"), None)


def test_calories_missing_met():
    assert CaloriesEstimator.estimate(
        weight_kg=Decimal("70.0"),
        birth_date=date(1990, 1, 1),
        completed_at=utc("2026-11-14T10:00:00"),
        duration_min=Decimal("30"),
        segments=(),
    ) == CalorieEstimate(None, "missing_met")


@pytest.mark.parametrize(
    ("birth_date", "reason"),
    [
        (date(1967, 11, 15), None),
        (date(1966, 11, 15), "unsupported_age_for_reference"),
    ],
)
def test_calories_kyiv_age_boundary(birth_date, reason):
    result = CaloriesEstimator.estimate(
        weight_kg=Decimal("70"),
        birth_date=birth_date,
        completed_at=utc("2026-11-14T22:30:00"),
        duration_min=Decimal("60"),
        segments=(CalorieSegment(Decimal("60"), Decimal("1")),),
    )
    if reason is None:
        assert result == CalorieEstimate(Decimal("70.00"), None)
    else:
        assert result == CalorieEstimate(None, reason)


def test_calories_missing_weight_is_domain_error():
    with pytest.raises(ExecutionDomainError):
        CaloriesEstimator.estimate(
            weight_kg=None,
            birth_date=date(1990, 1, 1),
            completed_at=utc("2026-11-14T10:00:00"),
            duration_min=Decimal("30"),
            segments=(),
        )


@pytest.mark.parametrize(
    ("duration", "expected"),
    [(1, 10), (9, 10), (10, 12), (120, 34), (121, 34), (300, 34)],
)
def test_points_duration_boundaries(duration, expected):
    assert (
        PointsPolicy.workout_points(
            duration_min=duration, completed_at=utc("2026-11-14T10:00:00")
        )
        == expected
    )


def test_points_planned_day_uses_kyiv_date_across_utc_midnight():
    assert (
        PointsPolicy.workout_points(
            duration_min=10,
            planned_at=utc("2026-11-14T23:30:00"),
            completed_at=utc("2026-11-15T20:30:00"),
        )
        == 17
    )
    assert (
        PointsPolicy.workout_points(
            duration_min=10,
            planned_at=utc("2026-11-14T20:30:00"),
            completed_at=utc("2026-11-14T23:30:00"),
        )
        == 12
    )


@pytest.mark.parametrize("duration", [0, 301])
def test_duration_rejects_out_of_range(duration):
    with pytest.raises(ExecutionDomainError):
        validate_duration(duration)
