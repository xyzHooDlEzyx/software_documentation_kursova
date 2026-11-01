"""Domain publication and validation services for the shared fitness catalog.

Enforces business rules BR-002, BR-003, BR-004, and BR-005.
"""

import re
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import ExperienceLevel, FitnessGoal

from .models import (
    Exercise,
    ExerciseCategory,
    ProgramTemplate,
    ProgramTemplateStatus,
    ProgramTemplateWorkout,
    Workout,
    WorkoutExercise,
)

MET_CODE_PATTERN = re.compile(r"^[0-9]{5}$")


class CatalogPublicationService:
    """Encapsulates validation, publication, and lifecycle for catalog entities."""

    @staticmethod
    def validate_met_metadata(obj: Any) -> None:
        """Validate 4-field MET bundle consistency (all present or all None)."""
        fields = [
            obj.met_value,
            obj.met_activity_code,
            obj.met_reference_version,
            obj.met_activity_description,
        ]
        all_null = all(f is None or f == "" for f in fields)
        all_present = all(f is not None and f != "" for f in fields)

        if not (all_null or all_present):
            raise ValidationError(
                "Усі 4 поля MET (met_value, met_activity_code, "
                "met_reference_version, met_activity_description) мають бути "
                "заповнені одночасно або залишені порожніми."
            )

        if all_present:
            if obj.met_value <= Decimal("0.00"):
                raise ValidationError(
                    {"met_value": "Значення MET має бути більшим за 0.00."}
                )
            if not MET_CODE_PATTERN.match(str(obj.met_activity_code)):
                raise ValidationError(
                    {
                        "met_activity_code": (
                            "Код активності MET має містити рівно 5 цифр."
                        )
                    }
                )
            if not str(obj.met_reference_version).strip():
                raise ValidationError(
                    {
                        "met_reference_version": (
                            "Версія довідника MET не може бути порожньою."
                        )
                    }
                )
            if not str(obj.met_activity_description).strip():
                raise ValidationError(
                    {
                        "met_activity_description": (
                            "Опис активності MET не може бути порожнім."
                        )
                    }
                )

    @classmethod
    def validate_exercise(cls, exercise: Exercise) -> None:
        """Validate an Exercise instance."""
        if not exercise.name or not exercise.name.strip():
            raise ValidationError({"name": "Назва вправи обов'язкова."})
        if exercise.category not in ExerciseCategory.values:
            raise ValidationError(
                {"category": f"Недійсна категорія: {exercise.category}"}
            )
        cls.validate_met_metadata(exercise)

    @classmethod
    def validate_workout_exercise_parameters(
        cls, we: WorkoutExercise, *, allow_archived_exercise: bool = False
    ) -> None:
        """Validate parameters of a WorkoutExercise against category (BR-002)."""
        if we.position is None or we.position <= 0:
            raise ValidationError(
                {"position": "Позиція вправи у тренуванні має бути > 0."}
            )

        exercise = we.exercise
        if not allow_archived_exercise and exercise.is_archived:
            raise ValidationError(
                f"Вправа '{exercise.name}' архівована і не може бути додана до "
                "активного тренування."
            )

        cat = exercise.category
        if cat == ExerciseCategory.STRENGTH:
            if we.recommended_sets is None or we.recommended_sets <= 0:
                raise ValidationError(
                    {
                        "recommended_sets": (
                            "Для силових вправ обов'язкова кількість підходів (> 0)."
                        )
                    }
                )
            if we.recommended_reps is None or we.recommended_reps <= 0:
                raise ValidationError(
                    {
                        "recommended_reps": (
                            "Для силових вправ обов'язкова кількість повторень (> 0)."
                        )
                    }
                )
            if we.recommended_load_kg is not None and we.recommended_load_kg < Decimal(
                "0.0"
            ):
                raise ValidationError(
                    {
                        "recommended_load_kg": (
                            "Рекомендована вага не може бути від'ємною."
                        )
                    }
                )
            if we.recommended_duration_min is not None:
                raise ValidationError(
                    {
                        "recommended_duration_min": (
                            "Тривалість не застосовується для силових вправ."
                        )
                    }
                )
            if we.recommended_distance_km is not None:
                raise ValidationError(
                    {
                        "recommended_distance_km": (
                            "Дистанція не застосовується для силових вправ."
                        )
                    }
                )

        elif cat == ExerciseCategory.CARDIO:
            if we.recommended_sets is not None:
                raise ValidationError(
                    {
                        "recommended_sets": (
                            "Кількість підходів не застосовується для кардіо-вправ."
                        )
                    }
                )
            if we.recommended_reps is not None:
                raise ValidationError(
                    {
                        "recommended_reps": (
                            "Кількість повторень не застосовується для кардіо-вправ."
                        )
                    }
                )
            if we.recommended_load_kg is not None:
                raise ValidationError(
                    {"recommended_load_kg": "Вага не застосовується для кардіо-вправ."}
                )

            has_dur = (
                we.recommended_duration_min is not None
                and we.recommended_duration_min > Decimal("0.00")
            )
            has_dist = (
                we.recommended_distance_km is not None
                and we.recommended_distance_km > Decimal("0.000")
            )
            if not (has_dur or has_dist):
                raise ValidationError(
                    "Для кардіо-вправ обов'язково вказати або тривалість "
                    "(> 0 хв), або дистанцію (> 0 км)."
                )

        elif cat == ExerciseCategory.YOGA:
            if we.recommended_sets is not None:
                raise ValidationError(
                    {
                        "recommended_sets": (
                            "Кількість підходів не застосовується для йоги."
                        )
                    }
                )
            if we.recommended_reps is not None:
                raise ValidationError(
                    {
                        "recommended_reps": (
                            "Кількість повторень не застосовується для йоги."
                        )
                    }
                )
            if we.recommended_load_kg is not None:
                raise ValidationError(
                    {"recommended_load_kg": "Вага не застосовується для йоги."}
                )
            if we.recommended_distance_km is not None:
                raise ValidationError(
                    {"recommended_distance_km": "Дистанція не застосовується для йоги."}
                )
            if (
                we.recommended_duration_min is None
                or we.recommended_duration_min <= Decimal("0.00")
            ):
                raise ValidationError(
                    {
                        "recommended_duration_min": (
                            "Для йоги обов'язкова тривалість (> 0 хв)."
                        )
                    }
                )

    @classmethod
    def validate_persisted_workout(
        cls, workout: Workout, *, allow_archived_exercises: bool = False
    ) -> None:
        """Validate a workout and child exercises already written in transaction."""
        cls.validate_met_metadata(workout)

        if workout.is_archived:
            return

        entries = list(
            workout.workout_exercises.select_related("exercise").order_by(
                "position", "id"
            )
        )
        if not entries:
            raise ValidationError(
                f"Активне тренування '{workout.name}' повинно містити "
                "щонайменше одну вправу (BR-002)."
            )

        positions = [e.position for e in entries]
        if len(positions) != len(set(positions)):
            raise ValidationError(
                "Позиції вправ у тренуванні мають бути унікальними (BR-002)."
            )

        for we in entries:
            cls.validate_workout_exercise_parameters(
                we, allow_archived_exercise=allow_archived_exercises
            )

    @classmethod
    def validate_persisted_program_template(cls, template: ProgramTemplate) -> None:
        """Validate a program template and child workouts written in transaction."""
        if template.fitness_goal not in FitnessGoal.values:
            raise ValidationError(
                {"fitness_goal": f"Недійсна ціль: {template.fitness_goal}"}
            )
        if template.experience_level not in ExperienceLevel.values:
            raise ValidationError(
                {"experience_level": f"Недійсний рівень: {template.experience_level}"}
            )
        if template.workouts_per_week < 1 or template.workouts_per_week > 7:
            raise ValidationError(
                {
                    "workouts_per_week": (
                        "Частота тренувань має бути від 1 до 7 днів на тиждень."
                    )
                }
            )

        if template.status == ProgramTemplateStatus.PUBLISHED:
            ptws = list(
                template.program_template_workouts.select_related("workout").order_by(
                    "position", "id"
                )
            )
            if not ptws:
                raise ValidationError(
                    f"Опублікований шаблон '{template.name}' повинен містити "
                    "щонайменше одне тренування (BR-003)."
                )

            positions = [ptw.position for ptw in ptws]
            if len(positions) != len(set(positions)):
                raise ValidationError(
                    "Позиції тренувань у шаблоні мають бути унікальними (BR-003)."
                )

            for ptw in ptws:
                if ptw.position <= 0:
                    raise ValidationError("Позиція тренування в шаблоні має бути > 0.")
                if ptw.suggested_weekday is not None and not (
                    1 <= ptw.suggested_weekday <= 7
                ):
                    raise ValidationError(
                        "Рекомендований день тижня має бути в межах 1..7 або порожнім."
                    )
                if ptw.workout.is_archived:
                    raise ValidationError(
                        "Опублікований шаблон не може містити архівоване тренування "
                        f"'{ptw.workout.name}' (BR-003)."
                    )
                cls.validate_persisted_workout(
                    ptw.workout, allow_archived_exercises=False
                )

    @classmethod
    @transaction.atomic
    def save_exercise(
        cls,
        *,
        name: str,
        category: str,
        description: str = "",
        met_value: Decimal | None = None,
        met_activity_code: str | None = None,
        met_reference_version: str | None = None,
        met_activity_description: str | None = None,
        is_archived: bool = False,
        instance: Exercise | None = None,
    ) -> Exercise:
        """Create or update an Exercise transactionally with full validation."""
        if instance is None:
            instance = Exercise()

        instance.name = name.strip()
        instance.category = category
        instance.description = description.strip()
        instance.met_value = met_value
        instance.met_activity_code = (
            met_activity_code.strip() if met_activity_code else None
        )
        instance.met_reference_version = (
            met_reference_version.strip() if met_reference_version else None
        )
        instance.met_activity_description = (
            met_activity_description.strip() if met_activity_description else None
        )
        instance.is_archived = is_archived

        cls.validate_exercise(instance)
        instance.full_clean()
        instance.save()
        return instance

    @classmethod
    @transaction.atomic
    def save_workout_with_composition(
        cls,
        *,
        name: str,
        category: str,
        exercises_data: list[dict[str, Any]],
        description: str = "",
        met_value: Decimal | None = None,
        met_activity_code: str | None = None,
        met_reference_version: str | None = None,
        met_activity_description: str | None = None,
        is_archived: bool = False,
        instance: Workout | None = None,
    ) -> Workout:
        """Create or update Workout with WorkoutExercise items atomically (BR-004)."""
        if instance is None:
            instance = Workout()

        instance.name = name.strip()
        instance.category = category
        instance.description = description.strip()
        instance.met_value = met_value
        instance.met_activity_code = (
            met_activity_code.strip() if met_activity_code else None
        )
        instance.met_reference_version = (
            met_reference_version.strip() if met_reference_version else None
        )
        instance.met_activity_description = (
            met_activity_description.strip() if met_activity_description else None
        )
        instance.is_archived = is_archived

        cls.validate_met_metadata(instance)
        instance.full_clean()
        instance.save()

        instance.workout_exercises.all().delete()
        for idx, item in enumerate(exercises_data, start=1):
            pos = item.get("position", idx)
            WorkoutExercise.objects.create(
                workout=instance,
                exercise=item["exercise"],
                position=pos,
                recommended_sets=item.get("recommended_sets"),
                recommended_reps=item.get("recommended_reps"),
                recommended_load_kg=item.get("recommended_load_kg"),
                recommended_duration_min=item.get("recommended_duration_min"),
                recommended_distance_km=item.get("recommended_distance_km"),
            )

        cls.validate_persisted_workout(instance)
        return instance

    @classmethod
    @transaction.atomic
    def save_program_template_with_composition(
        cls,
        *,
        name: str,
        fitness_goal: str,
        experience_level: str,
        workouts_per_week: int,
        workouts_data: list[dict[str, Any]],
        description: str = "",
        status: str = ProgramTemplateStatus.PUBLISHED,
        instance: ProgramTemplate | None = None,
    ) -> ProgramTemplate:
        """Create or update ProgramTemplate with items atomically (BR-004)."""
        if instance is None:
            instance = ProgramTemplate()

        instance.name = name.strip()
        instance.description = description.strip()
        instance.fitness_goal = fitness_goal
        instance.experience_level = experience_level
        instance.workouts_per_week = workouts_per_week
        instance.status = status

        instance.full_clean()
        instance.save()

        instance.program_template_workouts.all().delete()
        for idx, item in enumerate(workouts_data, start=1):
            pos = item.get("position", idx)
            ProgramTemplateWorkout.objects.create(
                program_template=instance,
                workout=item["workout"],
                position=pos,
                suggested_weekday=item.get("suggested_weekday"),
            )

        cls.validate_persisted_program_template(instance)
        return instance

    @classmethod
    @transaction.atomic
    def archive_exercise(cls, *, exercise: Exercise) -> Exercise:
        """Soft-archive exercise, verifying it does not break active workouts."""
        active_workouts = Workout.objects.filter(
            is_archived=False,
            workout_exercises__exercise=exercise,
        ).distinct()
        if active_workouts.exists():
            names = ", ".join(w.name for w in active_workouts[:3])
            raise ValidationError(
                f"Неможливо архівувати вправу '{exercise.name}', оскільки вона "
                f"використовується в активних тренуваннях: {names}."
            )
        exercise.is_archived = True
        exercise.save(update_fields=["is_archived"])
        return exercise

    @classmethod
    @transaction.atomic
    def archive_workout(cls, *, workout: Workout) -> Workout:
        """Soft-archive workout, verifying it does not break published templates."""
        active_templates = ProgramTemplate.objects.filter(
            status=ProgramTemplateStatus.PUBLISHED,
            program_template_workouts__workout=workout,
        ).distinct()
        if active_templates.exists():
            names = ", ".join(t.name for t in active_templates[:3])
            raise ValidationError(
                f"Неможливо архівувати тренування '{workout.name}', оскільки "
                f"воно використовується в опублікованих шаблонах програм: {names}."
            )
        workout.is_archived = True
        workout.save(update_fields=["is_archived"])
        return workout

    @classmethod
    @transaction.atomic
    def archive_program_template(cls, *, template: ProgramTemplate) -> ProgramTemplate:
        """Soft-archive a program template."""
        template.status = ProgramTemplateStatus.ARCHIVED
        template.save(update_fields=["status"])
        return template
