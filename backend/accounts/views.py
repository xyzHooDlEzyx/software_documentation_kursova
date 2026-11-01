from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import IntegrityError, transaction
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import EmailTaken, InvalidCredentials
from .serializers import (
    AccountSerializer,
    CredentialsSerializer,
    LeaderboardSettingsSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegistrationSerializer,
)
from .services import PasswordResetService
from .throttling import (
    PasswordResetConfirmIPThrottle,
    PasswordResetEmailThrottle,
    PasswordResetIPThrottle,
)

User = get_user_model()

PASSWORD_RESET_REQUEST_MESSAGE = (
    "Якщо акаунт із такою адресою існує, "
    "ми надішлемо інструкції для відновлення пароля."
)
PASSWORD_RESET_CONFIRM_MESSAGE = "Пароль оновлено. Увійдіть із новим паролем."


class CsrfView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrf_token": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise EmailTaken()
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=email, password=serializer.validated_data["password"]
                )
        except IntegrityError as exc:
            if User.objects.filter(email__iexact=email).exists():
                raise EmailTaken() from exc
            raise
        return Response(AccountSerializer(user).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CredentialsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            raise InvalidCredentials()
        login(request, user)
        return Response(AccountSerializer(user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(AccountSerializer(request.user).data)

    def patch(self, request):
        serializer = LeaderboardSettingsSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            if not user.is_active:
                raise NotAuthenticated()
            for name, value in serializer.validated_data.items():
                setattr(user, name, value)
            if user.leaderboard_opt_in and not (user.public_alias or "").strip():
                raise ValidationError(
                    {"public_alias": ["Для участі в рейтингу потрібен псевдонім."]}
                )
            user.save(update_fields=["public_alias", "leaderboard_opt_in"])
        return Response(AccountSerializer(user).data)


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetIPThrottle, PasswordResetEmailThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PasswordResetService().request_reset(serializer.validated_data["email"])
        return Response(
            {"message": PASSWORD_RESET_REQUEST_MESSAGE}, status=status.HTTP_200_OK
        )


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetConfirmIPThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PasswordResetService().confirm_reset(
            uid=serializer.validated_data["uid"],
            token=serializer.validated_data["token"],
            new_password=serializer.validated_data["new_password"],
        )
        return Response(
            {"message": PASSWORD_RESET_CONFIRM_MESSAGE}, status=status.HTTP_200_OK
        )
