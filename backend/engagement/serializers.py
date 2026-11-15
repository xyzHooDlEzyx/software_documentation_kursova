from datetime import timezone as dt_timezone

from rest_framework import serializers

from accounts.serializers import StrictIntegerField, StrictSerializer

from .models import Challenge, ChallengeGoalKind, ChallengeParticipation


class ChallengeQuerySerializer(StrictSerializer):
    state = serializers.ChoiceField(choices=("active", "upcoming"), required=False)
    page = StrictIntegerField(min_value=1, required=False, default=1)
    page_size = StrictIntegerField(
        min_value=1, max_value=100, required=False, default=20
    )


class EmptyBodySerializer(StrictSerializer):
    pass


class ChallengeSerializer(serializers.ModelSerializer):
    start_at = serializers.DateTimeField(
        format="%Y-%m-%dT%H:%M:%SZ", default_timezone=dt_timezone.utc
    )
    end_at = serializers.DateTimeField(
        format="%Y-%m-%dT%H:%M:%SZ", default_timezone=dt_timezone.utc
    )
    joined = serializers.BooleanField(read_only=True)

    class Meta:
        model = Challenge
        fields = (
            "id",
            "name",
            "start_at",
            "end_at",
            "goal_kind",
            "goal_value",
            "joined",
        )
        read_only_fields = fields


class ChallengeParticipationSerializer(serializers.ModelSerializer):
    challenge_id = serializers.IntegerField(read_only=True)
    joined_at = serializers.DateTimeField(
        format="%Y-%m-%dT%H:%M:%SZ", default_timezone=dt_timezone.utc
    )
    progress_value = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    goal_value = serializers.IntegerField(source="challenge.goal_value", read_only=True)

    def get_progress_value(self, obj):
        if obj.challenge.goal_kind == ChallengeGoalKind.WORKOUTS:
            return int(getattr(obj, "progress_value", 0))
        return str(getattr(obj, "progress_value", 0))

    def get_status(self, obj):
        return getattr(obj, "effective_status", obj.status)

    class Meta:
        model = ChallengeParticipation
        fields = (
            "id",
            "challenge_id",
            "joined_at",
            "status",
            "progress_value",
            "goal_value",
        )
        read_only_fields = fields
