from execution.policies import PointsPolicy

from .models import PointKind, PointTransaction


def award_program_completion_bonus(*, user_id: int, user_program_id: int):
    """Write the single BR-015 bonus through its unique ledger source."""
    return PointTransaction.objects.get_or_create(
        user_program_id=user_program_id,
        point_kind=PointKind.PROGRAM_COMPLETION,
        defaults={
            "user_id": user_id,
            "points": PointsPolicy.PROGRAM_COMPLETION_BONUS,
        },
    )
