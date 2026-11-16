from django.urls import path

from .views import CompletedSessionCreateView, CompletedSessionDetailView

urlpatterns = [
    path(
        "completed-sessions/",
        CompletedSessionCreateView.as_view(),
        name="completed-session-create",
    ),
    path(
        "completed-sessions/<int:session_id>/",
        CompletedSessionDetailView.as_view(),
        name="completed-session-detail",
    ),
]
