from decimal import Decimal

from django.db import models

from accounts.models import ExperienceLevel, FitnessGoal


class ExerciseCategory(models.TextChoices):
    CARDIO = "cardio", "Кардіо"
    STRENGTH = "strength", "Силові"
    YOGA = "yoga", "Йога"


Category = ExerciseCategory


class ProgramTemplateStatus(models.TextChoices):
    PUBLISHED = "published", "published"
    ARCHIVED = "archived", "archived"


TemplateStatus = ProgramTemplateStatus


def _met_package_consistent_q() -> models.Q:
    all_null = (
        models.Q(met_value__isnull=True)
        & models.Q(met_activity_code__isnull=True)
        & models.Q(met_reference_version__isnull=True)
        & models.Q(met_activity_description__isnull=True)
    )
    all_present = (
        models.Q(met_value__isnull=False)
        & models.Q(met_activity_code__isnull=False)
        & models.Q(met_reference_version__isnull=False)
        & models.Q(met_activity_description__isnull=False)
        & ~models.Q(met_reference_version="")
        & ~models.Q(met_activity_description="")
    )
    return all_null | all_present


class Exercise(models.Model):
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True, default="", db_default="")
    category = models.CharField(max_length=24, choices=ExerciseCategory.choices)
    met_value = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    met_activity_code = models.CharField(max_length=5, null=True, blank=True)
    met_reference_version = models.CharField(max_length=40, null=True, blank=True)
    met_activity_description = models.TextField(null=True, blank=True)
    is_archived = models.BooleanField(default=False, db_default=False)

    class Meta:
        db_table = "exercises"
        ordering = ["name", "id"]
        indexes = [
            models.Index(
                fields=["is_archived", "category", "name"],
                name="exercises_arch_cat_name_idx",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(category__in=ExerciseCategory.values),
                name="exercises_category_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(met_value__isnull=True)
                | models.Q(met_value__gt=Decimal("0.00")),
                name="exercises_met_value_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(met_activity_code__isnull=True)
                | models.Q(met_activity_code__regex=r"^[0-9]{5}$"),
                name="exercises_met_code_format",
            ),
            models.CheckConstraint(
                condition=_met_package_consistent_q(),
                name="exercises_met_pkg_consistent",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Workout(models.Model):
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True, default="", db_default="")
    category = models.CharField(max_length=24, choices=ExerciseCategory.choices)
    met_value = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    met_activity_code = models.CharField(max_length=5, null=True, blank=True)
    met_reference_version = models.CharField(max_length=40, null=True, blank=True)
    met_activity_description = models.TextField(null=True, blank=True)
    is_archived = models.BooleanField(default=False, db_default=False)

    class Meta:
        db_table = "workouts"
        ordering = ["name", "id"]
        indexes = [
            models.Index(
                fields=["is_archived", "category", "name"],
                name="workouts_arch_cat_name_idx",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(category__in=ExerciseCategory.values),
                name="workouts_category_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(met_value__isnull=True)
                | models.Q(met_value__gt=Decimal("0.00")),
                name="workouts_met_value_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(met_activity_code__isnull=True)
                | models.Q(met_activity_code__regex=r"^[0-9]{5}$"),
                name="workouts_met_code_format",
            ),
            models.CheckConstraint(
                condition=_met_package_consistent_q(),
                name="workouts_met_pkg_consistent",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class WorkoutExercise(models.Model):
    workout = models.ForeignKey(
        "catalog.Workout",
        on_delete=models.CASCADE,
        related_name="workout_exercises",
    )
    exercise = models.ForeignKey(
        "catalog.Exercise",
        on_delete=models.PROTECT,
        related_name="workout_exercises",
    )
    position = models.PositiveSmallIntegerField()
    recommended_sets = models.PositiveSmallIntegerField(null=True, blank=True)
    recommended_reps = models.PositiveSmallIntegerField(null=True, blank=True)
    recommended_load_kg = models.DecimalField(
        max_digits=6, decimal_places=1, null=True, blank=True
    )
    recommended_duration_min = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True
    )
    recommended_distance_km = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True
    )

    class Meta:
        db_table = "workout_exercises"
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["workout", "position"],
                name="workout_exercises_workout_pos_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(position__gt=0),
                name="workout_exercises_pos_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(recommended_sets__isnull=True)
                | models.Q(recommended_sets__gt=0),
                name="workout_exercises_sets_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(recommended_reps__isnull=True)
                | models.Q(recommended_reps__gt=0),
                name="workout_exercises_reps_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(recommended_load_kg__isnull=True)
                | models.Q(recommended_load_kg__gte=Decimal("0.0")),
                name="workout_exercises_load_nonneg",
            ),
            models.CheckConstraint(
                condition=models.Q(recommended_duration_min__isnull=True)
                | models.Q(recommended_duration_min__gt=Decimal("0.00")),
                name="workout_exercises_dur_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(recommended_distance_km__isnull=True)
                | models.Q(recommended_distance_km__gt=Decimal("0.000")),
                name="workout_exercises_dist_pos",
            ),
        ]

    def __str__(self) -> str:
        return f"WorkoutExercise(workout={self.workout_id}, pos={self.position})"


class ProgramTemplate(models.Model):
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True, default="", db_default="")
    fitness_goal = models.CharField(max_length=20, choices=FitnessGoal.choices)
    experience_level = models.CharField(max_length=20, choices=ExperienceLevel.choices)
    workouts_per_week = models.PositiveSmallIntegerField()
    status = models.CharField(
        max_length=12,
        choices=ProgramTemplateStatus.choices,
        default=ProgramTemplateStatus.PUBLISHED,
        db_default="published",
    )

    class Meta:
        db_table = "program_templates"
        ordering = ["id"]
        indexes = [
            models.Index(
                fields=["fitness_goal", "experience_level", "workouts_per_week", "id"],
                condition=models.Q(status="published"),
                name="prog_tmpl_pub_lookup_idx",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fitness_goal__in=FitnessGoal.values),
                name="program_templates_goal_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(experience_level__in=ExperienceLevel.values),
                name="program_templates_level_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=ProgramTemplateStatus.values),
                name="program_templates_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(workouts_per_week__gte=1)
                & models.Q(workouts_per_week__lte=7),
                name="program_templates_freq_range",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class ProgramTemplateWorkout(models.Model):
    program_template = models.ForeignKey(
        "catalog.ProgramTemplate",
        on_delete=models.CASCADE,
        related_name="program_template_workouts",
    )
    workout = models.ForeignKey(
        "catalog.Workout",
        on_delete=models.PROTECT,
        related_name="program_template_workouts",
    )
    position = models.PositiveSmallIntegerField()
    suggested_weekday = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = "program_template_workouts"
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["program_template", "position"],
                name="prog_tmpl_workouts_tmpl_pos_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(position__gt=0),
                name="prog_tmpl_workouts_pos_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(suggested_weekday__isnull=True)
                | (
                    models.Q(suggested_weekday__gte=1)
                    & models.Q(suggested_weekday__lte=7)
                ),
                name="prog_tmpl_workouts_weekday_rng",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"ProgramTemplateWorkout("
            f"template={self.program_template_id}, pos={self.position})"
        )
