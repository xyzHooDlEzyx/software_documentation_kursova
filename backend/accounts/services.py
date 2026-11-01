from django.conf import settings
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.exceptions import ValidationError

from .errors import ResetTokenInvalidOrExpired

User = get_user_model()


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
