"""Read-only REST API views for the shared fitness catalog (C01–C04).

Authorization note:
In requirements (FR-006, FR-008, FR-010, access matrix), read access to
Exercise/Workout/Category is CONFIRMED for authenticated User and Administrator
(IsAuthenticated), whereas Guest read access is PROPOSED.
We enforce the confirmed access policy (permission_classes = [IsAuthenticated])
and do not silently promote proposed Guest access without owner confirmation.
"""

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param
from rest_framework.views import APIView

from .selectors import (
    get_active_workout_detail,
    list_active_exercises,
    list_active_workouts,
    list_categories,
)
from .serializers import (
    CatalogListQuerySerializer,
    CategoryItemSerializer,
    EmptyQuerySerializer,
    ExerciseSerializer,
    WorkoutDetailSerializer,
    WorkoutSummarySerializer,
)


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


class CategoryListView(APIView):
    """C01 — GET /api/v1/categories/ (confirmed IsAuthenticated)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query_serializer = EmptyQuerySerializer(data=_extract_query_data(request))
        query_serializer.is_valid(raise_exception=True)
        categories = list_categories()
        return Response(
            {"results": CategoryItemSerializer(categories, many=True).data},
            status=status.HTTP_200_OK,
        )


class ExerciseListView(APIView):
    """C02 — GET /api/v1/exercises/ (confirmed IsAuthenticated)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query_serializer = CatalogListQuerySerializer(data=_extract_query_data(request))
        query_serializer.is_valid(raise_exception=True)
        validated = query_serializer.validated_data
        queryset = list_active_exercises(
            category=validated.get("category"),
            search=validated.get("search"),
        )
        return _paginate_queryset(
            request,
            queryset,
            page=validated["page"],
            page_size=validated["page_size"],
            serializer_cls=ExerciseSerializer,
        )


class WorkoutListView(APIView):
    """C03 — GET /api/v1/workouts/ (confirmed IsAuthenticated)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query_serializer = CatalogListQuerySerializer(data=_extract_query_data(request))
        query_serializer.is_valid(raise_exception=True)
        validated = query_serializer.validated_data
        queryset = list_active_workouts(
            category=validated.get("category"),
            search=validated.get("search"),
        )
        return _paginate_queryset(
            request,
            queryset,
            page=validated["page"],
            page_size=validated["page_size"],
            serializer_cls=WorkoutSummarySerializer,
        )


class WorkoutDetailView(APIView):
    """C04 — GET /api/v1/workouts/<id>/ (confirmed IsAuthenticated)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, workout_id: int):
        query_serializer = EmptyQuerySerializer(data=_extract_query_data(request))
        query_serializer.is_valid(raise_exception=True)
        workout = get_active_workout_detail(workout_id=workout_id)
        return Response(
            WorkoutDetailSerializer(workout).data,
            status=status.HTTP_200_OK,
        )
