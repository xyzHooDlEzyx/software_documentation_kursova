import secrets

from django.http import JsonResponse
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    ParseError,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.views import exception_handler as drf_exception_handler


def error_body(code, message, fields=None):
    return {
        "error": {
            "code": code,
            "message": message,
            "fields": fields or {},
            "request_id": f"req-{secrets.token_hex(4)}",
        }
    }


class EmailTaken(APIException):
    status_code = 409
    default_detail = "Ця адреса вже зареєстрована."
    default_code = "email_taken"


class UnknownField(APIException):
    status_code = 400
    default_detail = "Невідоме поле."
    default_code = "unknown_field"

    def __init__(self, names):
        self.names = names
        super().__init__()


class InvalidCredentials(AuthenticationFailed):
    default_detail = "Невірні облікові дані."
    default_code = "invalid_credentials"


class ResetTokenInvalidOrExpired(APIException):
    status_code = 400
    default_detail = (
        "Посилання для відновлення пароля недійсне або термін його дії минув."
    )
    default_code = "reset_token_invalid_or_expired"


def _field_errors(detail):
    if isinstance(detail, dict):
        return {
            key: [str(item) for item in (value if isinstance(value, list) else [value])]
            for key, value in detail.items()
        }
    if isinstance(detail, list):
        return {"non_field_errors": [str(item) for item in detail]}
    return {"non_field_errors": [str(detail)]}


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, UnknownField):
        code, message = "unknown_field", "Невідоме поле."
        fields = {name: ["Поле не підтримується."] for name in exc.names}
    elif isinstance(exc, EmailTaken):
        code, message, fields = "email_taken", str(exc.detail), {}
    elif isinstance(exc, InvalidCredentials):
        code, message, fields = "invalid_credentials", str(exc.detail), {}
    elif isinstance(exc, ResetTokenInvalidOrExpired):
        code, message, fields = "reset_token_invalid_or_expired", str(exc.detail), {}
    elif isinstance(exc, Throttled):
        code, message, fields = (
            "rate_limit_exceeded",
            "Забагато запитів. Спробуйте пізніше.",
            {},
        )
    elif isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        code, message, fields = "authentication_required", "Потрібен вхід.", {}
    elif isinstance(exc, ParseError):
        code, message, fields = "invalid_json", "Некоректний JSON.", {}
    elif isinstance(exc, PermissionDenied):
        if str(exc.detail).startswith("CSRF Failed"):
            code, message = "csrf_failed", "CSRF-перевірка не пройдена."
        else:
            code, message = "permission_denied", "Недостатньо прав."
        fields = {}
    elif isinstance(exc, ValidationError):
        code, message = "validation_error", "Некоректні дані."
        fields = _field_errors(exc.detail)
    else:
        code, message, fields = "request_failed", "Запит не виконано.", {}
    response.data = error_body(code, message, fields)
    return response


def csrf_failure(request, reason=""):
    return JsonResponse(
        error_body("csrf_failed", "CSRF-перевірка не пройдена."), status=403
    )
