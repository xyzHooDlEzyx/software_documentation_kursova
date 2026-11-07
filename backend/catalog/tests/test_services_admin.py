from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

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
from catalog.services import CatalogPublicationService

User = get_user_model()


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(
        email="admin@fitness.local",
        password="AdminSecurePassword123!",
        is_staff=True,
        is_active=True,
    )
    user.groups.add(Group.objects.get(name="Administrator"))
    return user


@pytest.fixture
def staff_without_permissions(db):
    return User.objects.create_user(
        email="staff@fitness.local",
        password="StaffSecurePassword123!",
        is_staff=True,
        is_active=True,
    )


@pytest.fixture
def non_staff_user(db):
    user = User.objects.create_user(
        email="user@fitness.local",
        password="UserSecurePassword123!",
        is_staff=False,
        is_active=True,
    )
    return user


@pytest.mark.django_db
class TestCatalogPublicationService:
    """Tests domain validation rules BR-002, BR-003, BR-004, and BR-005."""

    def test_strength_exercise_parameter_validation(self):
        ex = Exercise.objects.create(name="Жим", category=ExerciseCategory.STRENGTH)
        workout = Workout.objects.create(
            name="Сила", category=ExerciseCategory.STRENGTH
        )
        we = WorkoutExercise(workout=workout, exercise=ex, position=1)

        # Missing sets
        we.recommended_sets = None
        we.recommended_reps = 10
        with pytest.raises(ValidationError):
            CatalogPublicationService.validate_workout_exercise_parameters(we)

        # Missing reps
        we.recommended_sets = 3
        we.recommended_reps = None
        with pytest.raises(ValidationError):
            CatalogPublicationService.validate_workout_exercise_parameters(we)

        # Duration not allowed for strength
        we.recommended_reps = 10
        we.recommended_duration_min = Decimal("10.00")
        with pytest.raises(ValidationError):
            CatalogPublicationService.validate_workout_exercise_parameters(we)

        # Valid strength parameters
        we.recommended_duration_min = None
        we.recommended_load_kg = Decimal("40.0")
        CatalogPublicationService.validate_workout_exercise_parameters(we)

    def test_cardio_exercise_parameter_validation(self):
        ex = Exercise.objects.create(
            name="Біг", category=ExerciseCategory.CARDIO, tracks_distance=True
        )
        workout = Workout.objects.create(
            name="Кардіо", category=ExerciseCategory.CARDIO
        )
        we = WorkoutExercise(workout=workout, exercise=ex, position=1)

        # Neither duration nor distance
        with pytest.raises(ValidationError):
            CatalogPublicationService.validate_workout_exercise_parameters(we)

        # Sets/reps not allowed for cardio
        we.recommended_duration_min = Decimal("20.00")
        we.recommended_sets = 3
        with pytest.raises(ValidationError):
            CatalogPublicationService.validate_workout_exercise_parameters(we)

        # Valid cardio with duration
        we.recommended_sets = None
        CatalogPublicationService.validate_workout_exercise_parameters(we)

        # Valid cardio with distance
        we.recommended_duration_min = None
        we.recommended_distance_km = Decimal("5.000")
        CatalogPublicationService.validate_workout_exercise_parameters(we)

    def test_yoga_exercise_parameter_validation(self):
        ex = Exercise.objects.create(name="Йога", category=ExerciseCategory.YOGA)
        workout = Workout.objects.create(
            name="Йога сесія", category=ExerciseCategory.YOGA
        )
        we = WorkoutExercise(workout=workout, exercise=ex, position=1)

        # Missing duration
        with pytest.raises(ValidationError):
            CatalogPublicationService.validate_workout_exercise_parameters(we)

        # Distance not allowed for yoga
        we.recommended_duration_min = Decimal("30.00")
        we.recommended_distance_km = Decimal("1.000")
        with pytest.raises(ValidationError):
            CatalogPublicationService.validate_workout_exercise_parameters(we)

        # Valid yoga
        we.recommended_distance_km = None
        CatalogPublicationService.validate_workout_exercise_parameters(we)

    def test_active_workout_must_have_at_least_one_exercise(self):
        workout = Workout.objects.create(
            name="Порожнє тренування", category=ExerciseCategory.STRENGTH
        )
        with pytest.raises(ValidationError) as exc:
            CatalogPublicationService.validate_persisted_workout(workout)
        assert "BR-002" in str(exc.value)

    def test_published_template_must_have_at_least_one_workout(self):
        template = ProgramTemplate.objects.create(
            name="Порожній шаблон",
            fitness_goal=FitnessGoal.WEIGHT_LOSS,
            experience_level=ExperienceLevel.BEGINNER,
            workouts_per_week=3,
            status=ProgramTemplateStatus.PUBLISHED,
        )
        with pytest.raises(ValidationError) as exc:
            CatalogPublicationService.validate_persisted_program_template(template)
        assert "BR-003" in str(exc.value)

    def test_published_template_cannot_reference_archived_workout(self):
        ex = Exercise.objects.create(name="Вправа", category=ExerciseCategory.YOGA)
        workout = Workout.objects.create(
            name="Архівоване тренування",
            category=ExerciseCategory.YOGA,
            is_archived=True,
        )
        WorkoutExercise.objects.create(
            workout=workout,
            exercise=ex,
            position=1,
            recommended_duration_min=Decimal("20.00"),
        )

        template = ProgramTemplate.objects.create(
            name="Шаблон з архівом",
            fitness_goal=FitnessGoal.MAINTENANCE,
            experience_level=ExperienceLevel.BEGINNER,
            workouts_per_week=1,
            status=ProgramTemplateStatus.PUBLISHED,
        )
        ProgramTemplateWorkout.objects.create(
            program_template=template, workout=workout, position=1
        )

        with pytest.raises(ValidationError) as exc:
            CatalogPublicationService.validate_persisted_program_template(template)
        assert "архівоване тренування" in str(exc.value)

    def test_archive_exercise_guards_active_workouts(self):
        ex = Exercise.objects.create(
            name="Вправа в тренуванні", category=ExerciseCategory.STRENGTH
        )
        workout = Workout.objects.create(
            name="Активне тренування", category=ExerciseCategory.STRENGTH
        )
        WorkoutExercise.objects.create(
            workout=workout,
            exercise=ex,
            position=1,
            recommended_sets=3,
            recommended_reps=10,
        )

        with pytest.raises(ValidationError):
            CatalogPublicationService.archive_exercise(exercise=ex)

        # Once workout is archived, exercise can be archived
        workout.is_archived = True
        workout.save()
        CatalogPublicationService.archive_exercise(exercise=ex)
        ex.refresh_from_db()
        assert ex.is_archived is True

    def test_archive_workout_guards_published_templates(self):
        ex = Exercise.objects.create(
            name="Вправа Т", category=ExerciseCategory.STRENGTH
        )
        workout = Workout.objects.create(
            name="Тренування Т", category=ExerciseCategory.STRENGTH
        )
        WorkoutExercise.objects.create(
            workout=workout,
            exercise=ex,
            position=1,
            recommended_sets=3,
            recommended_reps=10,
        )

        template = ProgramTemplate.objects.create(
            name="Опублікована програма",
            fitness_goal=FitnessGoal.MUSCLE_GAIN,
            experience_level=ExperienceLevel.BEGINNER,
            workouts_per_week=1,
            status=ProgramTemplateStatus.PUBLISHED,
        )
        ProgramTemplateWorkout.objects.create(
            program_template=template, workout=workout, position=1
        )

        with pytest.raises(ValidationError):
            CatalogPublicationService.archive_workout(workout=workout)

        # Once template is archived, workout can be archived
        template.status = ProgramTemplateStatus.ARCHIVED
        template.save()
        CatalogPublicationService.archive_workout(workout=workout)
        workout.refresh_from_db()
        assert workout.is_archived is True


