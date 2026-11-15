"""Domain services for personal program selection and planning."""

from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Prefetch, QuerySet, prefetch_related_objects
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from accounts.errors import ProfileMissing
from accounts.models import Profile
from catalog.models import (
    Exercise,
    ProgramTemplate,
    ProgramTemplateStatus,
    ProgramTemplateWorkout,
    Workout,
    WorkoutExercise,
)
from catalog.services import CatalogPublicationService
from engagement.ledger import award_program_completion_bonus

from .errors import (
    InvalidProgramState,
    PlannedSessionsExist,
    RecommendationMismatch,
    RecommendationUnavailable,
)
from .models import (
    Notification,
    NotificationStatus,
    NotificationType,
    ScheduledSession,
    ScheduledSessionStatus,
    UserProgram,
    UserProgramExercise,
    UserProgramStatus,
    UserProgramWorkout,
)
from .policies import (
    can_schedule,
    format_utc_seconds,
    normalize_scheduled_at,
    reminder_visible_at,
    should_record_reschedule,
)
from .program_completion import evaluate_program_completion
from .selectors import with_program_progress
from .strategies import get_selection_strategy


class ProgramSelectionService:
    """Service encapsulating program template recommendation and deep copy."""

    @classmethod
    def recommend_program_template(
        cls, user: Any
    ) -> tuple[ProgramTemplate, dict[str, Any]]:
        """Find the best matching published template without writing state."""
        profile = Profile.objects.filter(user=user).first()
        if not profile:
            raise ProfileMissing()

        candidates = list(
            cls._eligible_templates(profile).prefetch_related(
                "program_template_workouts__workout__workout_exercises__exercise"
            )
        )
        return cls._choose(profile, candidates)

    @staticmethod
    def _eligible_templates(profile: Profile) -> QuerySet[ProgramTemplate]:
        return ProgramTemplate.objects.filter(
            fitness_goal=profile.fitness_goal,
            experience_level=profile.experience_level,
            status=ProgramTemplateStatus.PUBLISHED,
        ).order_by("id")

    @staticmethod
    def _choose(
        profile: Profile, candidates: list[ProgramTemplate]
    ) -> tuple[ProgramTemplate, dict[str, Any]]:
        if not candidates:
            raise RecommendationUnavailable()
        strategy = get_selection_strategy(profile.fitness_goal)
        winner = strategy.rank(candidates, profile.workouts_per_week)[0]

        reason = {
            "exact_goal": True,
            "exact_level": True,
            "frequency_difference": abs(
                winner.workouts_per_week - profile.workouts_per_week
            ),
            "strategy": strategy.name,
            "composition_criterion": strategy.composition_criterion,
        }
        return winner, reason

    @classmethod
    @transaction.atomic
    def create_user_program_from_template(
        cls, user: Any, program_template_id: int
    ) -> UserProgram:
        """Copy one consistent committed catalog composition into a draft."""
        profile = Profile.objects.select_for_update().filter(user=user).first()
        if not profile:
            raise ProfileMissing()

        if not ProgramTemplate.objects.filter(
            pk=program_template_id, status=ProgramTemplateStatus.PUBLISHED
        ).exists():
            raise NotFound()

        # Admin edits lock their parent template/workout rows when saving inlines.
        # Lock in a stable order before reading any composition or ranking it.
        candidates = list(cls._eligible_templates(profile).select_for_update())
        workout_ids = list(
            ProgramTemplateWorkout.objects.filter(program_template__in=candidates)
            .order_by("workout_id")
            .values_list("workout_id", flat=True)
            .distinct()
        )
        list(
            Workout.objects.filter(pk__in=workout_ids)
            .order_by("pk")
            .select_for_update()
        )
        exercise_ids = WorkoutExercise.objects.filter(
            workout_id__in=workout_ids
        ).values_list("exercise_id", flat=True)
        list(
            Exercise.objects.filter(pk__in=exercise_ids)
            .order_by("pk")
            .select_for_update()
        )
        prefetch_related_objects(
            candidates,
            "program_template_workouts__workout__workout_exercises__exercise",
        )
        winner, _ = cls._choose(profile, candidates)
        if winner.pk != program_template_id:
            raise RecommendationMismatch()

        user_program = UserProgram.objects.create(
            user=user,
            source_program_template=winner,
            fitness_goal=winner.fitness_goal,
            name=winner.name,
            description=winner.description,
            status=UserProgramStatus.DRAFT,
            is_archived=False,
            source_program_template_name_snapshot=winner.name,
            bonus_target_sessions=None,
        )

        ptws = sorted(
            winner.program_template_workouts.all(),
            key=lambda item: (item.position, item.id),
        )
        for ptw in ptws:
            upw = UserProgramWorkout.objects.create(
                user_program=user_program,
                source_workout=ptw.workout,
                position=ptw.position,
                name=ptw.workout.name,
                category=ptw.workout.category,
            )
            wes = sorted(
                ptw.workout.workout_exercises.all(),
                key=lambda item: (item.position, item.id),
            )
            for we in wes:
                UserProgramExercise.objects.create(
                    user_program_workout=upw,
                    exercise=we.exercise,
                    position=we.position,
                    recommended_sets=we.recommended_sets,
                    recommended_reps=we.recommended_reps,
                    recommended_load_kg=we.recommended_load_kg,
                    recommended_duration_min=we.recommended_duration_min,
                    recommended_distance_km=we.recommended_distance_km,
                )

        return user_program


