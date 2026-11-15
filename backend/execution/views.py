import hashlib
import json
from uuid import UUID

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import IdempotencyConflict, IdempotencyKeyInvalid
from .models import CompletedSession
from .serializers import (
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
