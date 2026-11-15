from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from accounts.errors import ProfileMissing
from accounts.models import Profile, WeightEntry
from catalog.models import Workout, WorkoutExercise
from engagement.events import WorkoutCompleted
from engagement.handlers import default_workout_completed_dispatcher
from engagement.models import PointKind, PointTransaction
from planning.models import (
    ScheduledSession,
    ScheduledSessionStatus,
    UserProgram,
    UserProgramExercise,
    UserProgramStatus,
)
from planning.program_completion import evaluate_program_completion
from planning.selectors import program_progress, with_program_progress
from planning.services import ReminderService

from .errors import DuplicateCompletion, IdempotencyConflict, InvalidCompletionState
from .models import CompletedSession, ExerciseResult
from .policies import CalorieSegment, CaloriesEstimator, validate_duration
from .processors import PROCESSORS, ValidatedExerciseResult


@dataclass(frozen=True)
class CompletionOutcome:
    session: CompletedSession
    created: bool


class WorkoutCompletionService:
    @classmethod
    def complete(
        cls,
        *,
        user: Any,
        idempotency_key: str,
        fingerprint: str,
        data: dict[str, Any],
    ) -> CompletionOutcome:
        try:
            return cls._complete_atomic(
                user=user,
                idempotency_key=idempotency_key,
                fingerprint=fingerprint,
                data=data,
            )
        except IntegrityError:
            committed = CompletedSession.objects.filter(
                user=user, idempotency_key=idempotency_key
            ).first()
            if committed:
                if committed.request_payload_sha256 != fingerprint:
                    raise IdempotencyConflict()
                return CompletionOutcome(committed, False)
            if (
                data.get("scheduled_session_id")
                and CompletedSession.objects.filter(
                    scheduled_session_id=data["scheduled_session_id"]
                ).exists()
            ):
                raise DuplicateCompletion()
            raise

    @classmethod
    @transaction.atomic
    def _complete_atomic(
        cls,
        *,
        user: Any,
        idempotency_key: str,
        fingerprint: str,
        data: dict[str, Any],
    ) -> CompletionOutcome:
        committed = CompletedSession.objects.filter(
            user=user, idempotency_key=idempotency_key
        ).first()
        if committed:
            if committed.request_payload_sha256 != fingerprint:
                raise IdempotencyConflict()
            return CompletionOutcome(committed, False)

        profile = Profile.objects.filter(user=user).first()
        if profile is None:
            raise ProfileMissing()

        completed_at = timezone.now()
        duration = validate_duration(data["duration_min"])
        slot, program, performed_name, performed_category, allowed = (
            cls._resolve_source(user=user, data=data)
        )
        raced = CompletedSession.objects.filter(
            user=user, idempotency_key=idempotency_key
        ).first()
        if raced:
            if raced.request_payload_sha256 != fingerprint:
                raise IdempotencyConflict()
            return CompletionOutcome(raced, False)
        if slot and CompletedSession.objects.filter(scheduled_session=slot).exists():
            raise DuplicateCompletion()
        if program and (
            program.status != UserProgramStatus.ACTIVE or program.is_archived
        ):
            raise InvalidCompletionState()
        if slot and slot.status != ScheduledSessionStatus.PLANNED:
            if slot.status == ScheduledSessionStatus.COMPLETED:
                raise DuplicateCompletion()
            raise InvalidCompletionState()
        validated_results = cls._validate_results(data["results"], allowed)
        segment_duration = sum(
            (item.actual_duration_min or Decimal("0") for item in validated_results),
            Decimal("0"),
        )
        if segment_duration > duration:
            raise ValidationError(
                {"results": ["Сума тривалостей вправ перевищує тривалість заняття."]}
            )

        workout = (
            slot.source_workout
            if slot
            else Workout.objects.get(pk=data["source_workout_id"])
        )
        weight = (
            WeightEntry.objects.filter(user=user, measured_at__lte=completed_at)
            .order_by("-measured_at", "-id")
            .first()
        )
        estimate = CaloriesEstimator.estimate(
            weight_kg=weight.weight_kg if weight else None,
            birth_date=profile.date_of_birth,
            completed_at=completed_at,
            duration_min=duration,
            segments=[
                CalorieSegment(item.actual_duration_min, item.exercise.met_value)
                for item in validated_results
                if item.actual_duration_min is not None
            ],
            workout_met_value=workout.met_value,
        )

        fact = CompletedSession.objects.create(
            user=user,
            scheduled_session=slot,
            source_workout=workout,
            source_workout_id_snapshot=workout.pk,
            source_workout_name_snapshot=workout.name,
            performed_workout_name_snapshot=performed_name,
            performed_workout_category_snapshot=performed_category,
            source_program_template_id_snapshot=(
                program.source_program_template_id if program else None
            ),
            source_program_template_name_snapshot=(
                program.source_program_template_name_snapshot if program else None
            ),
            user_program_id_snapshot=program.pk if program else None,
            user_program_name_snapshot=program.name if program else None,
            completed_at=completed_at,
            duration_min=duration,
            weight_kg_snapshot=weight.weight_kg if weight else None,
            weight_entry_id_snapshot=weight.pk if weight else None,
            workout_met_value_snapshot=workout.met_value,
            workout_met_activity_code_snapshot=workout.met_activity_code,
            workout_met_reference_version_snapshot=workout.met_reference_version,
            workout_met_description_snapshot=workout.met_activity_description,
            estimated_calories=estimate.value,
            missing_calorie_reason=estimate.reason,
            idempotency_key=idempotency_key,
            request_payload_sha256=fingerprint,
        )
        for item in validated_results:
            exercise = item.exercise
            ExerciseResult.objects.create(
                completed_session=fact,
                source_exercise=exercise,
                source_exercise_id_snapshot=exercise.pk,
                exercise_name_snapshot=exercise.name,
                exercise_category_snapshot=exercise.category,
                position=item.position,
                actual_sets=item.actual_sets,
                actual_reps=item.actual_reps,
                actual_load_kg=item.actual_load_kg,
                actual_duration_min=item.actual_duration_min,
                actual_distance_km=item.actual_distance_km,
                met_value_snapshot=exercise.met_value,
                met_activity_code_snapshot=exercise.met_activity_code,
                met_reference_version_snapshot=exercise.met_reference_version,
                met_activity_description_snapshot=exercise.met_activity_description,
            )

        evaluation = None
        if slot:
            slot.status = ScheduledSessionStatus.COMPLETED
            slot.save(update_fields=["status"])
            ReminderService.close(slot)
            if program:
                evaluation = evaluate_program_completion(
                    program, completed_at=completed_at
                )

        event = WorkoutCompleted(
            session_id=fact.pk,
            user_id=user.pk,
            completed_at=completed_at,
            duration_min=duration,
            scheduled_at=slot.scheduled_at if slot else None,
            user_program_id=program.pk if program else None,
            program_completed=bool(evaluation and evaluation.bonus_eligible),
        )
        default_workout_completed_dispatcher().dispatch(event)
        return CompletionOutcome(fact, True)

    @staticmethod
    def _resolve_source(*, user: Any, data: dict[str, Any]):
        session_id = data.get("scheduled_session_id")
        if session_id is None:
            workout = Workout.objects.filter(
                pk=data["source_workout_id"], is_archived=False
            ).first()
            if workout is None:
                raise NotFound()
            composition = list(
                WorkoutExercise.objects.filter(workout=workout)
                .select_related("exercise")
                .order_by("position", "id")
            )
            return (
                None,
                None,
                workout.name,
                workout.category,
                {
                    item.position: (item.exercise_id, item.exercise)
                    for item in composition
                },
            )

        identity = (
            ScheduledSession.objects.filter(user=user, pk=session_id)
            .values("user_program_id")
            .first()
        )
        if identity is None:
            raise NotFound()
        program = None
        if identity["user_program_id"] is not None:
            program = (
                UserProgram.objects.select_for_update()
                .filter(user=user, pk=identity["user_program_id"])
                .first()
            )
            if program is None:
                raise NotFound()
        slot = (
            # of=("self",): user_program_workout is nullable (LEFT JOIN), and
            # PostgreSQL cannot lock the nullable side of an outer join.
            ScheduledSession.objects.select_for_update(of=("self",))
            .select_related("source_workout", "user_program_workout")
            .filter(user=user, pk=session_id)
            .first()
        )
        if slot is None:
            raise NotFound()
        if program and slot.user_program_workout_id is not None:
            composition = list(
                UserProgramExercise.objects.filter(
                    user_program_workout=slot.user_program_workout
                )
                .select_related("exercise")
                .order_by("position", "id")
            )
            name = slot.user_program_workout.name
            category = slot.user_program_workout.category
        else:
            composition = list(
                WorkoutExercise.objects.filter(workout=slot.source_workout)
                .select_related("exercise")
                .order_by("position", "id")
            )
            name = slot.source_workout.name
            category = slot.source_workout.category
        return (
            slot,
            program,
            name,
            category,
            {item.position: (item.exercise_id, item.exercise) for item in composition},
        )

    @staticmethod
    def _validate_results(results, allowed) -> list[ValidatedExerciseResult]:
        output = []
        errors = {}
        for index, result in enumerate(results):
            allowed_item = allowed.get(result.get("position"))
            processor = (
                PROCESSORS.get(allowed_item[1].category) if allowed_item else None
            )
            if processor is None:
                errors[f"results[{index}]"] = [
                    "Вправа не належить до актуального складу тренування."
                ]
                continue
            try:
                output.append(processor.process(result, allowed_composition=allowed))
            except ValidationError as exc:
                if isinstance(exc.detail, dict):
                    for field, messages in exc.detail.items():
                        errors[f"results[{index}].{field}"] = [
                            str(item) for item in messages
                        ]
                else:
                    errors[f"results[{index}]"] = [str(item) for item in exc.detail]
        if errors:
            raise ValidationError(errors)
        return output

    @staticmethod
    def response_data(fact: CompletedSession) -> dict[str, Any]:
        points = PointTransaction.objects.get(
            completed_session=fact, point_kind=PointKind.WORKOUT_COMPLETION
        ).points
        program_data = None
        if fact.user_program_id_snapshot is not None:
            program = with_program_progress(
                UserProgram.objects.filter(pk=fact.user_program_id_snapshot)
            ).first()
            if program:
                program_data = {
                    "id": program.pk,
                    "status": program.status,
                    "progress_percent": program_progress(program)["percent"],
                    "bonus_earned": program.point_transactions.filter(
                        point_kind=PointKind.PROGRAM_COMPLETION
                    ).exists(),
                }
        return {
            "id": fact.pk,
            "scheduled_session_id": fact.scheduled_session_id,
            "source_workout_id": fact.source_workout_id,
            "completed_at": fact.completed_at,
            "duration_min": fact.duration_min,
            "estimated_calories": fact.estimated_calories,
            "missing_calorie_reason": fact.missing_calorie_reason,
            "workout_points": points,
            "program": program_data,
        }
