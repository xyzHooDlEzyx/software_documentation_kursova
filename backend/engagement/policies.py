from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable

from .models import AchievementCode


@dataclass(frozen=True)
class AchievementFacts:
    session_count: int
    total_duration_min: Decimal
    cardio_distance_km: Decimal
    maximum_strength_load_kg: Decimal | None


class AchievementEvaluator:
    @staticmethod
    def evaluate(
        facts: AchievementFacts, already_earned: Iterable[str] = ()
    ) -> set[AchievementCode]:
        earned = {AchievementCode(code) for code in already_earned}
        candidates: set[AchievementCode] = set()
        if facts.session_count >= 1:
            candidates.add(AchievementCode.FIRST_WORKOUT)
        if facts.session_count >= 5:
            candidates.add(AchievementCode.FIVE_WORKOUTS)
        if facts.total_duration_min >= Decimal("100"):
            candidates.add(AchievementCode.ONE_HUNDRED_MINUTES)
        if facts.cardio_distance_km >= Decimal("42.2"):
            candidates.add(AchievementCode.MARATHONER)
        if (
            facts.maximum_strength_load_kg is not None
            and facts.maximum_strength_load_kg >= Decimal("100")
        ):
            candidates.add(AchievementCode.HEAVYWEIGHT)
        return candidates - earned


@dataclass(frozen=True)
class ChallengeFact:
    completed_at: datetime
    duration_min: Decimal


@dataclass(frozen=True)
class ChallengeProgress:
    progress_value: Decimal
    completed: bool
    expired: bool


class ChallengeProgressEvaluator:
    @staticmethod
    def evaluate(
        *,
        goal_kind: str,
        goal_value: int,
        joined_at: datetime,
        start_at: datetime,
        end_at: datetime,
        facts: Iterable[ChallengeFact],
        now: datetime,
        already_completed: bool = False,
    ) -> ChallengeProgress:
        eligible = [
            fact
            for fact in facts
            if fact.completed_at > joined_at
            and fact.completed_at >= start_at
            and fact.completed_at < end_at
        ]
        if goal_kind == "workouts":
            value = Decimal(len(eligible))
        elif goal_kind == "minutes":
            value = sum((fact.duration_min for fact in eligible), Decimal("0"))
        else:
            raise ValueError("Unsupported challenge goal kind.")
        completed = already_completed or value >= Decimal(goal_value)
        return ChallengeProgress(
            progress_value=value,
            completed=completed,
            expired=not completed and now >= end_at,
        )
