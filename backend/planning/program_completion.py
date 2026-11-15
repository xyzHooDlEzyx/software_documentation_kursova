from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from django.db.models import Count, Q

from .models import ScheduledSessionStatus, UserProgram, UserProgramStatus


@dataclass(frozen=True)
class ProgramCompletionEvaluation:
    completed_now: bool
    bonus_eligible: bool
    total_planned: int
    completed_planned: int


def evaluate_program_completion(
    program: UserProgram, *, completed_at: datetime
) -> ProgramCompletionEvaluation:
    """Evaluate BR-007 while the caller holds the UserProgram row lock."""
    counts = program.scheduled_sessions.aggregate(
        total=Count("id", filter=~Q(status=ScheduledSessionStatus.CANCELLED)),
        completed=Count("id", filter=Q(status=ScheduledSessionStatus.COMPLETED)),
    )
    total = counts["total"]
    completed = counts["completed"]
    if program.status != UserProgramStatus.ACTIVE or total == 0 or completed != total:
        return ProgramCompletionEvaluation(False, False, total, completed)

    program.status = UserProgramStatus.COMPLETED
    program.completed_at = completed_at
    program.total_planned_at_completion = total
    program.completed_planned_at_completion = completed
    program.progress_percent_at_completion = Decimal("100.0")
    program.save(
        update_fields=[
            "status",
            "completed_at",
            "total_planned_at_completion",
            "completed_planned_at_completion",
            "progress_percent_at_completion",
        ]
    )
    eligible = (
        program.bonus_target_sessions is not None
        and completed >= program.bonus_target_sessions
    )
    return ProgramCompletionEvaluation(True, eligible, total, completed)
