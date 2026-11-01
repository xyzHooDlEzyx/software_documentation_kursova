from collections.abc import Mapping

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import IntegrityError, transaction
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param
from rest_framework.views import APIView

from .errors import EmailTaken, InvalidCredentials
from .selectors import list_user_weight_entries
from .serializers import (
    AccountSerializer,
    CredentialsSerializer,
    LeaderboardSettingsSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileCreateSerializer,
    ProfileResponseSerializer,
    ProfileUpdateSerializer,
    RegistrationSerializer,
    WeightEntryQuerySerializer,
    WeightEntrySerializer,
)
from .services import PasswordResetService, ProfileService
from .throttling import (
    PasswordResetConfirmIPThrottle,
    PasswordResetEmailThrottle,
    PasswordResetIPThrottle,
)

User = get_user_model()


def require_mapping_payload(data):
    if not isinstance(data, Mapping):
        raise ValidationError({"non_field_errors": ["Очікується JSON-об'єкт."]})
    return data


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


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = ProfileService.get_profile(request.user)
        return Response(
            ProfileResponseSerializer(profile).data, status=status.HTTP_200_OK
        )

    def post(self, request):
        serializer = ProfileCreateSerializer(data=require_mapping_payload(request.data))
        serializer.is_valid(raise_exception=True)
        profile = ProfileService.create_profile(request.user, serializer.validated_data)
        return Response(
            ProfileResponseSerializer(profile).data, status=status.HTTP_201_CREATED
        )

    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            data=require_mapping_payload(request.data), partial=True
        )
        serializer.is_valid(raise_exception=True)
        profile = ProfileService.update_profile(request.user, serializer.validated_data)
        return Response(
            ProfileResponseSerializer(profile).data, status=status.HTTP_200_OK
        )


class WeightEntryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query_data = {
            k: v[0] if len(v) == 1 else v for k, v in request.query_params.lists()
        }
        query_serializer = WeightEntryQuerySerializer(data=query_data)
        query_serializer.is_valid(raise_exception=True)
        start_date = query_serializer.validated_data.get("start_date")
        end_date = query_serializer.validated_data.get("end_date")
        page = query_serializer.validated_data["page"]
        page_size = query_serializer.validated_data["page_size"]

        queryset = list_user_weight_entries(
            user=request.user, start_date=start_date, end_date=end_date
        )
        total_count = queryset.count()
        if total_count == 0:
            if page > 1:
                raise ValidationError(
                    {"page": ["Сторінка виходить за межі наявних результатів."]}
                )
            return Response(
                {"count": 0, "next": None, "previous": None, "results": []},
                status=status.HTTP_200_OK,
            )

        offset = (page - 1) * page_size
        if offset >= total_count:
            raise ValidationError(
                {"page": ["Сторінка виходить за межі наявних результатів."]}
            )

        items = list(queryset[offset : offset + page_size])
        base_url = request.build_absolute_uri()
        next_url = (
            replace_query_param(base_url, "page", page + 1)
            if offset + page_size < total_count
            else None
        )
        previous_url = (
            None if page == 1 else replace_query_param(base_url, "page", page - 1)
        )
        return Response(
            {
                "count": total_count,
                "next": next_url,
                "previous": previous_url,
                "results": WeightEntrySerializer(items, many=True).data,
            },
            status=status.HTTP_200_OK,
        )
