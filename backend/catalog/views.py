"""Read-only REST API views for the shared fitness catalog (C01–C04).

Authorization note:
In requirements (FR-006, FR-008, FR-010, access matrix), read access to
Exercise/Workout/Category is CONFIRMED for authenticated User and Administrator
(IsAuthenticated), whereas Guest read access is PROPOSED.
We enforce the confirmed access policy (permission_classes = [IsAuthenticated])
and do not silently promote proposed Guest access without owner confirmation.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.api import extract_query_data, paginate_queryset

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


class CategoryListView(APIView):
    """C01 — GET /api/v1/categories/ (confirmed IsAuthenticated)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query_serializer = EmptyQuerySerializer(data=extract_query_data(request))
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
        query_serializer = CatalogListQuerySerializer(data=extract_query_data(request))
        query_serializer.is_valid(raise_exception=True)
        validated = query_serializer.validated_data
        queryset = list_active_exercises(
            category=validated.get("category"),
            search=validated.get("search"),
        )
        return paginate_queryset(
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
        query_serializer = CatalogListQuerySerializer(data=extract_query_data(request))
        query_serializer.is_valid(raise_exception=True)
        validated = query_serializer.validated_data
        queryset = list_active_workouts(
            category=validated.get("category"),
            search=validated.get("search"),
        )
        return paginate_queryset(
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
        query_serializer = EmptyQuerySerializer(data=extract_query_data(request))
        query_serializer.is_valid(raise_exception=True)
        workout = get_active_workout_detail(workout_id=workout_id)
        return Response(
            WorkoutDetailSerializer(workout).data,
            status=status.HTTP_200_OK,
        )
