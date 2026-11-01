from datetime import timezone as dt_timezone
from decimal import Decimal

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .errors import UnknownField
from .models import ExperienceLevel, FitnessGoal, Gender, Profile, WeightEntry
from .services import ProfileService

User = get_user_model()


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = sorted(set(data) - set(self.fields))
            if unknown:
                raise UnknownField(unknown)
        return super().to_internal_value(data)


class StrictIntegerField(serializers.IntegerField):
    def to_internal_value(self, data):
        if isinstance(data, (bool, float)):
            self.fail("invalid")
        return super().to_internal_value(data)


class StrictDecimalField(serializers.DecimalField):
    def to_internal_value(self, data):
        if isinstance(data, bool):
            self.fail("invalid")
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


class ProfileCreateSerializer(StrictSerializer):
    first_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=False,
    )
    last_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=False,
    )
    date_of_birth = serializers.DateField()
    weight_kg = StrictDecimalField(
        max_digits=4,
        decimal_places=1,
        min_value=Decimal("20.0"),
        max_value=Decimal("500.0"),
        coerce_to_string=True,
    )
    height_cm = StrictDecimalField(
        max_digits=4,
        decimal_places=1,
        min_value=Decimal("100.0"),
        max_value=Decimal("250.0"),
        coerce_to_string=True,
    )
    gender = serializers.ChoiceField(choices=Gender.choices)
    fitness_goal = serializers.ChoiceField(choices=FitnessGoal.choices)
    experience_level = serializers.ChoiceField(choices=ExperienceLevel.choices)
    workouts_per_week = StrictIntegerField(min_value=1, max_value=7)


class ProfileUpdateSerializer(StrictSerializer):
    first_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True, trim_whitespace=False
    )
    last_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True, trim_whitespace=False
    )
    date_of_birth = serializers.DateField(required=False)
    weight_kg = StrictDecimalField(
        max_digits=4,
        decimal_places=1,
        min_value=Decimal("20.0"),
        max_value=Decimal("500.0"),
        coerce_to_string=True,
        required=False,
    )
    height_cm = StrictDecimalField(
        max_digits=4,
        decimal_places=1,
        min_value=Decimal("100.0"),
        max_value=Decimal("250.0"),
        coerce_to_string=True,
        required=False,
    )
    gender = serializers.ChoiceField(choices=Gender.choices, required=False)
    fitness_goal = serializers.ChoiceField(choices=FitnessGoal.choices, required=False)
    experience_level = serializers.ChoiceField(
        choices=ExperienceLevel.choices, required=False
    )
    workouts_per_week = StrictIntegerField(min_value=1, max_value=7, required=False)


class ProfileResponseSerializer(serializers.ModelSerializer):
    age = serializers.SerializerMethodField()
    weight_kg = serializers.DecimalField(
        max_digits=4, decimal_places=1, coerce_to_string=True, read_only=True
    )
    height_cm = serializers.DecimalField(
        max_digits=4, decimal_places=1, coerce_to_string=True, read_only=True
    )

    def get_age(self, obj: Profile) -> int:
        return ProfileService.calculate_age(obj.date_of_birth)

    class Meta:
        model = Profile
        fields = (
            "first_name",
            "last_name",
            "date_of_birth",
            "age",
            "weight_kg",
            "height_cm",
            "gender",
            "fitness_goal",
            "experience_level",
            "workouts_per_week",
        )
        read_only_fields = fields


class WeightEntrySerializer(serializers.ModelSerializer):
    measured_at = serializers.DateTimeField(
        format="%Y-%m-%dT%H:%M:%SZ", default_timezone=dt_timezone.utc, read_only=True
    )
    weight_kg = serializers.DecimalField(
        max_digits=4, decimal_places=1, coerce_to_string=True, read_only=True
    )

    class Meta:
        model = WeightEntry
        fields = ("id", "measured_at", "weight_kg")
        read_only_fields = fields


class WeightEntryQuerySerializer(StrictSerializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    page = StrictIntegerField(min_value=1, required=False, default=1)
    page_size = StrictIntegerField(
        min_value=1, max_value=100, required=False, default=20
    )

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if (start_date is None) != (end_date is None):
            if start_date is None:
                raise serializers.ValidationError(
                    {
                        "start_date": [
                            "Поле start_date є обов'язковим при передачі end_date."
                        ]
                    }
                )
            raise serializers.ValidationError(
                {"end_date": ["Поле end_date є обов'язковим при передачі start_date."]}
            )
        if start_date is not None and end_date is not None and start_date >= end_date:
            raise serializers.ValidationError(
                {
                    "end_date": [
                        "Кінцева дата має бути пізнішою за початкову "
                        "(start_date < end_date)."
                    ]
                }
            )
        return attrs
