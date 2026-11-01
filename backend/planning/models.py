"""Models for personal program planning (Phase 4).

Entities:
- UserProgram: independent personal copy of a program template.
- UserProgramWorkout: personal workout entry preserving source workout origin.
- UserProgramExercise: personal exercise recommendations independent of shared catalog.
"""

from decimal import Decimal

from django.db import models
from django.utils import timezone

from accounts.models import FitnessGoal
from catalog.models import ExerciseCategory


class UserProgramStatus(models.TextChoices):
    DRAFT = "draft", "Чернетка"
    ACTIVE = "active", "Активна"
    COMPLETED = "completed", "Завершена"


class UserProgram(models.Model):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="user_programs",
    )
    source_program_template = models.ForeignKey(
        "catalog.ProgramTemplate",
        on_delete=models.PROTECT,
        related_name="user_programs",
    )
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True, default="", db_default="")
    fitness_goal = models.CharField(max_length=20, choices=FitnessGoal.choices)
    status = models.CharField(
        max_length=12,
        choices=UserProgramStatus.choices,
        default=UserProgramStatus.DRAFT,
        db_default="draft",
    )
    is_archived = models.BooleanField(default=False, db_default=False)
    source_program_template_name_snapshot = models.CharField(max_length=160)
    bonus_target_sessions = models.PositiveSmallIntegerField(null=True, blank=True)
    total_planned_at_completion = models.PositiveIntegerField(null=True, blank=True)
    completed_planned_at_completion = models.PositiveIntegerField(null=True, blank=True)
    progress_percent_at_completion = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    activated_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "user_programs"
        ordering = ["-id"]
        indexes = [
            models.Index(
                fields=["user", "is_archived", "status", "id"],
                name="user_prog_user_arch_stat_idx",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=UserProgramStatus.values),
                name="user_programs_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(fitness_goal__in=FitnessGoal.values),
                name="user_programs_goal_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status=UserProgramStatus.DRAFT, activated_at__isnull=True
                )
                | models.Q(
                    status__in=[
                        UserProgramStatus.ACTIVE,
                        UserProgramStatus.COMPLETED,
                    ],
                    activated_at__isnull=False,
                ),
                name="user_programs_activation_state",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    activated_at__isnull=True, bonus_target_sessions__isnull=True
                )
                | (
                    models.Q(activated_at__isnull=False)
                    & models.Q(bonus_target_sessions__gte=3)
                ),
                name="user_programs_bonus_target_state",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    completed_at__isnull=True,
                    total_planned_at_completion__isnull=True,
                    completed_planned_at_completion__isnull=True,
                    progress_percent_at_completion__isnull=True,
                )
                | models.Q(
                    completed_at__isnull=False,
                    total_planned_at_completion__isnull=False,
                    completed_planned_at_completion__isnull=False,
                    progress_percent_at_completion__isnull=False,
                ),
                name="user_programs_snapshot_all_or_none",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status=UserProgramStatus.COMPLETED, completed_at__isnull=False
                )
                | (
                    ~models.Q(status=UserProgramStatus.COMPLETED)
                    & models.Q(completed_at__isnull=True)
                ),
                name="user_programs_completion_state",
            ),
            models.CheckConstraint(
                condition=~models.Q(status=UserProgramStatus.COMPLETED)
                | (
                    models.Q(total_planned_at_completion__gt=0)
                    & models.Q(
                        completed_planned_at_completion=models.F(
                            "total_planned_at_completion"
                        )
                    )
                    & models.Q(progress_percent_at_completion=Decimal("100.0"))
                ),
                name="user_programs_completion_values",
            ),
        ]

    def __str__(self) -> str:
        return f"UserProgram(id={self.pk}, user={self.user_id}, status={self.status})"


class UserProgramWorkout(models.Model):
    user_program = models.ForeignKey(
        "planning.UserProgram",
        on_delete=models.CASCADE,
        related_name="workouts",
    )
    source_workout = models.ForeignKey(
        "catalog.Workout",
        on_delete=models.PROTECT,
        related_name="user_program_workouts",
    )
    position = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=160)
    category = models.CharField(max_length=24, choices=ExerciseCategory.choices)

    class Meta:
        db_table = "user_program_workouts"
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user_program", "position"],
                name="up_workouts_prog_pos_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(position__gt=0),
                name="up_workouts_pos_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(category__in=ExerciseCategory.values),
                name="up_workouts_cat_valid",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"UserProgramWorkout(program={self.user_program_id}, "
            f"pos={self.position}, name={self.name})"
        )


class UserProgramExercise(models.Model):
    user_program_workout = models.ForeignKey(
        "planning.UserProgramWorkout",
        on_delete=models.CASCADE,
        related_name="exercises",
    )
    exercise = models.ForeignKey(
        "catalog.Exercise",
        on_delete=models.PROTECT,
        related_name="user_program_exercises",
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
        db_table = "user_program_exercises"
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user_program_workout", "position"],
                name="up_exercises_workout_pos_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(position__gt=0),
                name="up_exercises_pos_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(recommended_sets__isnull=True)
                | models.Q(recommended_sets__gt=0),
                name="up_exercises_sets_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(recommended_reps__isnull=True)
                | models.Q(recommended_reps__gt=0),
                name="up_exercises_reps_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(recommended_load_kg__isnull=True)
                | models.Q(recommended_load_kg__gte=Decimal("0.0")),
                name="up_exercises_load_nonneg",
            ),
            models.CheckConstraint(
                condition=models.Q(recommended_duration_min__isnull=True)
                | models.Q(recommended_duration_min__gt=Decimal("0.00")),
                name="up_exercises_dur_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(recommended_distance_km__isnull=True)
                | models.Q(recommended_distance_km__gt=Decimal("0.000")),
                name="up_exercises_dist_pos",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"UserProgramExercise(upw={self.user_program_workout_id}, "
            f"pos={self.position}, ex={self.exercise_id})"
        )
