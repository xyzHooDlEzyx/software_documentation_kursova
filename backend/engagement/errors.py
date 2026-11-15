from rest_framework.exceptions import APIException


class ChallengeExpired(APIException):
    status_code = 409
    default_detail = "Строк вступу до челенджу завершився."
    default_code = "invalid_state"
