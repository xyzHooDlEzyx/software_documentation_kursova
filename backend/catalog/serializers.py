"""Serializers for the shared catalog REST API (C01–C04)."""

from rest_framework import serializers

from accounts.serializers import StrictIntegerField, StrictSerializer

from .models import Exercise, ExerciseCategory, Workout, WorkoutExercise


class EmptyQuerySerializer(StrictSerializer):
    """Rejects unexpected query parameters on endpoints taking no query params."""


class CatalogListQuerySerializer(StrictSerializer):
    """Query parameter validation for C02 (/exercises/) and C03 (/workouts/)."""

    category = serializers.ChoiceField(choices=ExerciseCategory.choices, required=False)
    search = serializers.CharField(
        max_length=160,
        required=False,
        allow_blank=True,
        trim_whitespace=False,
    )
    page = StrictIntegerField(min_value=1, required=False, default=1)
    page_size = StrictIntegerField(
        min_value=1, max_value=100, required=False, default=20
    )


class CategoryItemSerializer(serializers.Serializer):
    """Read-only category item representation for C01."""

    code = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)


class ExerciseSerializer(serializers.ModelSerializer):
    """Read-only catalog exercise representation for C02."""

    met_value = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        coerce_to_string=True,
        allow_null=True,
        read_only=True,
    )

    class Meta:
        model = Exercise
        fields = (
            "id",
            "name",
            "description",
            "category",
            "met_value",
            "met_activity_code",
            "met_reference_version",
            "met_activity_description",
        )
        read_only_fields = fields


class WorkoutSummarySerializer(serializers.ModelSerializer):
    """Read-only workout summary representation for C03."""

    exercise_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Workout
        fields = ("id", "name", "description", "category", "exercise_count")
        read_only_fields = fields


class WorkoutExerciseNestedExerciseSerializer(serializers.ModelSerializer):
    """Compact nested exercise representation inside C04 workout details."""

    class Meta:
        model = Exercise
        fields = ("id", "name", "category")
        read_only_fields = fields


class WorkoutExerciseItemSerializer(serializers.ModelSerializer):
    """Ordered workout exercise item representation for C04."""

    entry_id = serializers.IntegerField(source="id", read_only=True)
    exercise = WorkoutExerciseNestedExerciseSerializer(read_only=True)
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
        model = WorkoutExercise
        fields = (
            "entry_id",
            "position",
            "exercise",
            "recommended_sets",
            "recommended_reps",
            "recommended_load_kg",
            "recommended_duration_min",
            "recommended_distance_km",
        )
        read_only_fields = fields


class WorkoutDetailSerializer(serializers.ModelSerializer):
    """Full read-only workout detail representation with ordered exercises for C04."""

    exercises = WorkoutExerciseItemSerializer(
        source="workout_exercises", many=True, read_only=True
    )

    class Meta:
        model = Workout
        fields = ("id", "name", "description", "category", "exercises")
        read_only_fields = fields