@pytest.mark.django_db
class TestDjangoAdminPublicationAtomicity:
    """Tests atomic savepoint rollback on invalid inline composition in Django Admin."""

    def test_admin_access_restricted_to_staff(
        self, client: Client, admin_user, non_staff_user
    ):
        admin_url = reverse("admin:catalog_workout_changelist")

        # Unauthenticated -> redirect to login
        res = client.get(admin_url)
        assert res.status_code == 302

        # Non-staff user -> redirect to admin login
        client.force_login(non_staff_user)
        res = client.get(admin_url)
        assert res.status_code == 302

        # Staff user -> 200 OK
        client.force_login(admin_user)
        res = client.get(admin_url)
        assert res.status_code == 200

    def test_workout_admin_creation_fails_atomically_without_exercises(
        self, client: Client, admin_user
    ):
        client.force_login(admin_user)
        add_url = reverse("admin:catalog_workout_add")

        initial_count = Workout.objects.count()

        # Submit workout form without any inline exercises
        post_data = {
            "name": "Тренування без вправ",
            "category": ExerciseCategory.STRENGTH,
            "description": "Тест відкату",
            "workout_exercises-TOTAL_FORMS": "0",
            "workout_exercises-INITIAL_FORMS": "0",
            "workout_exercises-MIN_NUM_FORMS": "0",
            "workout_exercises-MAX_NUM_FORMS": "1000",
        }
        response = client.post(add_url, data=post_data)

        # Must return 200 changeform with error, NOT redirect (302)
        assert response.status_code == 200
        # No partial workout row committed to DB!
        assert Workout.objects.count() == initial_count
        assert not Workout.objects.filter(name="Тренування без вправ").exists()

    def test_template_admin_creation_fails_atomically_without_workouts(
        self, client: Client, admin_user
    ):
        client.force_login(admin_user)
        add_url = reverse("admin:catalog_programtemplate_add")

        initial_count = ProgramTemplate.objects.count()

        # Submit published template form without any inline workouts
        post_data = {
            "name": "Шаблон без тренувань",
            "fitness_goal": FitnessGoal.WEIGHT_LOSS,
            "experience_level": ExperienceLevel.BEGINNER,
            "workouts_per_week": 3,
            "status": ProgramTemplateStatus.PUBLISHED,
            "program_template_workouts-TOTAL_FORMS": "0",
            "program_template_workouts-INITIAL_FORMS": "0",
            "program_template_workouts-MIN_NUM_FORMS": "0",
            "program_template_workouts-MAX_NUM_FORMS": "1000",
        }
        response = client.post(add_url, data=post_data)

        # Must return 200 changeform with error
        assert response.status_code == 200
        # No partial template row committed to DB!
        assert ProgramTemplate.objects.count() == initial_count
        assert not ProgramTemplate.objects.filter(name="Шаблон без тренувань").exists()

    def test_template_admin_edit_rollback_when_deleting_last_workout(
        self, client: Client, admin_user
    ):
        client.force_login(admin_user)

        # Setup valid published template with 1 workout
        ex = Exercise.objects.create(
            name="Вправа Р", category=ExerciseCategory.STRENGTH
        )
        workout = Workout.objects.create(
            name="Тренування Р", category=ExerciseCategory.STRENGTH
        )
        WorkoutExercise.objects.create(
            workout=workout,
            exercise=ex,
            position=1,
            recommended_sets=3,
            recommended_reps=10,
        )

        template = ProgramTemplate.objects.create(
            name="Шаблон для зміни",
            fitness_goal=FitnessGoal.WEIGHT_LOSS,
            experience_level=ExperienceLevel.BEGINNER,
            workouts_per_week=3,
            status=ProgramTemplateStatus.PUBLISHED,
        )
        ptw = ProgramTemplateWorkout.objects.create(
            program_template=template, workout=workout, position=1
        )

        change_url = reverse("admin:catalog_programtemplate_change", args=[template.pk])

        # Submit update with DELETE flag set on the only workout inline
        post_data = {
            "name": "Шаблон для зміни",
            "fitness_goal": FitnessGoal.WEIGHT_LOSS,
            "experience_level": ExperienceLevel.BEGINNER,
            "workouts_per_week": 3,
            "status": ProgramTemplateStatus.PUBLISHED,
            "program_template_workouts-TOTAL_FORMS": "1",
            "program_template_workouts-INITIAL_FORMS": "1",
            "program_template_workouts-MIN_NUM_FORMS": "0",
            "program_template_workouts-MAX_NUM_FORMS": "1000",
            "program_template_workouts-0-id": str(ptw.pk),
            "program_template_workouts-0-program_template": str(template.pk),
            "program_template_workouts-0-workout": str(workout.pk),
            "program_template_workouts-0-position": "1",
            "program_template_workouts-0-DELETE": "on",
        }
        response = client.post(change_url, data=post_data)

        # Must return 200 with error
        assert response.status_code == 200
        # Inline was NOT deleted in DB due to atomic savepoint rollback!
        assert ProgramTemplateWorkout.objects.filter(pk=ptw.pk).exists()
        assert template.program_template_workouts.count() == 1


