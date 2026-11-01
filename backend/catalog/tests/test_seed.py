from io import StringIO

import pytest
from django.core.management import call_command

from accounts.models import ExperienceLevel, FitnessGoal
from catalog.models import (
    Exercise,
    ExerciseCategory,
    ProgramTemplate,
    ProgramTemplateStatus,
    ProgramTemplateWorkout,
    Workout,
    WorkoutExercise,
)


@pytest.mark.django_db
class TestSeedCatalogCommand:
    """Verifies seed_catalog idempotency, data integrity, and paired template rules."""

    def test_seed_catalog_initial_and_repeated_execution(self):
        out = StringIO()
        call_command("seed_catalog", stdout=out)

        assert Exercise.objects.count() == 10
        assert Workout.objects.count() == 6
        assert ProgramTemplate.objects.count() == 6
        assert WorkoutExercise.objects.count() == 14
        assert ProgramTemplateWorkout.objects.count() == 18

        # Run a second time
        out2 = StringIO()
        call_command("seed_catalog", stdout=out2)

        # Idempotency check: exactly the same counts, zero duplicates
        assert Exercise.objects.count() == 10
        assert Workout.objects.count() == 6
        assert ProgramTemplate.objects.count() == 6
        assert WorkoutExercise.objects.count() == 14
        assert ProgramTemplateWorkout.objects.count() == 18

    def test_seed_preserves_custom_admin_records(self):
        # Create an unrelated custom admin exercise and workout before seeding
        custom_ex = Exercise.objects.create(
            name="Індивідуальна вправа тренера",
            category=ExerciseCategory.STRENGTH,
            description="Спеціальна методика",
        )
        custom_workout = Workout.objects.create(
            name="Індивідуальне тренування тренера",
            category=ExerciseCategory.STRENGTH,
        )
        WorkoutExercise.objects.create(
            workout=custom_workout,
            exercise=custom_ex,
            position=1,
            recommended_sets=3,
            recommended_reps=10,
        )

        # Run seed
        call_command("seed_catalog", stdout=StringIO())

        # Counts: 10 seed + 1 custom = 11 exercises, 6 seed + 1 custom = 7 workouts
        assert Exercise.objects.count() == 11
        assert Workout.objects.count() == 7
        assert Exercise.objects.filter(name="Індивідуальна вправа тренера").exists()
        assert Workout.objects.filter(name="Індивідуальне тренування тренера").exists()

    def test_paired_templates_support_phase_4_selection_strategies(self):
        call_command("seed_catalog", stdout=StringIO())

        # All 6 templates must be published, for beginner, with 3 workouts_per_week
        templates = ProgramTemplate.objects.filter(
            experience_level=ExperienceLevel.BEGINNER,
            workouts_per_week=3,
            status=ProgramTemplateStatus.PUBLISHED,
        )
        assert templates.count() == 6

        # Pair 1: Weight Loss
        wl_templates = list(templates.filter(fitness_goal=FitnessGoal.WEIGHT_LOSS))
        assert len(wl_templates) == 2
        # One template must have higher cardio workout ratio than the other
        t1_cardio = (
            wl_templates[0]
            .program_template_workouts.filter(workout__category=ExerciseCategory.CARDIO)
            .count()
        )
        t2_cardio = (
            wl_templates[1]
            .program_template_workouts.filter(workout__category=ExerciseCategory.CARDIO)
            .count()
        )
        assert t1_cardio != t2_cardio, (
            "Weight loss pair must have distinct cardio shares for strategy evaluation"
        )

        # Pair 2: Muscle Gain
        mg_templates = list(templates.filter(fitness_goal=FitnessGoal.MUSCLE_GAIN))
        assert len(mg_templates) == 2
        t1_strength = (
            mg_templates[0]
            .program_template_workouts.filter(
                workout__category=ExerciseCategory.STRENGTH
            )
            .count()
        )
        t2_strength = (
            mg_templates[1]
            .program_template_workouts.filter(
                workout__category=ExerciseCategory.STRENGTH
            )
            .count()
        )
        assert t1_strength != t2_strength, (
            "Muscle gain pair must have distinct strength shares"
        )

        # Pair 3: Maintenance
        maint_templates = list(templates.filter(fitness_goal=FitnessGoal.MAINTENANCE))
        assert len(maint_templates) == 2
        # Check that one is balanced (has all 3 categories)
        cats_t1 = set(
            maint_templates[0].program_template_workouts.values_list(
                "workout__category", flat=True
            )
        )
        cats_t2 = set(
            maint_templates[1].program_template_workouts.values_list(
                "workout__category", flat=True
            )
        )
        assert (len(cats_t1) == 3 or len(cats_t2) == 3) and (cats_t1 != cats_t2), (
            "Maintenance pair must contain balanced template and alternative"
        )
