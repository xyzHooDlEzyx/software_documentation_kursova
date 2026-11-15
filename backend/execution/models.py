from decimal import Decimal

from django.db import models
from django.db.models import F
from django.utils import timezone

from catalog.models import ExerciseCategory


class MissingCalorieReason(models.TextChoices):
    MISSING_WEIGHT = "missing_weight", "Відсутня вага"
    MISSING_MET = "missing_met", "Відсутній MET"
    UNSUPPORTED_AGE = (
        "unsupported_age_for_reference",
        "Вік не підтримується довідником",
    )


class CompletedSession(models.Model):
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="completed_sessions"
    )
    scheduled_session = models.ForeignKey(
        "planning.ScheduledSession",
        on_delete=models.SET_NULL,
        related_name="completed_sessions",
        null=True,
        blank=True,
        db_index=False,
    )
    source_workout = models.ForeignKey(
        "catalog.Workout",
        on_delete=models.PROTECT,
        related_name="completed_sessions",
    )
    source_workout_id_snapshot = models.BigIntegerField()
    source_workout_name_snapshot = models.CharField(max_length=160)
    performed_workout_name_snapshot = models.CharField(max_length=160)
    performed_workout_category_snapshot = models.CharField(
        max_length=24, choices=ExerciseCategory.choices
    )
    source_program_template_id_snapshot = models.BigIntegerField(null=True, blank=True)
    source_program_template_name_snapshot = models.CharField(
        max_length=160, null=True, blank=True
    )
    user_program_id_snapshot = models.BigIntegerField(null=True, blank=True)
    user_program_name_snapshot = models.CharField(max_length=160, null=True, blank=True)
    completed_at = models.DateTimeField(default=timezone.now)
    duration_min = models.DecimalField(max_digits=7, decimal_places=2)
    weight_kg_snapshot = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True
    )
    weight_entry_id_snapshot = models.BigIntegerField(null=True, blank=True)
    workout_met_value_snapshot = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    workout_met_activity_code_snapshot = models.CharField(
        max_length=5, null=True, blank=True
    )
    workout_met_reference_version_snapshot = models.CharField(
        max_length=40, null=True, blank=True
    )
    workout_met_description_snapshot = models.TextField(null=True, blank=True)
    estimated_calories = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    missing_calorie_reason = models.CharField(
        max_length=40, choices=MissingCalorieReason.choices, null=True, blank=True
    )
    idempotency_key = models.CharField(max_length=100)
    request_payload_sha256 = models.CharField(max_length=64)

    class Meta:
        db_table = "completed_sessions"
        ordering = ["-completed_at", "-id"]
        indexes = [
            models.Index(
                fields=["user", "-completed_at", "-id"], name="cs_user_time_idx"
            ),
            models.Index(
                fields=["source_workout", "completed_at"], name="cs_workout_time_idx"
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "idempotency_key"], name="cs_user_idem_uq"
            ),
            models.UniqueConstraint(fields=["scheduled_session"], name="cs_slot_uq"),
            models.CheckConstraint(
                condition=models.Q(duration_min__gt=Decimal("0"))
                & models.Q(duration_min__lte=Decimal("300")),
                name="cs_duration_range",
            ),
            models.CheckConstraint(
                condition=models.Q(estimated_calories__isnull=True)
                | models.Q(estimated_calories__gte=Decimal("0")),
                name="cs_calories_nonneg",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        source_program_template_id_snapshot__isnull=True,
                        source_program_template_name_snapshot__isnull=True,
                        user_program_id_snapshot__isnull=True,
                        user_program_name_snapshot__isnull=True,
                    )
                    | models.Q(
                        source_program_template_id_snapshot__isnull=False,
                        source_program_template_name_snapshot__isnull=False,
                        user_program_id_snapshot__isnull=False,
                        user_program_name_snapshot__isnull=False,
                    )
                ),
                name="cs_program_ctx_all",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        estimated_calories__isnull=True,
                        missing_calorie_reason__isnull=False,
                    )
                    | models.Q(
                        estimated_calories__isnull=False,
                        missing_calorie_reason__isnull=True,
                    )
                ),
                name="cs_calorie_state",
            ),
            models.CheckConstraint(
                condition=models.Q(source_workout_id_snapshot=F("source_workout_id")),
                name="cs_source_snapshot",
            ),
            models.CheckConstraint(
                condition=~models.Q(idempotency_key=""), name="cs_idem_nonempty"
            ),
            models.CheckConstraint(
                condition=models.Q(request_payload_sha256__regex=r"^[0-9a-f]{64}$"),
                name="cs_hash_format",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    performed_workout_category_snapshot__in=ExerciseCategory.values
                ),
                name="cs_category_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(missing_calorie_reason__isnull=True)
                | models.Q(missing_calorie_reason__in=MissingCalorieReason.values),
                name="cs_reason_valid",
            ),
        ]


class ExerciseResult(models.Model):
    completed_session = models.ForeignKey(
        CompletedSession, on_delete=models.CASCADE, related_name="exercise_results"
    )
    source_exercise = models.ForeignKey(
        "catalog.Exercise",
        on_delete=models.PROTECT,
        related_name="exercise_results",
    )
    source_exercise_id_snapshot = models.BigIntegerField()
    exercise_name_snapshot = models.CharField(max_length=160)
    exercise_category_snapshot = models.CharField(
        max_length=24, choices=ExerciseCategory.choices
    )
    position = models.PositiveSmallIntegerField()
    actual_sets = models.PositiveSmallIntegerField(null=True, blank=True)
    actual_reps = models.PositiveSmallIntegerField(null=True, blank=True)
    actual_load_kg = models.DecimalField(
        max_digits=6, decimal_places=1, null=True, blank=True
    )
    actual_duration_min = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True
    )
    actual_distance_km = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True
    )
    met_value_snapshot = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    met_activity_code_snapshot = models.CharField(max_length=5, null=True, blank=True)
    met_reference_version_snapshot = models.CharField(
        max_length=40, null=True, blank=True
    )
    met_activity_description_snapshot = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "exercise_results"
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["completed_session", "position"], name="er_session_pos_uq"
            ),
            models.CheckConstraint(
                condition=models.Q(position__gt=0), name="er_position_pos"
            ),
            models.CheckConstraint(
                condition=models.Q(source_exercise_id_snapshot=F("source_exercise_id")),
                name="er_source_snapshot",
            ),
            models.CheckConstraint(
                condition=models.Q(actual_sets__isnull=True)
                | models.Q(actual_sets__gt=0),
                name="er_sets_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(actual_reps__isnull=True)
                | models.Q(actual_reps__gt=0),
                name="er_reps_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(actual_load_kg__isnull=True)
                | models.Q(actual_load_kg__gte=0),
                name="er_load_nonneg",
            ),
            models.CheckConstraint(
                condition=models.Q(actual_duration_min__isnull=True)
                | models.Q(actual_duration_min__gt=0),
                name="er_duration_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(actual_distance_km__isnull=True)
                | models.Q(actual_distance_km__gt=0),
                name="er_distance_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(met_value_snapshot__isnull=True)
                | models.Q(met_value_snapshot__gt=0),
                name="er_met_pos",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    exercise_category_snapshot__in=ExerciseCategory.values
                ),
                name="er_category_valid",
            ),
        ]
