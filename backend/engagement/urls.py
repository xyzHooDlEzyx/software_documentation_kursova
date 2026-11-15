from django.urls import path

from .views import ChallengeDetailView, ChallengeJoinView, ChallengeListView

urlpatterns = [
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
