from datetime import timezone as dt_timezone
from decimal import Decimal

from rest_framework import serializers

from accounts.serializers import (
    StrictDecimalField,
    StrictIntegerField,
    StrictSerializer,
)


class DecimalStringField(StrictDecimalField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        return super().to_internal_value(data)


class ExerciseResultInputSerializer(StrictSerializer):
    position = StrictIntegerField(min_value=1, max_value=32767)
    exercise_id = StrictIntegerField(min_value=1)
    actual_sets = StrictIntegerField(min_value=1, max_value=32767, allow_null=True)
    actual_reps = StrictIntegerField(min_value=1, max_value=32767, allow_null=True)
    actual_load_kg = DecimalStringField(
        max_digits=6, decimal_places=1, min_value=Decimal("0.0"), allow_null=True
    )
    actual_duration_min = DecimalStringField(
        max_digits=7, decimal_places=2, min_value=Decimal("0.01"), allow_null=True
    )
    actual_distance_km = DecimalStringField(
        max_digits=8, decimal_places=3, min_value=Decimal("0.001"), allow_null=True
    )


class WorkoutCompletionRequestSerializer(StrictSerializer):
    scheduled_session_id = StrictIntegerField(
        min_value=1, required=False, allow_null=True
    )
    source_workout_id = StrictIntegerField(min_value=1, required=False, allow_null=True)
    duration_min = DecimalStringField(
        max_digits=7,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=Decimal("300.00"),
    )
    results = serializers.ListField(
        child=ExerciseResultInputSerializer(), min_length=1, max_length=100
    )

    def validate(self, attrs):
        if (attrs.get("scheduled_session_id") is None) == (
            attrs.get("source_workout_id") is None
        ):
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        "Потрібно передати рівно одне джерело завершення."
                    ]
                }
            )
        positions = [item["position"] for item in attrs["results"]]
        if len(positions) != len(set(positions)):
            raise serializers.ValidationError(
                {"results": ["Позиції фактичних результатів не можуть дублюватися."]}
            )
        return attrs


class WorkoutCompletionResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    scheduled_session_id = serializers.IntegerField(read_only=True, allow_null=True)
    source_workout_id = serializers.IntegerField(read_only=True)
    completed_at = serializers.DateTimeField(
        format="%Y-%m-%dT%H:%M:%SZ", default_timezone=dt_timezone.utc, read_only=True
    )
    duration_min = serializers.DecimalField(
        max_digits=7, decimal_places=2, coerce_to_string=True, read_only=True
    )
    estimated_calories = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        coerce_to_string=True,
        allow_null=True,
        read_only=True,
    )
    missing_calorie_reason = serializers.CharField(allow_null=True, read_only=True)
    workout_points = serializers.IntegerField(read_only=True)
    program = serializers.DictField(allow_null=True, read_only=True)
