"""GoF Strategy pattern for program template recommendation (BR-005, FR-011).

Defines:
- SelectionStrategy (Abstract Base Strategy)
- WeightLossSelectionStrategy (prioritizes maximum cardio share)
- MuscleGainSelectionStrategy (prioritizes maximum strength share)
- MaintenanceSelectionStrategy (prioritizes minimum spread between categories)
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Sequence

from accounts.models import FitnessGoal
from catalog.models import ExerciseCategory, ProgramTemplate


def get_template_exercise_category_counts(
    template: ProgramTemplate,
) -> dict[str, int]:
    """Calculate the count of exercise occurrences by category in a template."""
    counts = {
        ExerciseCategory.CARDIO: 0,
        ExerciseCategory.STRENGTH: 0,
        ExerciseCategory.YOGA: 0,
    }
    # Preserve the relation caches populated by ProgramSelectionService. Calling
    # select_related() here would create fresh querysets for every candidate.
    for ptw in template.program_template_workouts.all():
        for we in ptw.workout.workout_exercises.all():
            cat = we.exercise.category
            if cat in counts:
                counts[cat] += 1
    return counts


class SelectionStrategy(ABC):
    """Abstract GoF Strategy for ranking candidate program templates."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the concrete strategy."""

    @property
    @abstractmethod
    def composition_criterion(self) -> str:
        """Human-readable description of the composition ranking rule."""

    @abstractmethod
    def score_template(self, template: ProgramTemplate) -> Decimal:
        """Calculate domain-specific score used for ranking."""

    @abstractmethod
    def sort_key(
        self, template: ProgramTemplate, target_frequency: int
    ) -> tuple[Any, ...]:
        """Return tuple for ascending sorting (min is winner)."""

    def rank(
        self,
        candidates: Sequence[ProgramTemplate],
        target_frequency: int,
    ) -> list[ProgramTemplate]:
        """Order eligible candidates using the concrete composition criterion."""
        return sorted(candidates, key=lambda t: self.sort_key(t, target_frequency))


class WeightLossSelectionStrategy(SelectionStrategy):
    """Strategy for Weight Loss goal: maximizes the share of cardio exercises."""

    @property
    def name(self) -> str:
        return "WeightLossSelectionStrategy"

    @property
    def composition_criterion(self) -> str:
        return "Максимальна частка вправ cardio"

    def score_template(self, template: ProgramTemplate) -> Decimal:
        counts = get_template_exercise_category_counts(template)
        total = sum(counts.values())
        if total == 0:
            return Decimal("0.0")
        return Decimal(counts[ExerciseCategory.CARDIO]) / Decimal(total)

    def sort_key(
        self, template: ProgramTemplate, target_frequency: int
    ) -> tuple[int, int, Decimal, int]:
        freq_diff = abs(template.workouts_per_week - target_frequency)
        cardio_ratio = self.score_template(template)
        # Frequency first, then highest cardio share, then smallest ID.
        return (freq_diff, template.workouts_per_week, -cardio_ratio, template.id)


class MuscleGainSelectionStrategy(SelectionStrategy):
    """Strategy for Muscle Gain goal: maximizes the share of strength exercises."""

    @property
    def name(self) -> str:
        return "MuscleGainSelectionStrategy"

    @property
    def composition_criterion(self) -> str:
        return "Максимальна частка вправ strength"

    def score_template(self, template: ProgramTemplate) -> Decimal:
        counts = get_template_exercise_category_counts(template)
        total = sum(counts.values())
        if total == 0:
            return Decimal("0.0")
        return Decimal(counts[ExerciseCategory.STRENGTH]) / Decimal(total)

    def sort_key(
        self, template: ProgramTemplate, target_frequency: int
    ) -> tuple[int, int, Decimal, int]:
        freq_diff = abs(template.workouts_per_week - target_frequency)
        strength_ratio = self.score_template(template)
        # Frequency first, then highest strength share, then smallest ID.
        return (
            freq_diff,
            template.workouts_per_week,
            -strength_ratio,
            template.id,
        )


class MaintenanceSelectionStrategy(SelectionStrategy):
    """Strategy for Maintenance goal: minimizes the spread between category shares."""

    @property
    def name(self) -> str:
        return "MaintenanceSelectionStrategy"

    @property
    def composition_criterion(self) -> str:
        return "Найменший розмах часток cardio/strength/yoga"

    def score_template(self, template: ProgramTemplate) -> Decimal:
        counts = get_template_exercise_category_counts(template)
        total = sum(counts.values())
        if total == 0:
            return Decimal("0.0")
        ratios = [
            Decimal(counts[cat]) / Decimal(total)
            for cat in (
                ExerciseCategory.CARDIO,
                ExerciseCategory.STRENGTH,
                ExerciseCategory.YOGA,
            )
        ]
        return max(ratios) - min(ratios)

    def sort_key(
        self, template: ProgramTemplate, target_frequency: int
    ) -> tuple[int, int, Decimal, int]:
        freq_diff = abs(template.workouts_per_week - target_frequency)
        spread = self.score_template(template)
        # Frequency first, then smallest category spread, then smallest ID.
        return (freq_diff, template.workouts_per_week, spread, template.id)


STRATEGY_REGISTRY: dict[str, SelectionStrategy] = {
    FitnessGoal.WEIGHT_LOSS: WeightLossSelectionStrategy(),
    FitnessGoal.MUSCLE_GAIN: MuscleGainSelectionStrategy(),
    FitnessGoal.MAINTENANCE: MaintenanceSelectionStrategy(),
}


def get_selection_strategy(fitness_goal: str) -> SelectionStrategy:
    """Factory retrieving the concrete SelectionStrategy for a given fitness goal."""
    strategy = STRATEGY_REGISTRY.get(fitness_goal)
    if not strategy:
        raise ValueError(f"No selection strategy registered for goal '{fitness_goal}'")
    return strategy
