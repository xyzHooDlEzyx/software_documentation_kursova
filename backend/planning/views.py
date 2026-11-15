"""REST API views for personal programs, sessions, and reminders."""

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.serializers import EmptyQuerySerializer
from config.api import extract_query_data, paginate_queryset

from .selectors import (
    filter_notifications_by_current,
    filter_sessions_in_local_period,
    get_visible_notification,
    owner_program_exists,
    owner_sessions,
    visible_notifications,
)
from .serializers import (
    ActivateProgramResponseSerializer,
    ArchiveProgramResponseSerializer,
    CancelledSessionResponseSerializer,
    CreatedScheduledSessionResponseSerializer,
    CreateScheduledSessionSerializer,
    CreateUserProgramRequestSerializer,
    EmptyBodySerializer,
    NotificationQuerySerializer,
    NotificationSerializer,
    ProgramListQuerySerializer,
    ProgramProgressSerializer,
    ProgramRecommendationResponseSerializer,
    ReplaceWorkoutCompositionRequestSerializer,
    RescheduledSessionResponseSerializer,
    RescheduleSessionSerializer,
    ScheduledSessionDetailSerializer,
    ScheduledSessionQuerySerializer,
    ScheduledSessionSummarySerializer,
    UpdateUserProgramRequestSerializer,
    UpdateUserProgramResponseSerializer,
    UserProgramDetailSerializer,
    UserProgramSummarySerializer,
    UserProgramWorkoutItemSerializer,
)
from .services import ProgramPlanningService, ProgramSelectionService, ReminderService


class ProgramRecommendationView(APIView):
    """G01 — GET /api/v1/program-recommendation/ (Strategy recommendation)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query_serializer = EmptyQuerySerializer(data=extract_query_data(request))
        query_serializer.is_valid(raise_exception=True)

        template, reason = ProgramSelectionService.recommend_program_template(
            request.user
        )
        data = {
            "program_template": template,
            "reason": reason,
        }
        return Response(
            ProgramRecommendationResponseSerializer(data).data,
            status=status.HTTP_200_OK,
        )


class UserProgramListCreateView(APIView):
    """G02 (GET /api/v1/user-programs/) and G03 (POST /api/v1/user-programs/)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query_serializer = ProgramListQuerySerializer(data=extract_query_data(request))
        query_serializer.is_valid(raise_exception=True)
        validated = query_serializer.validated_data

        queryset = ProgramPlanningService.list_user_programs(
            request.user,
            status=validated.get("status"),
            is_archived=validated.get("archived", False),
        )
        return paginate_queryset(
            request,
            queryset,
            page=validated["page"],
            page_size=validated["page_size"],
            serializer_cls=UserProgramSummarySerializer,
        )

    def post(self, request):
        req_serializer = CreateUserProgramRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        program_template_id = req_serializer.validated_data["program_template_id"]

        user_program = ProgramSelectionService.create_user_program_from_template(
            request.user, program_template_id=program_template_id
        )
        # Preload for serialized response
        loaded = ProgramPlanningService.get_user_program_detail(
            request.user, user_program.pk
        )
        return Response(
            UserProgramDetailSerializer(loaded).data,
            status=status.HTTP_201_CREATED,
        )


class UserProgramDetailView(APIView):
    """Read (G04) or update (G05) a personal program."""

    permission_classes = [IsAuthenticated]

    def get(self, request, program_id: int):
        query_serializer = EmptyQuerySerializer(data=extract_query_data(request))
        query_serializer.is_valid(raise_exception=True)

        program = ProgramPlanningService.get_user_program_detail(
            request.user, program_id=program_id
        )
        return Response(
            UserProgramDetailSerializer(program).data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, program_id: int):
        req_serializer = UpdateUserProgramRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        validated = req_serializer.validated_data

        updated = ProgramPlanningService.update_user_program_info(
            request.user,
            program_id=program_id,
            name=validated.get("name"),
            description=validated.get("description"),
        )
        return Response(
            UpdateUserProgramResponseSerializer(updated).data,
            status=status.HTTP_200_OK,
        )


class UserProgramWorkoutCompositionView(APIView):
    """G06 — replace one personal workout composition."""

    permission_classes = [IsAuthenticated]

    def put(self, request, program_id: int, entry_id: int):
        req_serializer = ReplaceWorkoutCompositionRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        validated = req_serializer.validated_data

        updated_workout = ProgramPlanningService.replace_workout_composition(
            request.user,
            program_id=program_id,
            entry_id=entry_id,
            name=validated["name"],
            exercises_data=validated["exercises"],
        )
        return Response(
            UserProgramWorkoutItemSerializer(updated_workout).data,
            status=status.HTTP_200_OK,
        )


