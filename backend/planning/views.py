"""REST API views for personal program selection and planning (G01–G06)."""

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param
from rest_framework.views import APIView

from catalog.serializers import EmptyQuerySerializer

from .serializers import (
    CreateUserProgramRequestSerializer,
    ProgramListQuerySerializer,
    ProgramRecommendationResponseSerializer,
    ReplaceWorkoutCompositionRequestSerializer,
    UpdateUserProgramRequestSerializer,
    UpdateUserProgramResponseSerializer,
    UserProgramDetailSerializer,
    UserProgramSummarySerializer,
    UserProgramWorkoutItemSerializer,
)
from .services import ProgramPlanningService, ProgramSelectionService


def _extract_query_data(request) -> dict:
    return {k: v[0] if len(v) == 1 else v for k, v in request.query_params.lists()}


def _paginate_queryset(request, queryset, *, page: int, page_size: int, serializer_cls):
    total_count = queryset.count()
    if total_count == 0:
        if page > 1:
            raise ValidationError(
                {"page": ["Сторінка виходить за межі наявних результатів."]}
            )
        return Response(
            {"count": 0, "next": None, "previous": None, "results": []},
            status=status.HTTP_200_OK,
        )

    offset = (page - 1) * page_size
    if offset >= total_count:
        raise ValidationError(
            {"page": ["Сторінка виходить за межі наявних результатів."]}
        )

    items = list(queryset[offset : offset + page_size])
    base_url = request.build_absolute_uri()
    next_url = (
        replace_query_param(base_url, "page", page + 1)
        if offset + page_size < total_count
        else None
    )
    previous_url = (
        None if page == 1 else replace_query_param(base_url, "page", page - 1)
    )
    return Response(
        {
            "count": total_count,
            "next": next_url,
            "previous": previous_url,
            "results": serializer_cls(items, many=True).data,
        },
        status=status.HTTP_200_OK,
    )


class ProgramRecommendationView(APIView):
    """G01 — GET /api/v1/program-recommendation/ (Strategy recommendation)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query_serializer = EmptyQuerySerializer(data=_extract_query_data(request))
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
        query_serializer = ProgramListQuerySerializer(data=_extract_query_data(request))
        query_serializer.is_valid(raise_exception=True)
        validated = query_serializer.validated_data

        queryset = ProgramPlanningService.list_user_programs(
            request.user,
            status=validated.get("status"),
            is_archived=validated.get("archived", False),
        )
        return _paginate_queryset(
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
        query_serializer = EmptyQuerySerializer(data=_extract_query_data(request))
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
