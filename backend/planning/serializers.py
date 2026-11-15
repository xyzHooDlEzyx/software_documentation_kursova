"""Serializers for personal programs, scheduling, and reminders."""

from datetime import timezone as dt_timezone
from decimal import Decimal
from typing import Any

from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from accounts.serializers import (
    StrictDecimalField,
    StrictIntegerField,
    StrictSerializer,
)

from .models import (
    Notification,
    NotificationStatus,
    NotificationType,
    ScheduledSession,
    ScheduledSessionStatus,
    UserProgram,
    UserProgramExercise,
    UserProgramStatus,
    UserProgramWorkout,
)
from .policies import format_utc_seconds
from .selectors import program_progress


def _bonus_earned(obj: UserProgram) -> bool:
    from engagement.models import PointKind

    return obj.point_transactions.filter(
        point_kind=PointKind.PROGRAM_COMPLETION
    ).exists()


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
        return program_progress(obj)["percent"]

    def get_bonus_earned(self, obj: UserProgram) -> bool:
        return _bonus_earned(obj)


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
        return program_progress(obj)

    def get_completion_snapshot(self, obj: UserProgram) -> dict[str, Any] | None:
        if obj.status == UserProgramStatus.COMPLETED:
            return {
                "completed_at": format_utc_seconds(obj.completed_at),
                "total_planned_at_completion": obj.total_planned_at_completion,
                "completed_planned_at_completion": obj.completed_planned_at_completion,
                "progress_percent_at_completion": str(
                    obj.progress_percent_at_completion
                ),
            }
        return None

    def get_bonus_earned(self, obj: UserProgram) -> bool:
        return _bonus_earned(obj)


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


# PostgreSQL column limits: positions/sets/reps are ``smallint`` and IDs are
# ``bigint``. Validating them here returns 400 instead of a DataError (500).
SMALLINT_MAX = 32767
BIGINT_MAX = 9223372036854775807
MAX_WORKOUT_EXERCISES = 100


class UpdateWorkoutExerciseItemSerializer(StrictSerializer):
    position = StrictIntegerField(min_value=1, max_value=SMALLINT_MAX)
    exercise_id = StrictIntegerField(min_value=1, max_value=BIGINT_MAX)
    recommended_sets = StrictIntegerField(
        min_value=1, max_value=SMALLINT_MAX, required=True, allow_null=True
    )
    recommended_reps = StrictIntegerField(
        min_value=1, max_value=SMALLINT_MAX, required=True, allow_null=True
    )
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
        max_length=MAX_WORKOUT_EXERCISES,
    )

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError(
                "Назва тренування не може бути порожньою."
            )
        return cleaned


class EmptyBodySerializer(StrictSerializer):
    pass


class ActivateProgramResponseSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()
    activated_at = serializers.DateTimeField(
        format="%Y-%m-%dT%H:%M:%SZ", default_timezone=dt_timezone.utc, read_only=True
    )

    class Meta:
        model = UserProgram
        fields = (
            "id",
            "status",
            "is_archived",
            "activated_at",
            "bonus_target_sessions",
            "progress",
        )
        read_only_fields = fields

    def get_progress(self, obj: UserProgram) -> dict[str, Any]:
        return program_progress(obj)


class ProgramProgressSerializer(serializers.ModelSerializer):
    user_program_id = serializers.IntegerField(source="id", read_only=True)
    total_planned = serializers.SerializerMethodField()
    completed_planned = serializers.SerializerMethodField()
    percent = serializers.SerializerMethodField()
    bonus_earned = serializers.SerializerMethodField()
    completion_snapshot = serializers.SerializerMethodField()

    class Meta:
        model = UserProgram
        fields = (
            "user_program_id",
            "status",
            "is_archived",
            "total_planned",
            "completed_planned",
            "percent",
            "bonus_target_sessions",
            "bonus_earned",
            "completion_snapshot",
        )
        read_only_fields = fields

    def get_total_planned(self, obj):
        return program_progress(obj)["total_planned"]

    def get_completed_planned(self, obj):
        return program_progress(obj)["completed_planned"]

    def get_percent(self, obj):
        return program_progress(obj)["percent"]

    def get_bonus_earned(self, obj):
        return _bonus_earned(obj)

    def get_completion_snapshot(self, obj):
        return UserProgramDetailSerializer().get_completion_snapshot(obj)


class AwareDateTimeField(serializers.DateTimeField):
    def to_internal_value(self, value):
        if not isinstance(value, str):
            self.fail("invalid", format="ISO 8601")
        try:
            parsed = parse_datetime(value)
        except ValueError, OverflowError:
            self.fail("invalid", format="ISO 8601")
        if parsed is not None and parsed.tzinfo is None:
            raise serializers.ValidationError(
                "Час має містити часовий пояс або суфікс Z."
            )
        return super().to_internal_value(value)


class ScheduledSessionQuerySerializer(StrictSerializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    status = serializers.ChoiceField(
        choices=ScheduledSessionStatus.choices, required=False
    )
    user_program_id = StrictIntegerField(min_value=1, required=False)
    page = StrictIntegerField(min_value=1, required=False, default=1)
    page_size = StrictIntegerField(
        min_value=1, max_value=100, required=False, default=20
    )

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if (start_date is None) != (end_date is None):
            missing = "start_date" if start_date is None else "end_date"
            raise serializers.ValidationError(
                {missing: ["start_date і end_date потрібно передавати разом."]}
            )
        if start_date is not None and start_date >= end_date:
            raise serializers.ValidationError(
                {"end_date": ["end_date має бути пізніше за start_date."]}
            )
        return attrs


class CreateScheduledSessionSerializer(StrictSerializer):
    user_program_workout_id = StrictIntegerField(
        min_value=1, required=False, allow_null=True
    )
    source_workout_id = StrictIntegerField(min_value=1, required=False, allow_null=True)
    scheduled_at = AwareDateTimeField()

    def validate(self, attrs):
        program_workout_id = attrs.get("user_program_workout_id")
        source_workout_id = attrs.get("source_workout_id")
        if (program_workout_id is None) == (source_workout_id is None):
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        "Потрібно передати рівно одне з user_program_workout_id "
                        "або source_workout_id."
                    ]
                }
            )
        return attrs


