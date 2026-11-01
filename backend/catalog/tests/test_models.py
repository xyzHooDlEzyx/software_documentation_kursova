from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from accounts.models import ExperienceLevel, FitnessGoal
from catalog.models import (
    Exercise,
    ExerciseCategory,
    ProgramTemplate,
    ProgramTemplateWorkout,
    Workout,
    WorkoutExercise,
)


@pytest.mark.django_db
class TestCatalogModelsAndConstraints:
    """Verifies schema, constraints, unique keys, and referential integrity."""

    def test_valid_exercise_creation_without_met(self):
        exercise = Exercise.objects.create(
            name="Розминка",
            category=ExerciseCategory.YOGA,
            description="Легка розминка",
        )
        assert exercise.pk is not None
        assert exercise.category == "yoga"
        assert exercise.is_archived is False
        assert exercise.met_value is None

    def test_valid_exercise_creation_with_met(self):
        exercise = Exercise.objects.create(
            name="Присідання",
            category=ExerciseCategory.STRENGTH,
            met_value=Decimal("5.00"),
            met_activity_code="02052",
            met_reference_version="Compendium 2024",
            met_activity_description="resistance training, squats",
        )
        assert exercise.pk is not None
        assert exercise.met_value == Decimal("5.00")

    def test_exercise_invalid_category_fails_db_constraint(self):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Exercise.objects.create(
                    name="Невідома вправа",
                    category="swimming",  # invalid category
                )

    def test_exercise_invalid_met_value_fails_db_constraint(self):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Exercise.objects.create(
                    name="Присідання з нульовим MET",
                    category=ExerciseCategory.STRENGTH,
                    met_value=Decimal("0.00"),
                    met_activity_code="02052",
                    met_reference_version="Compendium 2024",
                    met_activity_description="squats",
                )

    def test_exercise_invalid_met_code_fails_db_constraint(self):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Exercise.objects.create(
                    name="Присідання з невірним кодом MET",
                    category=ExerciseCategory.STRENGTH,
                    met_value=Decimal("5.00"),
                    met_activity_code="123",  # requires 5 digits
                    met_reference_version="Compendium 2024",
                    met_activity_description="squats",
                )

    def test_exercise_partial_met_package_fails_db_constraint(self):
        # 3 fields provided, 1 missing -> violates exercises_met_pkg_consistent
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Exercise.objects.create(
                    name="Частковий MET",
                    category=ExerciseCategory.CARDIO,
                    met_value=Decimal("8.00"),
                    met_activity_code="02022",
                    met_reference_version="Compendium 2024",
                    met_activity_description=None,
                )

    def test_workout_invalid_category_fails_db_constraint(self):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Workout.objects.create(
                    name="Невідоме тренування",
                    category="invalid_category",
                )

    def test_workout_exercise_position_must_be_positive(self):
        workout = Workout.objects.create(
            name="Тренування 1", category=ExerciseCategory.STRENGTH
        )
        exercise = Exercise.objects.create(
            name="Вправа 1", category=ExerciseCategory.STRENGTH
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                WorkoutExercise.objects.create(
                    workout=workout,
                    exercise=exercise,
                    position=0,  # position must be > 0
                )

    def test_workout_exercise_position_unique_per_workout(self):
        workout = Workout.objects.create(
            name="Тренування 2", category=ExerciseCategory.STRENGTH
        )
        ex1 = Exercise.objects.create(
            name="Вправа А", category=ExerciseCategory.STRENGTH
        )
        ex2 = Exercise.objects.create(
            name="Вправа Б", category=ExerciseCategory.STRENGTH
        )

        WorkoutExercise.objects.create(workout=workout, exercise=ex1, position=1)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                WorkoutExercise.objects.create(
                    workout=workout, exercise=ex2, position=1
                )

    def test_same_exercise_can_repeat_at_different_positions_in_workout(self):
        workout = Workout.objects.create(
            name="Тренування з повтором", category=ExerciseCategory.STRENGTH
        )
        exercise = Exercise.objects.create(
            name="Присідання", category=ExerciseCategory.STRENGTH
        )

        we1 = WorkoutExercise.objects.create(
            workout=workout,
            exercise=exercise,
            position=1,
            recommended_sets=3,
            recommended_reps=10,
        )
        we2 = WorkoutExercise.objects.create(
            workout=workout,
            exercise=exercise,
            position=2,
            recommended_sets=2,
            recommended_reps=12,
        )
        assert we1.pk != we2.pk
        assert workout.workout_exercises.count() == 2

    def test_workout_exercise_negative_recommended_values_fail_db_constraint(self):
        workout = Workout.objects.create(
            name="Тренування 3", category=ExerciseCategory.STRENGTH
        )
        exercise = Exercise.objects.create(
            name="Вправа 3", category=ExerciseCategory.STRENGTH
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                WorkoutExercise.objects.create(
                    workout=workout,
                    exercise=exercise,
                    position=1,
                    recommended_load_kg=Decimal("-1.0"),
                )

    def test_program_template_frequency_and_choices_constraints(self):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProgramTemplate.objects.create(
                    name="Невірні частота",
                    fitness_goal=FitnessGoal.WEIGHT_LOSS,
                    experience_level=ExperienceLevel.BEGINNER,
                    workouts_per_week=0,  # must be >= 1
                )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProgramTemplate.objects.create(
                    name="Завелика частота",
                    fitness_goal=FitnessGoal.WEIGHT_LOSS,
                    experience_level=ExperienceLevel.BEGINNER,
                    workouts_per_week=8,  # must be <= 7
                )

    def test_program_template_workout_constraints(self):
        template = ProgramTemplate.objects.create(
            name="Шаблон 1",
            fitness_goal=FitnessGoal.WEIGHT_LOSS,
            experience_level=ExperienceLevel.BEGINNER,
            workouts_per_week=3,
        )
        workout = Workout.objects.create(
            name="Тренування Ш1", category=ExerciseCategory.CARDIO
        )

        # Unique position per template
        ProgramTemplateWorkout.objects.create(
            program_template=template,
            workout=workout,
            position=1,
            suggested_weekday=1,
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProgramTemplateWorkout.objects.create(
                    program_template=template,
                    workout=workout,
                    position=1,  # duplicate position
                )

        # Invalid weekday
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProgramTemplateWorkout.objects.create(
                    program_template=template,
                    workout=workout,
                    position=2,
                    suggested_weekday=8,  # 1..7 only
                )

    def test_same_workout_can_repeat_at_different_positions_in_template(self):
        template = ProgramTemplate.objects.create(
            name="Шаблон з повтором",
            fitness_goal=FitnessGoal.MUSCLE_GAIN,
            experience_level=ExperienceLevel.BEGINNER,
            workouts_per_week=2,
        )
        workout = Workout.objects.create(
            name="Тренування Повтор", category=ExerciseCategory.STRENGTH
        )

        ptw1 = ProgramTemplateWorkout.objects.create(
            program_template=template, workout=workout, position=1, suggested_weekday=1
        )
        ptw2 = ProgramTemplateWorkout.objects.create(
            program_template=template, workout=workout, position=2, suggested_weekday=4
        )
        assert ptw1.pk != ptw2.pk
        assert template.program_template_workouts.count() == 2

    def test_referential_integrity_protects_referenced_exercise_and_workout(self):
        exercise = Exercise.objects.create(
            name="Захищена вправа", category=ExerciseCategory.STRENGTH
        )
        workout = Workout.objects.create(
            name="Захищене тренування", category=ExerciseCategory.STRENGTH
        )
        WorkoutExercise.objects.create(workout=workout, exercise=exercise, position=1)

        template = ProgramTemplate.objects.create(
            name="Захищений шаблон",
            fitness_goal=FitnessGoal.MAINTENANCE,
            experience_level=ExperienceLevel.INTERMEDIATE,
            workouts_per_week=3,
        )
        ProgramTemplateWorkout.objects.create(
            program_template=template, workout=workout, position=1
        )

        # Attempting physical delete of exercise protected by workout_exercises
        with pytest.raises(ProtectedError):
            exercise.delete()

        # Attempting physical delete of workout protected by program_template_workouts
        with pytest.raises(ProtectedError):
            workout.delete()
