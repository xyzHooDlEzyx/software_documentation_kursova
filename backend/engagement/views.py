from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.api import extract_query_data, paginate_queryset

from .selectors import available_challenge, available_challenges
from .serializers import (
    ChallengeParticipationSerializer,
    ChallengeQuerySerializer,
    ChallengeSerializer,
    EmptyBodySerializer,
)
from .services import ChallengeParticipationService


class ChallengeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = ChallengeQuerySerializer(data=extract_query_data(request))
        query.is_valid(raise_exception=True)
        data = query.validated_data
        queryset = available_challenges(
            request.user, state=data.get("state"), now=timezone.now()
        )
        return paginate_queryset(
            request,
            queryset,
            page=data["page"],
            page_size=data["page_size"],
            serializer_cls=ChallengeSerializer,
        )


class ChallengeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, challenge_id: int):
        query = EmptyBodySerializer(data=extract_query_data(request))
        query.is_valid(raise_exception=True)
        challenge = available_challenge(request.user, challenge_id=challenge_id)
        if challenge is None:
            raise NotFound()
        return Response(ChallengeSerializer(challenge).data)


class ChallengeJoinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, challenge_id: int):
        query = EmptyBodySerializer(data=extract_query_data(request))
        query.is_valid(raise_exception=True)
        body = EmptyBodySerializer(data=request.data)
        body.is_valid(raise_exception=True)
        participation, created = ChallengeParticipationService.join(
            user=request.user, challenge_id=challenge_id
        )
        return Response(
            ChallengeParticipationSerializer(participation).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
