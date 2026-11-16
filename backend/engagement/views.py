from django.db.models import Exists, OuterRef
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.selectors import kyiv_date_range_to_utc
from config.api import extract_query_data, paginate_queryset
from reporting.selectors import StatisticsQueryService

from .models import (
    Achievement,
    ChallengeParticipation,
    PointTransaction,
    UserAchievement,
)
from .selectors import (
    available_challenge,
    available_challenges,
    challenge_participation_progress,
)
from .serializers import (
    AchievementSerializer,
    ChallengeParticipationHistorySerializer,
    ChallengeParticipationSerializer,
    ChallengeQuerySerializer,
    ChallengeSerializer,
    EmptyBodySerializer,
    OptionalPeriodSerializer,
    PageQuerySerializer,
    ParticipationQuerySerializer,
    PointTransactionQuerySerializer,
    PointTransactionSerializer,
    UserAchievementSerializer,
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


class PointsSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = OptionalPeriodSerializer(data=extract_query_data(request))
        query.is_valid(raise_exception=True)
        data = query.validated_data
        totals = StatisticsQueryService.points_summary(user=request.user, **data)
        period = None
        if data.get("start_date") is not None:
            period = {
                "start_date": data["start_date"].isoformat(),
                "end_date": data["end_date"].isoformat(),
                "timezone": "Europe/Kyiv",
            }
        return Response({"period": period, **totals})


class PointTransactionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = PointTransactionQuerySerializer(data=extract_query_data(request))
        query.is_valid(raise_exception=True)
        data = query.validated_data
        queryset = PointTransaction.objects.filter(user=request.user)
        if data.get("start_date") is not None:
            start_at, end_at = kyiv_date_range_to_utc(
                data["start_date"], data["end_date"]
            )
            queryset = queryset.filter(awarded_at__gte=start_at, awarded_at__lt=end_at)
        if data.get("point_kind"):
            queryset = queryset.filter(point_kind=data["point_kind"])
        return paginate_queryset(
            request,
            queryset.order_by("-awarded_at", "-id"),
            page=data["page"],
            page_size=data["page_size"],
            serializer_cls=PointTransactionSerializer,
        )


class AchievementListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = PageQuerySerializer(data=extract_query_data(request))
        query.is_valid(raise_exception=True)
        data = query.validated_data
        queryset = (
            Achievement.objects.filter(is_archived=False)
            .annotate(
                earned=Exists(
                    UserAchievement.objects.filter(
                        user=request.user, achievement_id=OuterRef("pk")
                    )
                )
            )
            .order_by("code", "id")
        )
        return paginate_queryset(
            request,
            queryset,
            page=data["page"],
            page_size=data["page_size"],
            serializer_cls=AchievementSerializer,
        )


class UserAchievementListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = PageQuerySerializer(data=extract_query_data(request))
        query.is_valid(raise_exception=True)
        data = query.validated_data
        queryset = UserAchievement.objects.filter(user=request.user).order_by(
            "-unlocked_at", "-id"
        )
        return paginate_queryset(
            request,
            queryset,
            page=data["page"],
            page_size=data["page_size"],
            serializer_cls=UserAchievementSerializer,
        )


class ChallengeParticipationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = ParticipationQuerySerializer(data=extract_query_data(request))
        query.is_valid(raise_exception=True)
        data = query.validated_data
        participations = list(
            ChallengeParticipation.objects.filter(user=request.user)
            .select_related("challenge")
            .order_by("-joined_at", "-id")
        )
        for participation in participations:
            projection = challenge_participation_progress(participation)
            participation.progress_value = projection.progress_value
            participation.effective_status = projection.effective_status
        if data.get("status"):
            participations = [
                p for p in participations if p.effective_status == data["status"]
            ]
        start = (data["page"] - 1) * data["page_size"]
        end = start + data["page_size"]
        if start >= len(participations) and data["page"] > 1:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                {"page": ["Сторінка виходить за межі наявних результатів."]}
            )
        return Response(
            {
                "count": len(participations),
                "next": None,
                "previous": None,
                "results": ChallengeParticipationHistorySerializer(
                    participations[start:end], many=True
                ).data,
            }
        )
