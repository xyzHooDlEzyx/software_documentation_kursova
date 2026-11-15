from django.urls import path

from .views import CompletedSessionCreateView

urlpatterns = [
    path(
        "completed-sessions/",
        CompletedSessionCreateView.as_view(),
        name="completed-session-create",
    ),
]
