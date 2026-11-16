from django.urls import path

from .views import (
    AchievementListView,
    ChallengeDetailView,
    ChallengeJoinView,
    ChallengeListView,
    ChallengeParticipationListView,
    PointsSummaryView,
    PointTransactionListView,
    UserAchievementListView,
)

urlpatterns = [
    path("points/summary/", PointsSummaryView.as_view(), name="points-summary"),
    path(
        "point-transactions/",
        PointTransactionListView.as_view(),
        name="point-transaction-list",
    ),
    path("achievements/", AchievementListView.as_view(), name="achievement-list"),
    path(
        "user-achievements/",
        UserAchievementListView.as_view(),
        name="user-achievement-list",
    ),
    path(
        "challenge-participations/",
        ChallengeParticipationListView.as_view(),
        name="challenge-participation-list",
    ),
    path("challenges/", ChallengeListView.as_view(), name="challenge-list"),
    path(
        "challenges/<int:challenge_id>/",
        ChallengeDetailView.as_view(),
        name="challenge-detail",
    ),
    path(
        "challenges/<int:challenge_id>/join/",
        ChallengeJoinView.as_view(),
        name="challenge-join",
    ),
]
