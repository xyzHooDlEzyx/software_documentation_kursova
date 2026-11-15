from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError

from catalog.models import Exercise, ExerciseCategory
from execution.processors import (
    CardioResultProcessor,
    StrengthResultProcessor,
    YogaResultProcessor,
)


def result(**overrides):
    value = {
        "position": 1,
        "exercise_id": 7,
        "actual_sets": None,
        "actual_reps": None,
        "actual_load_kg": None,
        "actual_duration_min": None,
        "actual_distance_km": None,
    }
    value.update(overrides)
    return value


def exercise(category, *, tracks_distance=False):
    return Exercise(
        id=7,
        name="Test",
        category=category,
        tracks_distance=tracks_distance,
    )


def test_strength_template_validates_membership_then_normalizes():
    item = exercise(ExerciseCategory.STRENGTH)
    processed = StrengthResultProcessor().process(
        result(
            actual_sets=3,
            actual_reps=8,
            actual_load_kg=Decimal("20.0"),
            actual_duration_min=Decimal("10.00"),
        ),
        allowed_composition={1: (7, item)},
    )
    assert processed.actual_sets == 3
    assert processed.actual_load_kg == Decimal("20.0")

    with pytest.raises(ValidationError, match="актуального складу"):
        StrengthResultProcessor().process(
            result(exercise_id=8, actual_sets=3, actual_reps=8),
            allowed_composition={1: (7, item)},
        )


@pytest.mark.parametrize("tracks_distance", [False, True])
def test_cardio_distance_requires_tracks_distance(tracks_distance):
    item = exercise(ExerciseCategory.CARDIO, tracks_distance=tracks_distance)
    payload = result(actual_distance_km=Decimal("2.500"))
    if tracks_distance:
        assert CardioResultProcessor().process(
            payload, allowed_composition={1: (7, item)}
        ).actual_distance_km == Decimal("2.500")
    else:
        with pytest.raises(ValidationError):
            CardioResultProcessor().process(payload, allowed_composition={1: (7, item)})


def test_yoga_hook_requires_duration_and_rejects_strength_fields():
    item = exercise(ExerciseCategory.YOGA)
    assert YogaResultProcessor().process(
        result(actual_duration_min=Decimal("15.00")),
        allowed_composition={1: (7, item)},
    )
    with pytest.raises(ValidationError):
        YogaResultProcessor().process(
            result(actual_duration_min=Decimal("15.00"), actual_sets=1),
            allowed_composition={1: (7, item)},
        )
