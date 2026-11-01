"""Domain and API exceptions for the planning application."""

from rest_framework import status
from rest_framework.exceptions import APIException


class RecommendationUnavailable(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Немає доступних програм для вашого профілю."
    default_code = "recommendation_unavailable"


class RecommendationMismatch(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "ID не відповідає поточній рекомендації."
    default_code = "recommendation_mismatch"


class InvalidProgramState(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Неможливо змінити програму в поточному стані."
    default_code = "invalid_state"
