from django.db import models
from django.utils import timezone


class PointKind(models.TextChoices):
    WORKOUT_COMPLETION = "workout_completion", "Завершення тренування"
    PROGRAM_COMPLETION = "program_completion", "Завершення програми"


class AchievementCode(models.TextChoices):
    FIRST_WORKOUT = "first_workout", "Перше тренування"
    FIVE_WORKOUTS = "five_workouts", "П'ять тренувань"
    ONE_HUNDRED_MINUTES = "one_hundred_minutes", "100 хвилин"
    MARATHONER = "marathoner", "Марафонець"
    HEAVYWEIGHT = "heavyweight", "Важковаговик"


class PointTransaction(models.Model):
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="point_transactions"
    )
    completed_session = models.ForeignKey(
        "execution.CompletedSession",
        on_delete=models.CASCADE,
        related_name="point_transactions",
        null=True,
        blank=True,
    )
    user_program = models.ForeignKey(
        "planning.UserProgram",
        on_delete=models.CASCADE,
        related_name="point_transactions",
        null=True,
        blank=True,
    )
    point_kind = models.CharField(max_length=24, choices=PointKind.choices)
    points = models.IntegerField()
    awarded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "point_transactions"
        ordering = ["awarded_at", "id"]
        indexes = [
            models.Index(fields=["user", "awarded_at", "id"], name="pt_user_time_idx")
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(completed_session__isnull=False, user_program__isnull=True)
                    | models.Q(
                        completed_session__isnull=True, user_program__isnull=False
                    )
                ),
                name="pt_source_xor",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        point_kind=PointKind.WORKOUT_COMPLETION,
                        completed_session__isnull=False,
                        user_program__isnull=True,
                    )
                    | models.Q(
                        point_kind=PointKind.PROGRAM_COMPLETION,
                        completed_session__isnull=True,
                        user_program__isnull=False,
                    )
                ),
                name="pt_kind_source",
            ),
            models.CheckConstraint(
                condition=models.Q(points__gt=0), name="pt_points_pos"
            ),
            models.CheckConstraint(
                condition=~models.Q(point_kind=PointKind.PROGRAM_COMPLETION)
                | models.Q(points=50),
                name="pt_bonus_50",
            ),
            models.UniqueConstraint(
                fields=["completed_session", "point_kind"],
                condition=models.Q(completed_session__isnull=False),
                name="pt_session_kind_uq",
            ),
            models.UniqueConstraint(
                fields=["user_program", "point_kind"],
                condition=models.Q(user_program__isnull=False),
                name="pt_program_kind_uq",
            ),
        ]


class Achievement(models.Model):
    code = models.CharField(max_length=64, choices=AchievementCode.choices, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True, default="", db_default="")
    rule_code = models.CharField(max_length=64)
    is_archived = models.BooleanField(default=False, db_default=False)

    class Meta:
        db_table = "achievements"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["is_archived", "code"], name="ach_arch_code_idx")
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(code__in=AchievementCode.values),
                name="ach_code_valid",
            )
        ]

    def __str__(self) -> str:
        return self.name


class UserAchievement(models.Model):
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="user_achievements"
    )
    achievement = models.ForeignKey(
        Achievement, on_delete=models.PROTECT, related_name="user_achievements"
    )
    unlocked_at = models.DateTimeField(default=timezone.now)
    name_snapshot = models.CharField(max_length=160)
    rule_code_snapshot = models.CharField(max_length=64)

    class Meta:
        db_table = "user_achievements"
        ordering = ["-unlocked_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "achievement"], name="ua_user_achievement_uq"
            )
        ]


class ChallengeGoalKind(models.TextChoices):
    WORKOUTS = "workouts", "Тренування"
    MINUTES = "minutes", "Хвилини"


class Challenge(models.Model):
    name = models.CharField(max_length=160)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    goal_kind = models.CharField(max_length=16, choices=ChallengeGoalKind.choices)
    goal_value = models.PositiveIntegerField()
    is_archived = models.BooleanField(default=False, db_default=False)

    class Meta:
        db_table = "challenges"
        ordering = ["start_at", "id"]
        indexes = [
            models.Index(
                fields=["is_archived", "start_at", "end_at"], name="ch_arch_period_idx"
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_at__lt=models.F("end_at")),
                name="ch_period_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(goal_value__gt=0), name="ch_goal_pos"
            ),
            models.CheckConstraint(
                condition=models.Q(goal_kind__in=ChallengeGoalKind.values),
                name="ch_goal_kind_valid",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class ParticipationStatus(models.TextChoices):
    JOINED = "joined", "Приєднано"
    COMPLETED = "completed", "Завершено"
    EXPIRED = "expired", "Завершився строк"


class ChallengeParticipation(models.Model):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="challenge_participations",
    )
    challenge = models.ForeignKey(
        Challenge, on_delete=models.PROTECT, related_name="participations"
    )
    joined_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=12,
        choices=ParticipationStatus.choices,
        default=ParticipationStatus.JOINED,
        db_default="joined",
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "challenge_participations"
        ordering = ["-joined_at", "-id"]
        indexes = [
            models.Index(fields=["challenge", "status"], name="cp_challenge_status_idx")
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "challenge"], name="cp_user_challenge_uq"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status=ParticipationStatus.COMPLETED,
                        completed_at__isnull=False,
                    )
                    | (
                        models.Q(
                            status__in=[
                                ParticipationStatus.JOINED,
                                ParticipationStatus.EXPIRED,
                            ]
                        )
                        & models.Q(completed_at__isnull=True)
                    )
                ),
                name="cp_completion_state",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=ParticipationStatus.values),
                name="cp_status_valid",
            ),
        ]
