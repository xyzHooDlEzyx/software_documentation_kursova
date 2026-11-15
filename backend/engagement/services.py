from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound

from .errors import ChallengeExpired
from .models import Challenge, ChallengeParticipation
from .selectors import challenge_participation_progress


class ChallengeParticipationService:
    @staticmethod
    @transaction.atomic
    def join(*, user, challenge_id: int):
        challenge = Challenge.objects.filter(pk=challenge_id, is_archived=False).first()
        if challenge is None:
            raise NotFound()
        existing = (
            ChallengeParticipation.objects.select_related("challenge")
            .filter(user=user, challenge=challenge)
            .first()
        )
        if existing is not None:
            ChallengeParticipationService._apply_projection(existing)
            return existing, False
        joined_at = timezone.now()
        if joined_at >= challenge.end_at:
            raise ChallengeExpired()
        try:
            with transaction.atomic():
                participation = ChallengeParticipation.objects.create(
                    user=user, challenge=challenge, joined_at=joined_at
                )
        except IntegrityError:
            participation = ChallengeParticipation.objects.select_related(
                "challenge"
            ).get(
                user=user,
                challenge=challenge,
            )
            ChallengeParticipationService._apply_projection(participation)
            return participation, False
        ChallengeParticipationService._apply_projection(participation)
        return participation, True

    @staticmethod
    def _apply_projection(participation: ChallengeParticipation) -> None:
        projection = challenge_participation_progress(participation)
        participation.progress_value = projection.progress_value
        participation.effective_status = projection.effective_status