@pytest.mark.django_db
class TestAdminCannotBypassCatalogRules:
    """Regression tests: admin must not bypass BR-002/BR-004 or archive guards."""

    def _strength_workout(self):
        exercise = Exercise.objects.create(
            name="Жим лежачи", category=ExerciseCategory.STRENGTH
        )
        workout = Workout.objects.create(
            name="Силове Б", category=ExerciseCategory.STRENGTH
        )
        WorkoutExercise.objects.create(
            workout=workout,
            exercise=exercise,
            position=1,
            recommended_sets=3,
            recommended_reps=8,
        )
        return exercise, workout

    def test_staff_without_model_permissions_is_denied(
        self, client: Client, staff_without_permissions
    ):
        client.force_login(staff_without_permissions)
        res = client.get(reverse("admin:catalog_workout_changelist"))
        assert res.status_code == 403

    @pytest.mark.parametrize(
        "url",
        ["/admin/catalog/workoutexercise/", "/admin/catalog/programtemplateworkout/"],
    )
    def test_join_tables_have_no_standalone_admin(
        self, client: Client, admin_user, url
    ):
        client.force_login(admin_user)
        assert client.get(url).status_code == 404

    def test_is_archived_is_read_only_in_admin_forms(self, client: Client, admin_user):
        exercise, workout = self._strength_workout()
        client.force_login(admin_user)

        for url in (
            reverse("admin:catalog_exercise_change", args=[exercise.pk]),
            reverse("admin:catalog_workout_change", args=[workout.pk]),
        ):
            page = client.get(url)
            assert page.status_code == 200
            assert "is_archived" not in page.context["adminform"].form.fields

    def test_category_change_of_used_exercise_is_rejected(self):
        exercise, _ = self._strength_workout()
        exercise.category = ExerciseCategory.CARDIO

        with pytest.raises(ValidationError) as exc:
            CatalogPublicationService.validate_exercise_category_change(exercise)
        assert "category" in exc.value.message_dict

    def test_category_change_via_admin_form_is_rejected(
        self, client: Client, admin_user
    ):
        exercise, _ = self._strength_workout()
        client.force_login(admin_user)

        response = client.post(
            reverse("admin:catalog_exercise_change", args=[exercise.pk]),
            {
                "name": exercise.name,
                "description": "",
                "category": ExerciseCategory.CARDIO,
                "_save": "Save",
            },
        )
        assert response.status_code == 200
        assert "category" in response.context["adminform"].form.errors
        exercise.refresh_from_db()
        assert exercise.category == ExerciseCategory.STRENGTH

    def test_category_change_of_unused_exercise_is_allowed(self):
        exercise = Exercise.objects.create(
            name="Нова вправа", category=ExerciseCategory.STRENGTH
        )
        exercise.category = ExerciseCategory.YOGA
        CatalogPublicationService.validate_exercise_category_change(exercise)


@pytest.mark.django_db
def test_exercise_without_met_data_can_be_created_in_admin(client: Client, admin_user):
    client.force_login(admin_user)
    response = client.post(
        reverse("admin:catalog_exercise_add"),
        {"name": "Розтяжка", "description": "", "category": ExerciseCategory.YOGA},
    )
    assert response.status_code == 302
    exercise = Exercise.objects.get(name="Розтяжка")
    assert exercise.met_activity_description is None
