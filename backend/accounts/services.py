from collections.abc import Mapping
from datetime import date
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.exceptions import NotAuthenticated, ValidationError

from .errors import ProfileExists, ProfileMissing, ResetTokenInvalidOrExpired
from .models import Profile, WeightEntry

User = get_user_model()

KYIV_TZ = ZoneInfo("Europe/Kyiv")


class PasswordResetService:
    def __init__(self, token_generator=default_token_generator):
        self.token_generator = token_generator

    def request_reset(self, email: str) -> None:
        normalized_email = User.objects.normalize_email(email)
        user = User.objects.filter(email__iexact=normalized_email).first()
        if user is not None and user.is_active and user.has_usable_password():
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = self.token_generator.make_token(user)
            reset_url = (
                f"{settings.FRONTEND_ORIGIN.rstrip('/')}/reset-password/{uid}/{token}"
            )
            timeout_minutes = max(
                1, int(getattr(settings, "PASSWORD_RESET_TIMEOUT", 3600)) // 60
            )
            context = {
                "reset_url": reset_url,
                "timeout_minutes": timeout_minutes,
            }
            subject = "".join(
                render_to_string(
                    "accounts/emails/password_reset_subject.txt", context
                ).splitlines()
            ).strip()
            body = render_to_string("accounts/emails/password_reset_body.txt", context)
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        else:
            self.token_generator.make_token(
                User(pk=0, email=normalized_email, password="!unusable")
            )

    def confirm_reset(self, uid: str, token: str, new_password: str) -> None:
        try:
            raw_pk = force_str(urlsafe_base64_decode(uid))
            user_pk = int(raw_pk)
            if user_pk <= 0:
                raise ValueError
        except (TypeError, ValueError, OverflowError, UnicodeDecodeError) as exc:
            raise ResetTokenInvalidOrExpired() from exc

        with transaction.atomic():
            user = User.objects.select_for_update().filter(pk=user_pk).first()
            if user is None or not user.is_active or not user.has_usable_password():
                raise ResetTokenInvalidOrExpired()
            if not self.token_generator.check_token(user, token):
                raise ResetTokenInvalidOrExpired()
            try:
                password_validation.validate_password(new_password, user)
            except DjangoValidationError as exc:
                raise ValidationError({"new_password": list(exc.messages)}) from exc
            user.set_password(new_password)
            user.save(update_fields=["password"])

    requestReset = request_reset
    confirmReset = confirm_reset


class ProfileService:
    KYIV_TZ = KYIV_TZ
    UPDATABLE_FIELDS = (
        "first_name",
        "last_name",
        "date_of_birth",
        "weight_kg",
        "height_cm",
        "gender",
        "fitness_goal",
        "experience_level",
        "workouts_per_week",
    )

    @staticmethod
    def calculate_age(date_of_birth: date, on_date: date | None = None) -> int:
        if on_date is None:
            on_date = timezone.now().astimezone(KYIV_TZ).date()
        return (
            on_date.year
            - date_of_birth.year
            - ((on_date.month, on_date.day) < (date_of_birth.month, date_of_birth.day))
        )

    @staticmethod
    def validate_age_on_date(date_of_birth: date, reference_date: date) -> int:
        age = ProfileService.calculate_age(date_of_birth, on_date=reference_date)
        if age < 19 or age > 59:
            raise ValidationError(
                {"date_of_birth": ["Вік має бути від 19 до 59 років включно."]}
            )
        return age

    @staticmethod
    def get_profile(user: User) -> Profile:
        profile = Profile.objects.filter(user=user).first()
        if profile is None:
            raise ProfileMissing()
        return profile

    @staticmethod
    def create_profile(user: User, data: Mapping[str, Any]) -> Profile:
        with transaction.atomic():
            locked_user = User.objects.select_for_update().get(pk=user.pk)
            if not locked_user.is_active:
                raise NotAuthenticated()
            if Profile.objects.filter(user=locked_user).exists():
                raise ProfileExists()
            now = timezone.now()
            creation_local_date = now.astimezone(KYIV_TZ).date()
            ProfileService.validate_age_on_date(
                data["date_of_birth"], creation_local_date
            )
            try:
                profile = Profile.objects.create(
                    user=locked_user,
                    first_name=data.get("first_name", ""),
                    last_name=data.get("last_name", ""),
                    date_of_birth=data["date_of_birth"],
                    weight_kg=data["weight_kg"],
                    height_cm=data["height_cm"],
                    gender=data["gender"],
                    fitness_goal=data["fitness_goal"],
                    experience_level=data["experience_level"],
                    workouts_per_week=data["workouts_per_week"],
                    created_at=now,
                )
            except IntegrityError as exc:
                raise ProfileExists() from exc
            WeightEntry.objects.create(
                user=locked_user,
                weight_kg=profile.weight_kg,
                measured_at=now,
                created_at=now,
            )
            return profile

    @staticmethod
    def update_profile(user: User, data: Mapping[str, Any]) -> Profile:
        with transaction.atomic():
            locked_user = User.objects.select_for_update().get(pk=user.pk)
            if not locked_user.is_active:
                raise NotAuthenticated()
            profile = (
                Profile.objects.select_for_update().filter(user=locked_user).first()
            )
            if profile is None:
                raise ProfileMissing()
            if "date_of_birth" in data:
                creation_local_date = profile.created_at.astimezone(KYIV_TZ).date()
                ProfileService.validate_age_on_date(
                    data["date_of_birth"], creation_local_date
                )
            old_weight = profile.weight_kg
            updated_fields: list[str] = []
            for field in ProfileService.UPDATABLE_FIELDS:
                if field in data:
                    setattr(profile, field, data[field])
                    updated_fields.append(field)
            if updated_fields:
                profile.save(update_fields=updated_fields)
            if "weight_kg" in data and profile.weight_kg != old_weight:
                now = timezone.now()
                WeightEntry.objects.create(
                    user=locked_user,
                    weight_kg=profile.weight_kg,
                    measured_at=now,
                    created_at=now,
                )
            return profile

    createProfile = create_profile
    updateProfile = update_profile
    updateProfileAndWeight = update_profile
