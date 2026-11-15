from rest_framework import status
from rest_framework.exceptions import APIException


class IdempotencyKeyInvalid(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Потрібен коректний Idempotency-Key у форматі UUID v4."
    default_code = "validation_error"


class IdempotencyConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Ключ уже використано з іншими даними."
    default_code = "idempotency_conflict"


class DuplicateCompletion(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Заняття вже завершено."
    default_code = "duplicate_completion"


class InvalidCompletionState(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Неможливо завершити заняття для програми в поточному стані."
    default_code = "invalid_state"


class ExecutionDomainError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Дані виконання не відповідають правилам."
    default_code = "validation_error"
