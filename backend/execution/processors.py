from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, final

from rest_framework.exceptions import ValidationError

from catalog.models import Exercise, ExerciseCategory


@dataclass(frozen=True)
class ValidatedExerciseResult:
    exercise: Exercise
    position: int
    actual_sets: int | None
    actual_reps: int | None
    actual_load_kg: Decimal | None
    actual_duration_min: Decimal | None
    actual_distance_km: Decimal | None


class ExerciseResultProcessor(ABC):
    category: str

    @final
    def process(
        self,
        result: dict[str, Any],
        *,
        allowed_composition: dict[int, tuple[int, Exercise]],
    ) -> ValidatedExerciseResult:
        position = result.get("position")
        allowed = allowed_composition.get(position)
        exercise_id = result.get("exercise_id")
        if allowed is None or allowed[0] != exercise_id:
            raise ValidationError(
                "Вправа не належить до актуального складу тренування."
            )
        exercise = allowed[1]
        if exercise.category != self.category:
            raise ValidationError("Категорія вправи не відповідає обробнику.")

        values = {
            name: result.get(name)
            for name in (
                "actual_sets",
                "actual_reps",
                "actual_load_kg",
                "actual_duration_min",
                "actual_distance_km",
            )
        }
        for name in ("actual_sets", "actual_reps"):
            value = values[name]
            if value is not None and (
                isinstance(value, bool) or int(value) != value or value <= 0
            ):
                raise ValidationError(
                    {name: ["Значення має бути додатним цілим числом."]}
                )
        for name in ("actual_load_kg", "actual_duration_min", "actual_distance_km"):
            value = values[name]
            if value is not None and value < 0:
                raise ValidationError({name: ["Значення не може бути від'ємним."]})
        if values["actual_duration_min"] == 0 or values["actual_distance_km"] == 0:
            raise ValidationError(
                "Тривалість і дистанція, якщо задані, мають бути додатними."
            )

        self.validate_category(exercise, values)
        return ValidatedExerciseResult(
            exercise=exercise,
            position=int(position),
            actual_sets=int(values["actual_sets"])
            if values["actual_sets"] is not None
            else None,
            actual_reps=int(values["actual_reps"])
            if values["actual_reps"] is not None
            else None,
            actual_load_kg=self._decimal(values["actual_load_kg"], "0.1"),
            actual_duration_min=self._decimal(values["actual_duration_min"], "0.01"),
            actual_distance_km=self._decimal(values["actual_distance_km"], "0.001"),
        )

    @staticmethod
    def _decimal(value: Decimal | None, quantum: str) -> Decimal | None:
        return value.quantize(Decimal(quantum)) if value is not None else None

    @abstractmethod
    def validate_category(self, exercise: Exercise, values: dict[str, Any]) -> None:
        raise NotImplementedError


class StrengthResultProcessor(ExerciseResultProcessor):
    category = ExerciseCategory.STRENGTH

    def validate_category(self, exercise: Exercise, values: dict[str, Any]) -> None:
        if values["actual_sets"] is None or values["actual_reps"] is None:
            raise ValidationError("Для силової вправи потрібні підходи й повторення.")
        if values["actual_distance_km"] is not None:
            raise ValidationError(
                {
                    "actual_distance_km": [
                        "Дистанція не застосовується до силової вправи."
                    ]
                }
            )


class CardioResultProcessor(ExerciseResultProcessor):
    category = ExerciseCategory.CARDIO

    def validate_category(self, exercise: Exercise, values: dict[str, Any]) -> None:
        if any(
            values[name] is not None
            for name in ("actual_sets", "actual_reps", "actual_load_kg")
        ):
            raise ValidationError(
                "Підходи, повторення й навантаження не застосовуються до кардіо."
            )
        if exercise.tracks_distance:
            if (
                values["actual_duration_min"] is None
                and values["actual_distance_km"] is None
            ):
                raise ValidationError("Для кардіо потрібна тривалість або дистанція.")
        else:
            if values["actual_distance_km"] is not None:
                raise ValidationError(
                    {"actual_distance_km": ["Ця вправа не відстежує дистанцію."]}
                )
            if values["actual_duration_min"] is None:
                raise ValidationError(
                    {"actual_duration_min": ["Для цієї вправи потрібна тривалість."]}
                )


class YogaResultProcessor(ExerciseResultProcessor):
    category = ExerciseCategory.YOGA

    def validate_category(self, exercise: Exercise, values: dict[str, Any]) -> None:
        if values["actual_duration_min"] is None:
            raise ValidationError(
                {"actual_duration_min": ["Для йоги потрібна тривалість."]}
            )
        if any(
            values[name] is not None
            for name in (
                "actual_sets",
                "actual_reps",
                "actual_load_kg",
                "actual_distance_km",
            )
        ):
            raise ValidationError("Для йоги дозволена лише фактична тривалість.")


PROCESSORS = {
    ExerciseCategory.STRENGTH: StrengthResultProcessor(),
    ExerciseCategory.CARDIO: CardioResultProcessor(),
    ExerciseCategory.YOGA: YogaResultProcessor(),
}
