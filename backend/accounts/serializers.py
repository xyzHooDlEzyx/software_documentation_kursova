from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .errors import UnknownField

User = get_user_model()


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = sorted(set(data) - set(self.fields))
            if unknown:
                raise UnknownField(unknown)
        return super().to_internal_value(data)


class CredentialsSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(trim_whitespace=False, write_only=True)

    def validate_email(self, value):
        return User.objects.normalize_email(value)


class RegistrationSerializer(CredentialsSerializer):
    def validate(self, attrs):
        candidate = User(email=attrs["email"])
        try:
            password_validation.validate_password(attrs["password"], candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "public_alias", "leaderboard_opt_in")
        read_only_fields = fields


class LeaderboardSettingsSerializer(StrictSerializer):
    public_alias = serializers.CharField(
        max_length=80, allow_null=True, allow_blank=True, required=False
    )
    leaderboard_opt_in = serializers.BooleanField(required=False)

    def validate(self, attrs):
        user = self.context["request"].user
        alias = attrs.get("public_alias", user.public_alias)
        opt_in = attrs.get("leaderboard_opt_in", user.leaderboard_opt_in)
        if opt_in and (alias is None or not alias.strip()):
            raise serializers.ValidationError(
                {"public_alias": ["Для участі в рейтингу потрібен псевдонім."]}
            )
        return attrs


class PasswordResetRequestSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=254)

    def validate_email(self, value):
        return User.objects.normalize_email(value)


class PasswordResetConfirmSerializer(StrictSerializer):
    uid = serializers.CharField(max_length=128, trim_whitespace=True)
    token = serializers.CharField(max_length=256, trim_whitespace=True)
    new_password = serializers.CharField(trim_whitespace=False, write_only=True)
