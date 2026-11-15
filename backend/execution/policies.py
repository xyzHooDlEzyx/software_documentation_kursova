from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

from config.timezones import KYIV_TZ

from .errors import ExecutionDomainError


@dataclass(frozen=True)
class CalorieSegment:
    duration_min: Decimal
    met_value: Decimal | None


@dataclass(frozen=True)
class CalorieEstimate:
    value: Decimal | None
    reason: str | None


class CaloriesEstimator:
    MISSING_MET = "missing_met"
    UNSUPPORTED_AGE = "unsupported_age_for_reference"

    @staticmethod
    def age_on(birth_date: date, on_date: date) -> int:
        return (
            on_date.year
            - birth_date.year
            - ((on_date.month, on_date.day) < (birth_date.month, birth_date.day))
        )

    @classmethod
    def estimate(
        cls,
        *,
        weight_kg: Decimal | None,
        birth_date: date,
        completed_at: datetime,
        duration_min: Decimal,
        segments: tuple[CalorieSegment, ...] | list[CalorieSegment],
        workout_met_value: Decimal | None = None,
    ) -> CalorieEstimate:
        if weight_kg is None:
            raise ExecutionDomainError("A historical weight entry is required.")
        local_date = completed_at.astimezone(KYIV_TZ).date()
        if cls.age_on(birth_date, local_date) >= 60:
            return CalorieEstimate(None, cls.UNSUPPORTED_AGE)

        covered = Decimal("0")
        total = Decimal("0")
        for segment in segments:
            if segment.duration_min <= 0:
                raise ExecutionDomainError("Segment duration must be positive.")
            covered += segment.duration_min
            if segment.met_value is None:
                return CalorieEstimate(None, cls.MISSING_MET)
            total += (
                segment.met_value * weight_kg * segment.duration_min / Decimal("60")
            )
        if covered > duration_min:
            raise ExecutionDomainError("Segment duration exceeds session duration.")
        remainder = duration_min - covered
        if remainder:
            if workout_met_value is None:
                return CalorieEstimate(None, cls.MISSING_MET)
            total += workout_met_value * weight_kg * remainder / Decimal("60")
        return CalorieEstimate(
            total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), None
        )


def validate_duration(duration_min: Decimal | int) -> Decimal:
    value = Decimal(duration_min)
    if value <= 0 or value > 300:
        raise ExecutionDomainError("Duration must be greater than 0 and at most 300.")
    return value


class PointsPolicy:
    PROGRAM_COMPLETION_BONUS = 50

    @classmethod
    def workout_points(
        cls,
        *,
        duration_min: Decimal | int,
        completed_at: datetime,
        planned_at: datetime | None = None,
    ) -> int:
        duration = validate_duration(duration_min)
        capped = min(duration, Decimal("120"))
        blocks = int((capped / Decimal("10")).to_integral_value(rounding=ROUND_FLOOR))
        planned_bonus = (
            int(
                planned_at is not None
                and completed_at.astimezone(KYIV_TZ).date()
                == planned_at.astimezone(KYIV_TZ).date()
            )
            * 5
        )
        return 10 + 2 * blocks + planned_bonus
