import hashlib
import json
from uuid import UUID

from django.db.models import F, FilteredRelation, Q
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.selectors import kyiv_date_range_to_utc
from config.api import extract_query_data, paginate_queryset
from engagement.models import PointKind

from .errors import IdempotencyConflict, IdempotencyKeyInvalid
from .models import CompletedSession
from .serializers import (
    CompletedSessionDetailSerializer,
    CompletedSessionListSerializer,
    CompletedSessionQuerySerializer,
    WorkoutCompletionRequestSerializer,
    WorkoutCompletionResponseSerializer,
)
from .services import WorkoutCompletionService


class CompletedSessionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        key = request.headers.get("Idempotency-Key")
        try:
            parsed = UUID(key or "")
        except ValueError, AttributeError:
            raise IdempotencyKeyInvalid()
        if parsed.version != 4 or str(parsed) != key:
            raise IdempotencyKeyInvalid()

        canonical = json.dumps(
            request.data,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        fingerprint = hashlib.sha256(canonical).hexdigest()
        committed = CompletedSession.objects.filter(
            user=request.user, idempotency_key=key
        ).first()
        if committed:
            if committed.request_payload_sha256 != fingerprint:
                raise IdempotencyConflict()
            payload = WorkoutCompletionService.response_data(committed)
            return Response(
                WorkoutCompletionResponseSerializer(payload).data,
                status=status.HTTP_200_OK,
            )
        serializer = WorkoutCompletionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        outcome = WorkoutCompletionService.complete(
            user=request.user,
            idempotency_key=key,
            fingerprint=fingerprint,
            data=serializer.validated_data,
        )
        payload = WorkoutCompletionService.response_data(outcome.session)
        response = Response(
            WorkoutCompletionResponseSerializer(payload).data,
            status=status.HTTP_201_CREATED if outcome.created else status.HTTP_200_OK,
        )
        if outcome.created:
            response["Location"] = f"/api/v1/completed-sessions/{outcome.session.pk}/"
        return response

    def get(self, request):
        query = CompletedSessionQuerySerializer(data=extract_query_data(request))
        query.is_valid(raise_exception=True)
        data = query.validated_data
        queryset = CompletedSession.objects.filter(user=request.user)
        if data.get("start_date") is not None:
            start_at, end_at = kyiv_date_range_to_utc(
                data["start_date"], data["end_date"]
            )
            queryset = queryset.filter(
                completed_at__gte=start_at, completed_at__lt=end_at
            )
        if data.get("source_workout_id") is not None:
            queryset = queryset.filter(source_workout_id=data["source_workout_id"])
        queryset = (
            queryset.alias(
                workout_tx=FilteredRelation(
                    "point_transactions",
                    condition=Q(
                        point_transactions__point_kind=PointKind.WORKOUT_COMPLETION
                    ),
                )
            )
            .annotate(workout_points=F("workout_tx__points"))
            .order_by("-completed_at", "-id")
        )
        return paginate_queryset(
            request,
            queryset,
            page=data["page"],
            page_size=data["page_size"],
            serializer_cls=CompletedSessionListSerializer,
        )


class CompletedSessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id: int):
        fact = (
            CompletedSession.objects.filter(user=request.user, pk=session_id)
            .prefetch_related("exercise_results", "point_transactions")
            .first()
        )
        if fact is None:
            raise NotFound()
        workout_points = next(
            tx.points
            for tx in fact.point_transactions.all()
            if tx.point_kind == PointKind.WORKOUT_COMPLETION
        )
        program_context = None
        if fact.user_program_id_snapshot is not None:
            program_context = {
                "source_program_template_id_snapshot": (
                    fact.source_program_template_id_snapshot
                ),
                "source_program_template_name_snapshot": (
                    fact.source_program_template_name_snapshot
                ),
                "user_program_id_snapshot": fact.user_program_id_snapshot,
                "user_program_name_snapshot": fact.user_program_name_snapshot,
            }
        payload = {
            **{
                field.name: getattr(fact, field.name)
                for field in fact._meta.fields
                if field.name
                not in {
                    "user",
                    "scheduled_session",
                    "source_workout",
                    "idempotency_key",
                    "request_payload_sha256",
                }
            },
            "id": fact.pk,
            "scheduled_session_id": fact.scheduled_session_id,
            "source_workout_id": fact.source_workout_id,
            "program_context": program_context,
            "workout_points": workout_points,
            "results": fact.exercise_results.all(),
        }
        return Response(CompletedSessionDetailSerializer(payload).data)
