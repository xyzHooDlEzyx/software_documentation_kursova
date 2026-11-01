"""Serializers for personal program selection and planning REST API (G01–G06)."""

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from accounts.serializers import (
    StrictDecimalField,
    StrictIntegerField,
    StrictSerializer,
)

from .models import (
    UserProgram,
    UserProgramExercise,
    UserProgramStatus,
    UserProgramWorkout,
)


class TemplateWorkoutSummarySerializer(serializers.Serializer):
    position = serializers.IntegerField(read_only=True)
    workout_id = serializers.IntegerField(source="workout.id", read_only=True)
    name = serializers.CharField(source="workout.name", read_only=True)


class TemplateRecommendationItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    fitness_goal = serializers.CharField(read_only=True)
    experience_level = serializers.CharField(read_only=True)
    workouts_per_week = serializers.IntegerField(read_only=True)
    workouts = TemplateWorkoutSummarySerializer(
        source="program_template_workouts", many=True, read_only=True
    )


class RecommendationReasonSerializer(serializers.Serializer):
    exact_goal = serializers.BooleanField(read_only=True)
    exact_level = serializers.BooleanField(read_only=True)
    frequency_difference = serializers.IntegerField(read_only=True)
    strategy = serializers.CharField(read_only=True)
    composition_criterion = serializers.CharField(read_only=True)


class ProgramRecommendationResponseSerializer(serializers.Serializer):
    program_template = TemplateRecommendationItemSerializer(read_only=True)
    reason = RecommendationReasonSerializer(read_only=True)


class ProgramListQuerySerializer(StrictSerializer):
    status = serializers.ChoiceField(choices=UserProgramStatus.choices, required=False)
    archived = serializers.BooleanField(required=False, default=False)
    page = StrictIntegerField(min_value=1, required=False, default=1)
    page_size = StrictIntegerField(
        min_value=1, max_value=100, required=False, default=20
    )


class UserProgramSummarySerializer(serializers.ModelSerializer):
    progress_percent = serializers.SerializerMethodField()
    bonus_earned = serializers.SerializerMethodField()

    class Meta:
        model = UserProgram
        fields = (
            "id",
            "name",
            "status",
            "is_archived",
            "source_program_template_id",
            "progress_percent",
            "bonus_earned",
        )
        read_only_fields = fields

    def get_progress_percent(self, obj: UserProgram) -> str:
        # In Phase 4, no scheduled sessions exist yet; draft progress is 0.0%
        return "0.0"

    def get_bonus_earned(self, obj: UserProgram) -> bool:
        # BonusPointLedger is introduced in a later phase.
        return False


class CreateUserProgramRequestSerializer(StrictSerializer):
    program_template_id = StrictIntegerField(min_value=1)


class UserProgramExerciseItemSerializer(serializers.ModelSerializer):
    recommended_load_kg = serializers.DecimalField(
        max_digits=6,
        decimal_places=1,
        coerce_to_string=True,
        allow_null=True,
        read_only=True,
    )
    recommended_duration_min = serializers.DecimalField(
        max_digits=7,
        decimal_places=2,
        coerce_to_string=True,
        allow_null=True,
        read_only=True,
    )
    recommended_distance_km = serializers.DecimalField(
        max_digits=8,
        decimal_places=3,
        coerce_to_string=True,
        allow_null=True,
        read_only=True,
    )

    class Meta:
        model = UserProgramExercise
        fields = (
            "position",
            "exercise_id",
            "recommended_sets",
            "recommended_reps",
            "recommended_load_kg",
            "recommended_duration_min",
            "recommended_distance_km",
        )
        read_only_fields = fields


class UserProgramWorkoutItemSerializer(serializers.ModelSerializer):
    entry_id = serializers.IntegerField(source="id", read_only=True)
    exercises = UserProgramExerciseItemSerializer(many=True, read_only=True)

    class Meta:
        model = UserProgramWorkout
        fields = (
            "entry_id",
            "position",
            "source_workout_id",
            "name",
            "category",
            "exercises",
        )
        read_only_fields = fields


class UserProgramDetailSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()
    completion_snapshot = serializers.SerializerMethodField()
    bonus_earned = serializers.SerializerMethodField()
    workouts = UserProgramWorkoutItemSerializer(many=True, read_only=True)

    class Meta:
        model = UserProgram
        fields = (
            "id",
            "name",
            "description",
            "fitness_goal",
            "status",
            "is_archived",
            "source_program_template_id",
            "source_program_template_name_snapshot",
            "bonus_target_sessions",
            "progress",
            "completion_snapshot",
            "bonus_earned",
            "workouts",
        )
        read_only_fields = fields

    def get_progress(self, obj: UserProgram) -> dict[str, Any]:
        return {
            "total_planned": 0,
            "completed_planned": 0,
            "percent": "0.0",
        }

    def get_completion_snapshot(self, obj: UserProgram) -> dict[str, Any] | None:
        if obj.status == UserProgramStatus.COMPLETED:
            return {
                "completed_at": obj.completed_at.isoformat(),
                "total_planned_at_completion": obj.total_planned_at_completion,
                "completed_planned_at_completion": obj.completed_planned_at_completion,
                "progress_percent_at_completion": str(
                    obj.progress_percent_at_completion
                ),
            }
        return None

    def get_bonus_earned(self, obj: UserProgram) -> bool:
        return False


class UpdateUserProgramRequestSerializer(StrictSerializer):
    name = serializers.CharField(max_length=160, required=False)
    description = serializers.CharField(
        required=False, allow_blank=True, trim_whitespace=False
    )

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Назва програми не може бути порожньою.")
        return cleaned


class UpdateUserProgramResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProgram
        fields = ("id", "name", "description", "status", "is_archived")
        read_only_fields = fields


class UpdateWorkoutExerciseItemSerializer(StrictSerializer):
    position = StrictIntegerField(min_value=1)
    exercise_id = StrictIntegerField(min_value=1)
    recommended_sets = StrictIntegerField(min_value=1, required=True, allow_null=True)
    recommended_reps = StrictIntegerField(min_value=1, required=True, allow_null=True)
    recommended_load_kg = StrictDecimalField(
        min_value=Decimal("0.0"),
        max_digits=6,
        decimal_places=1,
        required=True,
        allow_null=True,
    )
    recommended_duration_min = StrictDecimalField(
        min_value=Decimal("0.01"),
        max_digits=7,
        decimal_places=2,
        required=True,
        allow_null=True,
    )
    recommended_distance_km = StrictDecimalField(
        min_value=Decimal("0.001"),
        max_digits=8,
        decimal_places=3,
        required=True,
        allow_null=True,
    )


class ReplaceWorkoutCompositionRequestSerializer(StrictSerializer):
    name = serializers.CharField(max_length=160)
    exercises = serializers.ListField(
        child=UpdateWorkoutExerciseItemSerializer(),
        min_length=1,
    )

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError(
                "Назва тренування не може бути порожньою."
            )
        return cleaned
