from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param
from rest_framework.views import APIView

from config.api import extract_query_data
from config.timezones import KYIV_TZ

from .selectors import LeaderboardQueryService, StatisticsQueryService, decimal_2
from .serializers import (
    LeaderboardQuerySerializer,
    RequiredPeriodQuerySerializer,
    WeightChartPointSerializer,
)


def period_payload(data):
    return {
        "start_date": data["start_date"].isoformat(),
        "end_date": data["end_date"].isoformat(),
        "timezone": "Europe/Kyiv",
    }


class WeightChartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = RequiredPeriodQuerySerializer(data=extract_query_data(request))
        query.is_valid(raise_exception=True)
        data = query.validated_data
        points = StatisticsQueryService.weight_chart(user=request.user, **data)
        return Response(
            {
                "period": period_payload(data),
                "points": WeightChartPointSerializer(points, many=True).data,
            }
        )


class StatisticsOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = RequiredPeriodQuerySerializer(data=extract_query_data(request))
        query.is_valid(raise_exception=True)
        data = query.validated_data
        totals = StatisticsQueryService.overview(user=request.user, **data)
        return Response(
            {
                "period": period_payload(data),
                "completed_workouts": totals["completed_workouts"],
                "performed_exercises": totals["performed_exercises"],
                "total_duration_min": str(decimal_2(totals["total_duration"])),
                "estimated_calories_total": str(decimal_2(totals["calories"])),
                "workouts_without_calorie_estimate": totals["missing_calories"],
                "weekly_activity": [
                    {
                        "week_start": bucket["week_start"].isoformat(),
                        "completed_workouts": bucket["completed_workouts"],
                        "total_duration_min": str(bucket["total_duration_min"]),
                    }
                    for bucket in totals["weekly_activity"]
                ],
            }
        )


class LeaderboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = LeaderboardQuerySerializer(data=extract_query_data(request))
        query.is_valid(raise_exception=True)
        data = query.validated_data
        period = LeaderboardQueryService.period(data["period"], data.get("anchor_date"))
        rows = LeaderboardQueryService.rows(period=period)
        for rank, row in enumerate(rows, start=1):
            row["rank"] = rank
        page = data["page"]
        page_size = data["page_size"]
        start = (page - 1) * page_size
        if start >= len(rows) and page > 1:
            raise ValidationError(
                {"page": ["Сторінка виходить за межі наявних результатів."]}
            )
        visible = rows[start : start + page_size]
        base_url = request.build_absolute_uri()
        own_row = next((row for row in rows if row["id"] == request.user.pk), None)
        own_points = (
            own_row["points"]
            if own_row is not None
            else LeaderboardQueryService.own_points(user=request.user, period=period)
        )
        period_data = {"kind": period.kind, "start_at": None, "end_at": None}
        if period.start_at is not None:
            period_data.update(
                {
                    "start_at": period.start_at.astimezone(KYIV_TZ).isoformat(),
                    "end_at": period.end_at.astimezone(KYIV_TZ).isoformat(),
                }
            )
        return Response(
            {
                "period": period_data,
                "count": len(rows),
                "next": replace_query_param(base_url, "page", page + 1)
                if start + page_size < len(rows)
                else None,
                "previous": replace_query_param(base_url, "page", page - 1)
                if page > 1
                else None,
                "results": [
                    {
                        "rank": row["rank"],
                        "public_alias": row["public_alias"],
                        "points": row["points"],
                    }
                    for row in visible
                ],
                "self": {
                    "opted_in": bool(own_row),
                    "points": own_points,
                    "rank": own_row["rank"] if own_row else None,
                },
            }
        )
