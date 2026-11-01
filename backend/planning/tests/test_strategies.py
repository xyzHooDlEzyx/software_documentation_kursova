"""Tests for the goal-specific GoF Strategy used by program recommendation."""

from io import StringIO
from types import SimpleNamespace

import pytest
from django.core.management import call_command

from catalog.models import ExerciseCategory, ProgramTemplate, ProgramTemplateStatus
from planning.models import UserProgram
from planning.strategies import (
    MaintenanceSelectionStrategy,
    MuscleGainSelectionStrategy,
    WeightLossSelectionStrategy,
    get_selection_strategy,
)


def _counts(cardio: int, strength: int, yoga: int) -> dict[str, int]:
    return {
        ExerciseCategory.CARDIO: cardio,
        ExerciseCategory.STRENGTH: strength,
        ExerciseCategory.YOGA: yoga,
    }


@pytest.fixture
def seeded_catalog(db):
    call_command("seed_catalog", stdout=StringIO())


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("goal", "strategy_type", "preferred_name", "other_name"),
    [
        (
            "weight_loss",
            WeightLossSelectionStrategy,
            "Кардіо фокус для схуднення (Початківець)",
            "Базовий мікс для схуднення (Початківець)",
        ),
        (
            "muscle_gain",
            MuscleGainSelectionStrategy,
            "Інтенсивний набір м'язової маси (Початківець)",
            "Гібридний ріст м'язів (Початківець)",
        ),
        (
            "maintenance",
            MaintenanceSelectionStrategy,
            "Гармонійний баланс (Початківець)",
            "Силовий баланс форми (Початківець)",
        ),
    ],
)
def test_seeded_pairs_have_distinct_scores_and_correct_winner(
    seeded_catalog, goal, strategy_type, preferred_name, other_name
):
    candidates = list(
        ProgramTemplate.objects.filter(
            fitness_goal=goal,
            experience_level="beginner",
            workouts_per_week=3,
            status=ProgramTemplateStatus.PUBLISHED,
        ).prefetch_related(
            "program_template_workouts__workout__workout_exercises__exercise"
        )
    )
    assert {template.name for template in candidates} == {
        preferred_name,
        other_name,
    }

    strategy = get_selection_strategy(goal)
    assert isinstance(strategy, strategy_type)
    preferred = next(t for t in candidates if t.name == preferred_name)
    other = next(t for t in candidates if t.name == other_name)
    if goal == "maintenance":
        assert strategy.score_template(preferred) < strategy.score_template(other)
    else:
        assert strategy.score_template(preferred) > strategy.score_template(other)
    assert min(candidates, key=lambda t: strategy.sort_key(t, 3)) == preferred
    assert strategy.rank(candidates, 3)[0] == preferred
    assert UserProgram.objects.count() == 0  # Ranking itself is read-only.


@pytest.mark.django_db
def test_scoring_reuses_prefetched_composition(
    seeded_catalog, django_assert_num_queries
):
    candidates = list(
        ProgramTemplate.objects.filter(
            fitness_goal="weight_loss",
            status=ProgramTemplateStatus.PUBLISHED,
        ).prefetch_related(
            "program_template_workouts__workout__workout_exercises__exercise"
        )
    )
    with django_assert_num_queries(0):
        for candidate in candidates:
            WeightLossSelectionStrategy().sort_key(candidate, 3)


@pytest.mark.parametrize(
    ("goal", "inferior", "preferred"),
    [
        ("weight_loss", _counts(1, 2, 0), _counts(3, 0, 0)),
        ("muscle_gain", _counts(2, 1, 0), _counts(0, 3, 0)),
        ("maintenance", _counts(3, 0, 0), _counts(1, 1, 1)),
    ],
)
def test_composition_breaks_tie_before_smaller_id(
    monkeypatch, goal, inferior, preferred
):
    # The worse candidate deliberately has the smaller ID. This proves the
    # concrete strategy runs before the final deterministic ID tie-break.
    low_id = SimpleNamespace(id=1, workouts_per_week=3)
    high_id = SimpleNamespace(id=2, workouts_per_week=3)
    counts = {1: inferior, 2: preferred}
    monkeypatch.setattr(
        "planning.strategies.get_template_exercise_category_counts",
        lambda template: counts[template.id],
    )
    strategy = get_selection_strategy(goal)
    assert min((low_id, high_id), key=lambda t: strategy.sort_key(t, 3)) == high_id
    assert strategy.rank((low_id, high_id), 3)[0] == high_id


@pytest.mark.parametrize(
    ("goal", "inferior", "preferred"),
    [
        ("weight_loss", _counts(0, 3, 0), _counts(3, 0, 0)),
        ("muscle_gain", _counts(3, 0, 0), _counts(0, 3, 0)),
        ("maintenance", _counts(3, 0, 0), _counts(1, 1, 1)),
    ],
)
def test_frequency_distance_precedes_composition(
    monkeypatch, goal, inferior, preferred
):
    exact = SimpleNamespace(id=1, workouts_per_week=3)
    distant = SimpleNamespace(id=2, workouts_per_week=5)
    counts = {1: inferior, 2: preferred}
    monkeypatch.setattr(
        "planning.strategies.get_template_exercise_category_counts",
        lambda template: counts[template.id],
    )
    strategy = get_selection_strategy(goal)
    assert min((exact, distant), key=lambda t: strategy.sort_key(t, 3)) == exact


@pytest.mark.parametrize(
    ("goal", "inferior", "preferred"),
    [
        ("weight_loss", _counts(0, 3, 0), _counts(3, 0, 0)),
        ("muscle_gain", _counts(3, 0, 0), _counts(0, 3, 0)),
        ("maintenance", _counts(3, 0, 0), _counts(1, 1, 1)),
    ],
)
def test_lower_frequency_precedes_composition_when_distance_ties(
    monkeypatch, goal, inferior, preferred
):
    lower = SimpleNamespace(id=1, workouts_per_week=2)
    higher = SimpleNamespace(id=2, workouts_per_week=4)
    counts = {1: inferior, 2: preferred}
    monkeypatch.setattr(
        "planning.strategies.get_template_exercise_category_counts",
        lambda template: counts[template.id],
    )
    strategy = get_selection_strategy(goal)
    assert min((lower, higher), key=lambda t: strategy.sort_key(t, 3)) == lower


@pytest.mark.parametrize("goal", ["weight_loss", "muscle_gain", "maintenance"])
def test_smaller_id_is_final_tie_break(monkeypatch, goal):
    lower_id = SimpleNamespace(id=1, workouts_per_week=3)
    higher_id = SimpleNamespace(id=2, workouts_per_week=3)
    monkeypatch.setattr(
        "planning.strategies.get_template_exercise_category_counts",
        lambda template: _counts(1, 1, 1),
    )
    strategy = get_selection_strategy(goal)
    assert min((higher_id, lower_id), key=lambda t: strategy.sort_key(t, 3)) == lower_id


def test_unknown_goal_has_no_strategy():
    with pytest.raises(ValueError, match="No selection strategy"):
        get_selection_strategy("unsupported")