class RescheduleSessionSerializer(StrictSerializer):
    scheduled_at = AwareDateTimeField()


class StrictBooleanQueryField(serializers.ChoiceField):
    def __init__(self, **kwargs):
        super().__init__(choices=("true", "false"), **kwargs)

    def to_internal_value(self, data):
        return super().to_internal_value(data) == "true"


class ReminderSerializer(serializers.ModelSerializer):
    visible_at = serializers.DateTimeField(
        format="%Y-%m-%dT%H:%M:%SZ", default_timezone=dt_timezone.utc, read_only=True
    )
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ("id", "visible_at", "status", "is_current")
        read_only_fields = fields

    def get_is_current(self, obj):
        session_status = self.context.get("scheduled_session_status")
        if session_status is not None:
            return session_status == ScheduledSessionStatus.PLANNED
        return obj.is_current


class ScheduledSessionSummarySerializer(serializers.ModelSerializer):
    scheduled_at = serializers.DateTimeField(
        format="%Y-%m-%dT%H:%M:%SZ", default_timezone=dt_timezone.utc, read_only=True
    )
    is_missed = serializers.BooleanField(read_only=True)

    class Meta:
        model = ScheduledSession
        fields = (
            "id",
            "scheduled_at",
            "status",
            "is_missed",
            "user_program_id",
            "user_program_workout_id",
            "source_workout_id",
        )
        read_only_fields = fields


def _serialized_session_reminder(obj: ScheduledSession) -> dict[str, Any]:
    reminder = next(
        (
            item
            for item in obj.notifications.all()
            if item.type == NotificationType.WORKOUT_REMINDER
        ),
        None,
    )
    return ReminderSerializer(
        reminder, context={"scheduled_session_status": obj.status}
    ).data


class ScheduledSessionDetailSerializer(ScheduledSessionSummarySerializer):
    reschedule_history = serializers.ListField(read_only=True)
    completed_session_id = serializers.SerializerMethodField()
    reminder = serializers.SerializerMethodField()

    class Meta(ScheduledSessionSummarySerializer.Meta):
        fields = ScheduledSessionSummarySerializer.Meta.fields + (
            "reschedule_history",
            "completed_session_id",
            "reminder",
        )

    def get_completed_session_id(self, obj):
        return None

    def get_reminder(self, obj):
        return _serialized_session_reminder(obj)


class CreatedScheduledSessionResponseSerializer(ScheduledSessionSummarySerializer):
    reschedule_history = serializers.ListField(read_only=True)
    reminder = serializers.SerializerMethodField()

    class Meta(ScheduledSessionSummarySerializer.Meta):
        fields = ScheduledSessionSummarySerializer.Meta.fields + (
            "reschedule_history",
            "reminder",
        )

    def get_reminder(self, obj):
        return _serialized_session_reminder(obj)


class RescheduledSessionResponseSerializer(serializers.ModelSerializer):
    scheduled_at = serializers.DateTimeField(
        format="%Y-%m-%dT%H:%M:%SZ", default_timezone=dt_timezone.utc, read_only=True
    )
    is_missed = serializers.BooleanField(read_only=True)
    reminder = serializers.SerializerMethodField()

    class Meta:
        model = ScheduledSession
        fields = (
            "id",
            "scheduled_at",
            "status",
            "is_missed",
            "reschedule_history",
            "reminder",
        )
        read_only_fields = fields

    def get_reminder(self, obj):
        return _serialized_session_reminder(obj)


class CancelledSessionResponseSerializer(serializers.ModelSerializer):
    reminder = serializers.SerializerMethodField()

    class Meta:
        model = ScheduledSession
        fields = ("id", "status", "reminder")
        read_only_fields = fields

    def get_reminder(self, obj):
        data = _serialized_session_reminder(obj)
        return {key: data[key] for key in ("id", "status", "is_current")}


class ArchiveProgramResponseSerializer(serializers.ModelSerializer):
    bonus_earned = serializers.SerializerMethodField()

    class Meta:
        model = UserProgram
        fields = ("id", "status", "is_archived", "bonus_earned")
        read_only_fields = fields

    def get_bonus_earned(self, obj):
        return _bonus_earned(obj)


class NotificationQuerySerializer(StrictSerializer):
    status = serializers.ChoiceField(
        choices=[NotificationStatus.PENDING, NotificationStatus.READ], required=False
    )
    is_current = StrictBooleanQueryField(required=False)
    page = StrictIntegerField(min_value=1, required=False, default=1)
    page_size = StrictIntegerField(
        min_value=1, max_value=100, required=False, default=20
    )


class NotificationSerializer(serializers.ModelSerializer):
    visible_at = serializers.DateTimeField(
        format="%Y-%m-%dT%H:%M:%SZ", default_timezone=dt_timezone.utc, read_only=True
    )
    read_at = serializers.DateTimeField(
        format="%Y-%m-%dT%H:%M:%SZ",
        default_timezone=dt_timezone.utc,
        allow_null=True,
        read_only=True,
    )
    is_current = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "scheduled_session_id",
            "type",
            "visible_at",
            "status",
            "read_at",
            "is_current",
        )
        read_only_fields = fields
