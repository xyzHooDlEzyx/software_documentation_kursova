from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from rest_framework.authentication import SessionAuthentication


class CaseInsensitiveEmailBackend(ModelBackend):
    """Authenticate by email while the database enforces UNIQUE(LOWER(email))."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        email = username or kwargs.get(User.USERNAME_FIELD)
        if email is None or password is None:
            return None
        try:
            user = User.objects.get(email__iexact=User.objects.normalize_email(email))
        except User.DoesNotExist:
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None


class APISessionAuthentication(SessionAuthentication):
    """Keep Django sessions while making anonymous API failures HTTP 401."""

    def authenticate_header(self, request):
        return 'Session realm="api"'