class ProgramPlanningService:
    """Service managing personal programs, details, and personal composition edits."""

    @classmethod
    def list_user_programs(
        cls,
        user: Any,
        *,
        status: str | None = None,
        is_archived: bool = False,
    ) -> QuerySet[UserProgram]:
        """Return owner's UserPrograms ordered by id DESC."""
        qs = with_program_progress(
            UserProgram.objects.filter(user=user, is_archived=is_archived)
        )
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-id")

    @classmethod
    def get_user_program_detail(cls, user: Any, program_id: int) -> UserProgram:
        """Return the owner's program with ordered personal composition."""
        ordered_exercises = Prefetch(
            "exercises",
            queryset=UserProgramExercise.objects.select_related("exercise").order_by(
                "position", "id"
            ),
        )
        ordered_workouts = Prefetch(
            "workouts",
            queryset=UserProgramWorkout.objects.prefetch_related(
                ordered_exercises
            ).order_by("position", "id"),
        )

        program = (
            with_program_progress(UserProgram.objects.filter(user=user, pk=program_id))
            .prefetch_related(ordered_workouts)
            .first()
        )
        if not program:
            raise NotFound()
        return program

    @classmethod
    @transaction.atomic
    def update_user_program_info(
        cls,
        user: Any,
        program_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> UserProgram:
        """Update name and description of a draft/active personal program under lock."""
        program = (
            UserProgram.objects.select_for_update()
            .filter(user=user, pk=program_id)
            .first()
        )
        if not program:
            raise NotFound()

        if program.is_archived or program.status == UserProgramStatus.COMPLETED:
            raise InvalidProgramState()

        if name is not None:
            clean_name = name.strip()
            if not clean_name:
                raise ValidationError(
                    {"name": ["Назва програми не може бути порожньою."]}
                )
            program.name = clean_name

        if description is not None:
            program.description = description.strip()

        program.save(update_fields=["name", "description"])
        return program

    @classmethod
    @transaction.atomic
    def replace_workout_composition(
        cls,
        user: Any,
        program_id: int,
        entry_id: int,
        *,
        name: str,
        exercises_data: list[dict[str, Any]],
    ) -> UserProgramWorkout:
        """Replace one personal composition under the shared program lock."""
        # Future E01 takes this UserProgram lock before reading its composition.
        program = (
            UserProgram.objects.select_for_update()
            .filter(user=user, pk=program_id)
            .first()
        )
        if not program:
            raise NotFound()

        if program.is_archived or program.status == UserProgramStatus.COMPLETED:
            raise InvalidProgramState()

        workout = program.workouts.filter(pk=entry_id).first()
        if not workout:
            raise NotFound()

        clean_name = name.strip()
        if not clean_name:
            raise ValidationError(
                {"name": ["Назва тренування не може бути порожньою."]}
            )

        if not exercises_data:
            raise ValidationError(
                {"exercises": ["Склад вправ тренування не може бути порожнім."]}
            )

        # Positions describe the resulting order, independently of JSON array order.
        positions = [item.get("position") for item in exercises_data]
        expected_positions = list(range(1, len(exercises_data) + 1))
        if sorted(positions) != expected_positions:
            raise ValidationError(
                {
                    "exercises": [
                        "Позиції вправ мають бути послідовними цілими числами "
                        f"від 1 до {len(exercises_data)} без пропусків та дублікатів."
                    ]
                }
            )

        # Serialize catalog visibility with Exercise archiving. Query the rows
        # in ID order to avoid lock inversion for requests with many exercises.
        exercise_ids = [
            item.get("exercise_id") or getattr(item.get("exercise"), "pk", None)
            for item in exercises_data
        ]
        exercises_by_id = {
            exercise.pk: exercise
            for exercise in Exercise.objects.filter(pk__in=exercise_ids)
            .order_by("pk")
            .select_for_update()
        }

        # Validate each exercise's parameters according to category rules (BR-004)
        for idx, item in enumerate(exercises_data, start=1):
            for field in (
                "recommended_load_kg",
                "recommended_duration_min",
                "recommended_distance_km",
            ):
                value = item.get(field)
                if value is not None and not isinstance(value, Decimal):
                    try:
                        item[field] = Decimal(str(value))
                    except (InvalidOperation, TypeError, ValueError) as exc:
                        raise ValidationError(
                            {f"exercises[{idx - 1}].{field}": ["Некоректне число."]}
                        ) from exc
            exercise_id = exercise_ids[idx - 1]
            exercise = exercises_by_id.get(exercise_id)
            if exercise is None or exercise.is_archived:
                raise ValidationError(
                    {
                        f"exercises[{idx - 1}].exercise_id": [
                            f"Вправа з ID {exercise_id} не існує або архівована."
                        ]
                    }
                )
            item["exercise"] = exercise

            temp_we = UserProgramExercise(
                user_program_workout=workout,
                exercise=exercise,
                position=item["position"],
                recommended_sets=item.get("recommended_sets"),
                recommended_reps=item.get("recommended_reps"),
                recommended_load_kg=item.get("recommended_load_kg"),
                recommended_duration_min=item.get("recommended_duration_min"),
                recommended_distance_km=item.get("recommended_distance_km"),
            )
            try:
                CatalogPublicationService.validate_workout_exercise_parameters(
                    temp_we, allow_archived_exercise=False
                )
            except DjangoValidationError as exc:
                if hasattr(exc, "message_dict"):
                    fields = {
                        f"exercises[{idx - 1}].{field}": messages
                        for field, messages in exc.message_dict.items()
                    }
                else:
                    fields = {f"exercises[{idx - 1}]": exc.messages}
                raise ValidationError(fields) from exc

        workout.name = clean_name
        workout.save(update_fields=["name"])

        workout.exercises.all().delete()
        for item in exercises_data:
            UserProgramExercise.objects.create(
                user_program_workout=workout,
                exercise=item["exercise"],
                position=item["position"],
                recommended_sets=item.get("recommended_sets"),
                recommended_reps=item.get("recommended_reps"),
                recommended_load_kg=item.get("recommended_load_kg"),
                recommended_duration_min=item.get("recommended_duration_min"),
                recommended_distance_km=item.get("recommended_distance_km"),
            )

        return workout

    @classmethod
    @transaction.atomic
    def activate_user_program(cls, user: Any, program_id: int) -> UserProgram:
        program = (
            UserProgram.objects.select_for_update()
            .filter(user=user, pk=program_id)
            .first()
        )
        if not program:
            raise NotFound()
        if program.is_archived or program.status != UserProgramStatus.DRAFT:
            raise InvalidProgramState()

        initial_count = program.scheduled_sessions.exclude(
            status=ScheduledSessionStatus.CANCELLED
        ).count()
        if initial_count < 1:
            raise ValidationError(
                {"non_field_errors": ["Для активації потрібен хоча б один слот."]}
            )

        program.status = UserProgramStatus.ACTIVE
        program.activated_at = timezone.now()
        program.bonus_target_sessions = max(3, initial_count)
        program.save(update_fields=["status", "activated_at", "bonus_target_sessions"])
        return with_program_progress(UserProgram.objects.filter(pk=program.pk)).get()

    @classmethod
    def get_program_progress(cls, user: Any, program_id: int) -> UserProgram:
        program = with_program_progress(
            UserProgram.objects.filter(user=user, pk=program_id)
        ).first()
        if not program:
            raise NotFound()
        return program

    @classmethod
    @transaction.atomic
    def archive_user_program(cls, user: Any, program_id: int) -> UserProgram:
        program = (
            UserProgram.objects.select_for_update()
            .filter(user=user, pk=program_id)
            .first()
        )
        if not program:
            raise NotFound()
        if program.is_archived:
            return program
        if program.status == UserProgramStatus.ACTIVE:
            raise InvalidProgramState()
        if (
            program.status == UserProgramStatus.DRAFT
            and program.scheduled_sessions.filter(
                status=ScheduledSessionStatus.PLANNED
            ).exists()
        ):
            raise PlannedSessionsExist()
        program.is_archived = True
        program.save(update_fields=["is_archived"])
        return program

    @classmethod
    @transaction.atomic
    def cancel_scheduled_session(cls, user: Any, session_id: int) -> ScheduledSession:
        identity = (
            ScheduledSession.objects.filter(user=user, pk=session_id)
            .values("user_program_id")
            .first()
        )
        if not identity:
            raise NotFound()
        program = None
        if identity["user_program_id"] is not None:
            program = (
                UserProgram.objects.select_for_update()
                .filter(user=user, pk=identity["user_program_id"])
                .first()
            )
            if not program:
                raise NotFound()
        session = (
            ScheduledSession.objects.select_for_update()
            .filter(user=user, pk=session_id)
            .first()
        )
        if not session:
            raise NotFound()
        if session.status == ScheduledSessionStatus.CANCELLED:
            return cls._load_session(session.pk)
        if session.status == ScheduledSessionStatus.COMPLETED:
            raise InvalidProgramState()
        if program and (
            program.is_archived or program.status == UserProgramStatus.COMPLETED
        ):
            raise InvalidProgramState()

        cancelled_at = timezone.now()
        session.status = ScheduledSessionStatus.CANCELLED
        session.save(update_fields=["status"])
        ReminderService.close(session)
        if program:
            evaluation = evaluate_program_completion(program, completed_at=cancelled_at)
            if evaluation.bonus_eligible:
                award_program_completion_bonus(
                    user_id=user.pk, user_program_id=program.pk
                )
        return cls._load_session(session.pk)

    @classmethod
    @transaction.atomic
    def create_scheduled_session(
        cls,
        user: Any,
        *,
        scheduled_at,
        user_program_workout_id: int | None,
        source_workout_id: int | None,
    ) -> ScheduledSession:
        scheduled_at = normalize_scheduled_at(scheduled_at)
        cls._validate_future_time(scheduled_at)
        if user_program_workout_id is not None:
            program_id = (
                UserProgramWorkout.objects.filter(
                    pk=user_program_workout_id, user_program__user=user
                )
                .values_list("user_program_id", flat=True)
                .first()
            )
            if program_id is None:
                raise NotFound()
            program = (
                UserProgram.objects.select_for_update()
                .filter(pk=program_id, user=user)
                .first()
            )
            if not program:
                raise NotFound()
            if program.is_archived or program.status == UserProgramStatus.COMPLETED:
                raise InvalidProgramState()
            program_workout = (
                UserProgramWorkout.objects.filter(
                    pk=user_program_workout_id, user_program=program
                )
                .select_related("source_workout")
                .first()
            )
            if not program_workout:
                raise NotFound()
            session = ScheduledSession.objects.create(
                user=user,
                user_program=program,
                user_program_workout=program_workout,
                source_workout=program_workout.source_workout,
                scheduled_at=scheduled_at,
            )
        else:
            workout = Workout.objects.filter(
                pk=source_workout_id, is_archived=False
            ).first()
            if not workout:
                raise NotFound()
            session = ScheduledSession.objects.create(
                user=user,
                source_workout=workout,
                scheduled_at=scheduled_at,
            )

        ReminderService.create_for_session(session)
        return cls._load_session(session.pk)

    @classmethod
    @transaction.atomic
    def reschedule_session(
        cls, user: Any, session_id: int, *, scheduled_at
    ) -> ScheduledSession:
        scheduled_at = normalize_scheduled_at(scheduled_at)
        cls._validate_future_time(scheduled_at)
        identity = (
            ScheduledSession.objects.filter(user=user, pk=session_id)
            .values("user_program_id")
            .first()
        )
        if not identity:
            raise NotFound()

        if identity["user_program_id"] is not None:
            program = (
                UserProgram.objects.select_for_update()
                .filter(pk=identity["user_program_id"], user=user)
                .first()
            )
            if not program:
                raise NotFound()
            if program.is_archived or program.status == UserProgramStatus.COMPLETED:
                raise InvalidProgramState()

        session = (
            ScheduledSession.objects.select_for_update()
            .filter(user=user, pk=session_id)
            .first()
        )
        if not session:
            raise NotFound()
        if session.status != ScheduledSessionStatus.PLANNED:
            raise InvalidProgramState()

        if should_record_reschedule(
            current_scheduled_at=session.scheduled_at,
            requested_scheduled_at=scheduled_at,
        ):
            previous = format_utc_seconds(session.scheduled_at)
            session.reschedule_history = [*session.reschedule_history, previous]
            session.scheduled_at = scheduled_at
            session.save(update_fields=["scheduled_at", "reschedule_history"])
            ReminderService.reschedule(session)
        return cls._load_session(session.pk)

    @staticmethod
    def _validate_future_time(scheduled_at) -> None:
        if not can_schedule(scheduled_at=scheduled_at, now=timezone.now()):
            raise ValidationError(
                {"scheduled_at": ["Час заняття має бути в майбутньому."]}
            )

    @classmethod
    def _load_session(
        cls, session_id: int, *, user: Any | None = None
    ) -> ScheduledSession:
        queryset = ScheduledSession.objects.select_related(
            "user_program", "user_program_workout", "source_workout"
        ).prefetch_related("notifications")
        if user is not None:
            queryset = queryset.filter(user=user)
        session = queryset.filter(pk=session_id).first()
        if not session:
            raise NotFound()
        return session

    @classmethod
    def get_scheduled_session(cls, user: Any, session_id: int) -> ScheduledSession:
        return cls._load_session(session_id, user=user)


class ReminderService:
    """Keep the single workout reminder consistent with its slot."""

    @staticmethod
    def create_for_session(session: ScheduledSession) -> Notification:
        return Notification.objects.create(
            user=session.user,
            scheduled_session=session,
            type=NotificationType.WORKOUT_REMINDER,
            visible_at=reminder_visible_at(session.scheduled_at),
            status=NotificationStatus.PENDING,
        )

    @staticmethod
    def reschedule(session: ScheduledSession) -> Notification:
        reminder = Notification.objects.select_for_update().get(
            scheduled_session=session,
            type=NotificationType.WORKOUT_REMINDER,
        )
        reminder.visible_at = reminder_visible_at(session.scheduled_at)
        reminder.status = NotificationStatus.PENDING
        reminder.read_at = None
        reminder.save(update_fields=["visible_at", "status", "read_at"])
        return reminder

    @staticmethod
    def close(session: ScheduledSession) -> Notification:
        reminder = Notification.objects.select_for_update().get(
            scheduled_session=session,
            type=NotificationType.WORKOUT_REMINDER,
        )
        if timezone.now() < reminder.visible_at:
            reminder.status = NotificationStatus.CANCELLED
            reminder.read_at = None
            reminder.save(update_fields=["status", "read_at"])
        return reminder

    @staticmethod
    @transaction.atomic
    def mark_read(user: Any, notification_id: int) -> Notification:
        reminder = (
            Notification.objects.select_for_update(of=("self",))
            .filter(
                user=user,
                pk=notification_id,
                visible_at__lte=timezone.now(),
                status__in=[NotificationStatus.PENDING, NotificationStatus.READ],
            )
            .select_related("scheduled_session")
            .first()
        )
        if not reminder:
            raise NotFound()
        if reminder.status == NotificationStatus.PENDING:
            reminder.status = NotificationStatus.READ
            reminder.read_at = timezone.now()
            reminder.save(update_fields=["status", "read_at"])
        return reminder
