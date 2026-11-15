import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from django.contrib.auth import get_user_model
from django.db import connection, transaction

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkoutCompleted:
    session_id: int
    user_id: int
    completed_at: datetime
    duration_min: Decimal
    scheduled_at: datetime | None = None
    user_program_id: int | None = None
    program_completed: bool = False


class WorkoutCompletedHandler(Protocol):
    def handle(self, event: WorkoutCompleted) -> None: ...


class WorkoutCompletedDispatcher:
    def __init__(self):
        self.required_handlers: list[WorkoutCompletedHandler] = []
        self.optional_handlers: list[WorkoutCompletedHandler] = []

    def register(
        self, handler: WorkoutCompletedHandler, *, required: bool = True
    ) -> None:
        handlers = self.required_handlers if required else self.optional_handlers
        handlers.append(handler)

    def dispatch_required(self, event: WorkoutCompleted) -> None:
        if not connection.in_atomic_block:
            raise RuntimeError("Required workout handlers need transaction.atomic().")
        User = get_user_model()
        User.objects.select_for_update(no_key=True).only("pk").get(pk=event.user_id)
        for handler in self.required_handlers:
            handler.handle(event)

    def dispatch_after_commit(self, event: WorkoutCompleted) -> None:
        for handler in self.optional_handlers:
            transaction.on_commit(
                lambda current=handler: self._handle_optional(current, event)
            )

    def dispatch(self, event: WorkoutCompleted) -> None:
        self.dispatch_required(event)
        self.dispatch_after_commit(event)

    @staticmethod
    def _handle_optional(
        handler: WorkoutCompletedHandler, event: WorkoutCompleted
    ) -> None:
        try:
            handler.handle(event)
        except Exception:
            logger.exception(
                "Optional workout-completed handler failed",
                extra={"session_id": event.session_id},
            )
