"""PostgreSQL integrity tests for independent personal program copies."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from accounts.models import FitnessGoal
from catalog.models import Exercise, ExerciseCategory, ProgramTemplate, Workout
from planning.models import (
    UserProgram,
    UserProgramExercise,
    UserProgramStatus,
    UserProgramWorkout,
)

User = get_user_model()


@pytest.fixture
def personal_catalog(db):
    user = User.objects.create_user("planner@example.test", "SafePassword2026!")
    template = ProgramTemplate.objects.create(
        name="Початкова програма",
        fitness_goal=FitnessGoal.MUSCLE_GAIN,
        experience_level="beginner",
        workouts_per_week=3,
        status="published",
    )
    workout = Workout.objects.create(
        name="Силовий блок", category=ExerciseCategory.STRENGTH
    )
    exercise = Exercise.objects.create(
        name="Присідання", category=ExerciseCategory.STRENGTH
    )
    return user, template, workout, exercise


def make_program(personal_catalog):
    user, template, _, _ = personal_catalog
    return UserProgram.objects.create(
        user=user,
        source_program_template=template,
        source_program_template_name_snapshot=template.name,
        fitness_goal=template.fitness_goal,
        name="Моя програма",
        description="Початковий опис",
    )


@pytest.mark.django_db
def test_draft_defaults_and_frozen_source_identity(personal_catalog):
    program = make_program(personal_catalog)
    _, template, _, _ = personal_catalog
    assert program.status == UserProgramStatus.DRAFT
    assert program.is_archived is False
    assert program.bonus_target_sessions is None
    assert program.activated_at is None
    assert program.completed_at is None
    assert program.source_program_template_id == template.pk
    assert program.source_program_template_name_snapshot == template.name
    assert program.fitness_goal == FitnessGoal.MUSCLE_GAIN


@pytest.mark.django_db
def test_personal_workout_and_exercise_occurrences_cascade(personal_catalog):
    program = make_program(personal_catalog)
    _, _, workout, exercise = personal_catalog
    first = UserProgramWorkout.objects.create(
        user_program=program,
        source_workout=workout,
        position=1,
        name=workout.name,
        category=workout.category,
    )
    second = UserProgramWorkout.objects.create(
        user_program=program,
        source_workout=workout,
        position=2,
        name=workout.name,
        category=workout.category,
    )
    for position in (1, 2):
        UserProgramExercise.objects.create(
            user_program_workout=first,
            exercise=exercise,
            position=position,
            recommended_sets=3,
            recommended_reps=8,
            recommended_load_kg=Decimal("20.0"),
        )
    assert list(program.workouts.values_list("position", flat=True)) == [1, 2]
    assert first.source_workout_id == second.source_workout_id
    assert first.exercises.count() == 2
    program.delete()
    assert not UserProgramWorkout.objects.filter(pk__in=[first.pk, second.pk]).exists()
    assert UserProgramExercise.objects.count() == 0
    assert Workout.objects.filter(pk=workout.pk).exists()
    assert Exercise.objects.filter(pk=exercise.pk).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("position", [0, -1])
def test_workout_position_must_be_positive(personal_catalog, position):
    program = make_program(personal_catalog)
    _, _, workout, _ = personal_catalog
    with pytest.raises(IntegrityError), transaction.atomic():
        UserProgramWorkout.objects.create(
            user_program=program,
            source_workout=workout,
            position=position,
            name=workout.name,
            category=workout.category,
        )


@pytest.mark.django_db
def test_workout_position_unique_per_program(personal_catalog):
    program = make_program(personal_catalog)
    _, _, workout, _ = personal_catalog
    fields = dict(
        user_program=program,
        source_workout=workout,
        position=1,
        name=workout.name,
        category=workout.category,
    )
    UserProgramWorkout.objects.create(**fields)
    with pytest.raises(IntegrityError), transaction.atomic():
        UserProgramWorkout.objects.create(**fields)


@pytest.mark.django_db
def test_exercise_position_unique_and_positive(personal_catalog):
    program = make_program(personal_catalog)
    _, _, workout, exercise = personal_catalog
    occurrence = UserProgramWorkout.objects.create(
        user_program=program,
        source_workout=workout,
        position=1,
        name=workout.name,
        category=workout.category,
    )
    fields = dict(
        user_program_workout=occurrence,
        exercise=exercise,
        recommended_sets=3,
        recommended_reps=8,
    )
    UserProgramExercise.objects.create(position=1, **fields)
    with pytest.raises(IntegrityError), transaction.atomic():
        UserProgramExercise.objects.create(position=1, **fields)
    with pytest.raises(IntegrityError), transaction.atomic():
        UserProgramExercise.objects.create(position=0, **fields)


@pytest.mark.django_db
def test_invalid_personal_status_and_category_rejected(personal_catalog):
    user, template, workout, _ = personal_catalog
    with pytest.raises(IntegrityError), transaction.atomic():
        UserProgram.objects.create(
            user=user,
            source_program_template=template,
            source_program_template_name_snapshot=template.name,
            fitness_goal=template.fitness_goal,
            name="Недійсна",
            status="archived",
        )
    program = make_program(personal_catalog)
    with pytest.raises(IntegrityError), transaction.atomic():
        UserProgramWorkout.objects.create(
            user_program=program,
            source_workout=workout,
            position=1,
            name=workout.name,
            category="unknown",
        )


@pytest.mark.django_db
def test_shared_catalog_references_are_protected(personal_catalog):
    program = make_program(personal_catalog)
    _, template, workout, exercise = personal_catalog
    occurrence = UserProgramWorkout.objects.create(
        user_program=program,
        source_workout=workout,
        position=1,
        name=workout.name,
        category=workout.category,
    )
    UserProgramExercise.objects.create(
        user_program_workout=occurrence,
        exercise=exercise,
        position=1,
        recommended_sets=3,
        recommended_reps=8,
    )
    for source in (template, workout, exercise):
        with pytest.raises(ProtectedError):
            source.delete()
