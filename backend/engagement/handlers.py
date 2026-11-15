from decimal import Decimal

from django.db.models import Count, Max, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from execution.models import CompletedSession, ExerciseResult
from execution.policies import PointsPolicy

from .events import WorkoutCompleted
from .ledger import award_program_completion_bonus
from .models import (
    Achievement,
    AchievementCode,
    ChallengeParticipation,
    ParticipationStatus,
    PointKind,
    PointTransaction,
    UserAchievement,
)
from .policies import AchievementEvaluator, AchievementFacts
from .selectors import challenge_participation_progress


class PointsLedgerHandler:
    def handle(self, event: WorkoutCompleted) -> None:
        points = PointsPolicy.workout_points(
            duration_min=event.duration_min,
            completed_at=event.completed_at,
            planned_at=event.scheduled_at,
        )
        PointTransaction.objects.get_or_create(
            completed_session_id=event.session_id,
            point_kind=PointKind.WORKOUT_COMPLETION,
            defaults={"user_id": event.user_id, "points": points},
        )
        if event.program_completed and event.user_program_id is not None:
            award_program_completion_bonus(
                user_id=event.user_id, user_program_id=event.user_program_id
            )


class AchievementHandler:
    def handle(self, event: WorkoutCompleted) -> None:
        session_totals = CompletedSession.objects.filter(
            user_id=event.user_id
        ).aggregate(
            session_count=Count("id"),
            total_duration=Coalesce(
                Sum("duration_min"),
                Decimal("0"),
                output_field=CompletedSession._meta.get_field("duration_min"),
            ),
        )
        result_totals = ExerciseResult.objects.filter(
            completed_session__user_id=event.user_id
        ).aggregate(
            cardio_distance=Coalesce(
                Sum(
                    "actual_distance_km",
                    filter=Q(exercise_category_snapshot="cardio"),
                ),
                Decimal("0"),
                output_field=ExerciseResult._meta.get_field("actual_distance_km"),
            ),
            strength_load=Max(
                "actual_load_kg", filter=Q(exercise_category_snapshot="strength")
            ),
        )
        already = UserAchievement.objects.filter(user_id=event.user_id).values_list(
            "achievement__code", flat=True
        )
        codes = AchievementEvaluator.evaluate(
            AchievementFacts(
                session_count=session_totals["session_count"],
                total_duration_min=session_totals["total_duration"],
                cardio_distance_km=result_totals["cardio_distance"],
                maximum_strength_load_kg=result_totals["strength_load"],
            ),
            already,
        )
        definitions = Achievement.objects.filter(
            code__in=[AchievementCode(code).value for code in codes], is_archived=False
        )
        for achievement in definitions:
            UserAchievement.objects.get_or_create(
                user_id=event.user_id,
                achievement=achievement,
                defaults={
                    "unlocked_at": event.completed_at,
                    "name_snapshot": achievement.name,
                    "rule_code_snapshot": achievement.rule_code,
                },
            )


class ChallengeHandler:
    def handle(self, event: WorkoutCompleted) -> None:
        current_time = timezone.now()
        participations = list(
            ChallengeParticipation.objects.select_for_update(of=("self",))
            .select_related("challenge")
            .filter(user_id=event.user_id, status=ParticipationStatus.JOINED)
        )
        for participation in participations:
            projection = challenge_participation_progress(
                participation, now=current_time
            )
            if projection.effective_status == ParticipationStatus.COMPLETED:
                participation.status = ParticipationStatus.COMPLETED
                participation.completed_at = event.completed_at
                participation.save(update_fields=["status", "completed_at"])
            elif projection.effective_status == ParticipationStatus.EXPIRED:
                participation.status = ParticipationStatus.EXPIRED
                participation.save(update_fields=["status"])


def default_workout_completed_dispatcher(*, optional_handlers=()):
    from .events import WorkoutCompletedDispatcher

    dispatcher = WorkoutCompletedDispatcher()
    dispatcher.register(PointsLedgerHandler())
    dispatcher.register(AchievementHandler())
    dispatcher.register(ChallengeHandler())
    for handler in optional_handlers:
        dispatcher.register(handler, required=False)
    return dispatcher
