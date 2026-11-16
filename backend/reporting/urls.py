from django.urls import path

from .views import LeaderboardView, StatisticsOverviewView, WeightChartView

urlpatterns = [
    path("statistics/weight-chart/", WeightChartView.as_view(), name="weight-chart"),
    path(
        "statistics/overview/",
        StatisticsOverviewView.as_view(),
        name="statistics-overview",
    ),
    path("leaderboard/", LeaderboardView.as_view(), name="leaderboard"),
]
