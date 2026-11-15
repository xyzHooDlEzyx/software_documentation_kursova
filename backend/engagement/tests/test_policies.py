from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal

import pytest

from engagement.models import AchievementCode
from engagement.policies import (
    AchievementEvaluator,
    AchievementFacts,
    ChallengeFact,
    ChallengeProgressEvaluator,
)


@pytest.mark.parametrize(
    ("facts", "expected"),
    [
        (
            AchievementFacts(1, Decimal("1"), Decimal("0"), None),
            {AchievementCode.FIRST_WORKOUT},
        ),
        (
            AchievementFacts(5, Decimal("1"), Decimal("0"), None),
            {AchievementCode.FIRST_WORKOUT, AchievementCode.FIVE_WORKOUTS},
        ),
        (
            AchievementFacts(1, Decimal("99"), Decimal("0"), None),
            {AchievementCode.FIRST_WORKOUT},
        ),
        (
            AchievementFacts(1, Decimal("100"), Decimal("0"), None),
            {
                AchievementCode.FIRST_WORKOUT,
                AchievementCode.ONE_HUNDRED_MINUTES,
            },
        ),
        (
            AchievementFacts(1, Decimal("1"), Decimal("42.1"), None),
            {AchievementCode.FIRST_WORKOUT},
        ),
        (
            AchievementFacts(1, Decimal("1"), Decimal("42.2"), None),
            {AchievementCode.FIRST_WORKOUT, AchievementCode.MARATHONER},
        ),
        (
            AchievementFacts(1, Decimal("1"), Decimal("0"), Decimal("99.99")),
            {AchievementCode.FIRST_WORKOUT},
        ),
        (
            AchievementFacts(1, Decimal("1"), Decimal("0"), Decimal("100")),
            {AchievementCode.FIRST_WORKOUT, AchievementCode.HEAVYWEIGHT},
        ),
    ],
)
def test_achievement_boundaries(facts, expected):
    assert AchievementEvaluator.evaluate(facts) == expected


def test_achievement_skips_already_earned():
    facts = AchievementFacts(5, Decimal("100"), Decimal("42.2"), Decimal("100"))
    assert AchievementCode.FIRST_WORKOUT not in AchievementEvaluator.evaluate(
        facts, {AchievementCode.FIRST_WORKOUT}
    )


def test_challenge_counts_only_after_join_and_inside_period():
    start = datetime(2026, 11, 1, tzinfo=dt_timezone.utc)
    joined = start + timedelta(days=2)
    end = start + timedelta(days=10)
    facts = [
        ChallengeFact(start + timedelta(days=1), Decimal("50")),
        ChallengeFact(joined + timedelta(seconds=1), Decimal("20")),
        ChallengeFact(end - timedelta(seconds=1), Decimal("30")),
        ChallengeFact(end, Decimal("100")),
    ]
    workouts = ChallengeProgressEvaluator.evaluate(
        goal_kind="workouts",
        goal_value=2,
        joined_at=joined,
        start_at=start,
        end_at=end,
        facts=facts,
        now=end - timedelta(days=1),
    )
    minutes = ChallengeProgressEvaluator.evaluate(
        goal_kind="minutes",
        goal_value=50,
        joined_at=joined,
        start_at=start,
        end_at=end,
        facts=facts,
        now=end - timedelta(days=1),
    )
    assert workouts.progress_value == 2 and workouts.completed
    assert minutes.progress_value == 50 and minutes.completed


def test_challenge_expires_only_after_end_when_incomplete():
    start = datetime(2026, 11, 1, tzinfo=dt_timezone.utc)
    end = start + timedelta(days=1)
    result = ChallengeProgressEvaluator.evaluate(
        goal_kind="workouts",
        goal_value=2,
        joined_at=start,
        start_at=start,
        end_at=end,
        facts=(),
        now=end,
    )
    assert result.expired and not result.completed
