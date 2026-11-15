from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Exists, OuterRef
from django.utils import timezone

from execution.models import CompletedSession

from .models import Challenge, ChallengeParticipation
from .policies import ChallengeFact, ChallengeProgressEvaluator


@dataclass(frozen=True)
class ChallengeParticipationProjection:
    progress_value: Decimal
    effective_status: str


def challenge_participation_progress(
    participation: ChallengeParticipation, *, now=None
) -> ChallengeParticipationProjection:
    """Project progress and expiry without writing.

    Persisted ``joined`` may lag after the challenge ends because expiry is written
    only by completion events. Read responses expose the effective ``expired`` state.
    """

    current_time = now or timezone.now()
    session_facts = CompletedSession.objects.filter(
        user_id=participation.user_id
    ).values("completed_at", "duration_min")
    facts = [ChallengeFact(**row) for row in session_facts]
    progress = ChallengeProgressEvaluator.evaluate(
        goal_kind=participation.challenge.goal_kind,
        goal_value=participation.challenge.goal_value,
        joined_at=participation.joined_at,
        start_at=participation.challenge.start_at,
        end_at=participation.challenge.end_at,
        facts=facts,
        now=current_time,
        already_completed=participation.status == "completed",
    )
    effective_status = participation.status
    if participation.status == "joined":
        if progress.completed:
            effective_status = "completed"
        elif progress.expired:
            effective_status = "expired"
    return ChallengeParticipationProjection(
        progress_value=progress.progress_value,
        effective_status=effective_status,
    )


def available_challenges(user, *, state: str | None, now):
    queryset = Challenge.objects.filter(is_archived=False).annotate(
        joined=Exists(
            ChallengeParticipation.objects.filter(
                user=user, challenge_id=OuterRef("pk")
            )
        )
    )
    if state == "active":
        queryset = queryset.filter(start_at__lte=now, end_at__gt=now)
    elif state == "upcoming":
        queryset = queryset.filter(start_at__gt=now)
    return queryset.order_by("start_at", "id")


def available_challenge(user, *, challenge_id: int):
    return (
        Challenge.objects.filter(pk=challenge_id, is_archived=False)
        .annotate(
            joined=Exists(
                ChallengeParticipation.objects.filter(
                    user=user, challenge_id=OuterRef("pk")
                )
            )
        )
        .first()
    )