class UserProgramActivateView(APIView):
    """G07 — activate a draft program and freeze its bonus threshold."""

    permission_classes = [IsAuthenticated]

    def post(self, request, program_id: int):
        serializer = EmptyBodySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        program = ProgramPlanningService.activate_user_program(request.user, program_id)
        return Response(
            ActivateProgramResponseSerializer(program).data,
            status=status.HTTP_200_OK,
        )


class UserProgramProgressView(APIView):
    """G08 — current BR-006 progress projection."""

    permission_classes = [IsAuthenticated]

    def get(self, request, program_id: int):
        serializer = EmptyQuerySerializer(data=extract_query_data(request))
        serializer.is_valid(raise_exception=True)
        program = ProgramPlanningService.get_program_progress(request.user, program_id)
        return Response(
            ProgramProgressSerializer(program).data, status=status.HTTP_200_OK
        )


class UserProgramArchiveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, program_id: int):
        serializer = EmptyBodySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        program = ProgramPlanningService.archive_user_program(request.user, program_id)
        return Response(ArchiveProgramResponseSerializer(program).data)


class ScheduledSessionListCreateView(APIView):
    """S01/S02 — list calendar slots or atomically create a slot and reminder."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ScheduledSessionQuerySerializer(data=extract_query_data(request))
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        queryset = owner_sessions(request.user)

        program_id = data.get("user_program_id")
        if program_id is not None:
            if not owner_program_exists(request.user, program_id):
                raise NotFound()
            queryset = queryset.filter(user_program_id=program_id)
        if data.get("status"):
            queryset = queryset.filter(status=data["status"])
        if data.get("start_date") is not None:
            queryset = filter_sessions_in_local_period(
                queryset,
                start_date=data["start_date"],
                end_date=data["end_date"],
            )
        queryset = queryset.order_by("scheduled_at", "id")
        return paginate_queryset(
            request,
            queryset,
            page=data["page"],
            page_size=data["page_size"],
            serializer_cls=ScheduledSessionSummarySerializer,
        )

    def post(self, request):
        serializer = CreateScheduledSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        session = ProgramPlanningService.create_scheduled_session(
            request.user,
            scheduled_at=data["scheduled_at"],
            user_program_workout_id=data.get("user_program_workout_id"),
            source_workout_id=data.get("source_workout_id"),
        )
        return Response(
            CreatedScheduledSessionResponseSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )


class ScheduledSessionDetailView(APIView):
    """S03/S04 — retrieve or reschedule an owned slot."""

    permission_classes = [IsAuthenticated]

    def get(self, request, session_id: int):
        query = EmptyQuerySerializer(data=extract_query_data(request))
        query.is_valid(raise_exception=True)
        session = ProgramPlanningService.get_scheduled_session(request.user, session_id)
        return Response(
            ScheduledSessionDetailSerializer(session).data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, session_id: int):
        serializer = RescheduleSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = ProgramPlanningService.reschedule_session(
            request.user,
            session_id,
            scheduled_at=serializer.validated_data["scheduled_at"],
        )
        return Response(
            RescheduledSessionResponseSerializer(session).data,
            status=status.HTTP_200_OK,
        )


class ScheduledSessionCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id: int):
        serializer = EmptyBodySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = ProgramPlanningService.cancel_scheduled_session(
            request.user, session_id
        )
        return Response(CancelledSessionResponseSerializer(session).data)


class NotificationListView(APIView):
    """N01 — visible, non-cancelled reminders owned by the current user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = NotificationQuerySerializer(data=extract_query_data(request))
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        queryset = visible_notifications(request.user)
        if data.get("status"):
            queryset = queryset.filter(status=data["status"])
        if "is_current" in data:
            queryset = filter_notifications_by_current(
                queryset, is_current=data["is_current"]
            )
        queryset = queryset.order_by("-visible_at", "-id")
        return paginate_queryset(
            request,
            queryset,
            page=data["page"],
            page_size=data["page_size"],
            serializer_cls=NotificationSerializer,
        )


class NotificationDetailView(APIView):
    """N02 — retrieve one owned visible reminder."""

    permission_classes = [IsAuthenticated]

    def get(self, request, notification_id: int):
        query = EmptyQuerySerializer(data=extract_query_data(request))
        query.is_valid(raise_exception=True)
        reminder = get_visible_notification(request.user, notification_id)
        return Response(
            NotificationSerializer(reminder).data, status=status.HTTP_200_OK
        )


class NotificationReadView(APIView):
    """N03 — idempotently mark an owned visible reminder as read."""

    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id: int):
        serializer = EmptyBodySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reminder = ReminderService.mark_read(request.user, notification_id)
        return Response(
            NotificationSerializer(reminder).data, status=status.HTTP_200_OK
        )
