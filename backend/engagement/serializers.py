from datetime import timezone as dt_timezone

from rest_framework import serializers

from accounts.serializers import StrictIntegerField, StrictSerializer

from .models import (
    Achievement,
    Challenge,
    ChallengeGoalKind,
    ChallengeParticipation,
    ParticipationStatus,
    PointKind,
    PointTransaction,
    UserAchievement,
)


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


class OptionalPeriodSerializer(StrictSerializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if (start_date is None) != (end_date is None):
            missing = "start_date" if start_date is None else "end_date"
            raise serializers.ValidationError(
                {missing: ["Потрібно передати обидві межі періоду."]}
            )
        if start_date is not None and start_date >= end_date:
            raise serializers.ValidationError(
                {"end_date": ["Кінцева дата має бути пізнішою за початкову."]}
            )
        return attrs


class PointTransactionQuerySerializer(OptionalPeriodSerializer):
    point_kind = serializers.ChoiceField(choices=PointKind.choices, required=False)
    page = StrictIntegerField(min_value=1, default=1)
    page_size = StrictIntegerField(min_value=1, max_value=100, default=20)


class PageQuerySerializer(StrictSerializer):
    page = StrictIntegerField(min_value=1, default=1)
    page_size = StrictIntegerField(min_value=1, max_value=100, default=20)


class ParticipationQuerySerializer(PageQuerySerializer):
    status = serializers.ChoiceField(
        choices=ParticipationStatus.choices, required=False
    )


class PointTransactionSerializer(serializers.ModelSerializer):
    awarded_at = serializers.DateTimeField(
        format="%Y-%m-%dT%H:%M:%SZ", default_timezone=dt_timezone.utc
    )
    source = serializers.SerializerMethodField()

    def get_source(self, obj):
        if obj.completed_session_id is not None:
            return {"kind": "completed_session", "id": obj.completed_session_id}
        return {"kind": "user_program", "id": obj.user_program_id}

    class Meta:
        model = PointTransaction
        fields = ("id", "point_kind", "points", "awarded_at", "source")


class AchievementSerializer(serializers.ModelSerializer):
    earned = serializers.BooleanField(read_only=True)

    class Meta:
        model = Achievement
        fields = ("id", "code", "name", "description", "earned")


class UserAchievementSerializer(serializers.ModelSerializer):
    achievement_id = serializers.IntegerField(read_only=True)
    unlocked_at = serializers.DateTimeField(
        format="%Y-%m-%dT%H:%M:%SZ", default_timezone=dt_timezone.utc
    )

    class Meta:
        model = UserAchievement
        fields = (
            "id",
            "achievement_id",
            "rule_code_snapshot",
            "name_snapshot",
            "unlocked_at",
        )


class ChallengeParticipationHistorySerializer(ChallengeParticipationSerializer):
    challenge_name = serializers.CharField(source="challenge.name", read_only=True)
    goal_kind = serializers.CharField(source="challenge.goal_kind", read_only=True)
    completed_at = serializers.DateTimeField(
        format="%Y-%m-%dT%H:%M:%SZ", default_timezone=dt_timezone.utc, allow_null=True
    )

    class Meta(ChallengeParticipationSerializer.Meta):
        fields = (
            "id",
            "challenge_id",
            "challenge_name",
            "joined_at",
            "status",
            "goal_kind",
            "goal_value",
            "progress_value",
            "completed_at",
        )
