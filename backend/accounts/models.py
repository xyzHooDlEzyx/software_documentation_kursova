from decimal import Decimal

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.functions import Length, Lower, Trim
from django.db.models.lookups import GreaterThan
from django.utils import timezone

from .managers import UserManager


class Gender(models.TextChoices):
    MALE = "male", "male"
    FEMALE = "female", "female"
    OTHER = "other", "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say", "prefer_not_to_say"


class FitnessGoal(models.TextChoices):
    WEIGHT_LOSS = "weight_loss", "weight_loss"
    MUSCLE_GAIN = "muscle_gain", "muscle_gain"
    MAINTENANCE = "maintenance", "maintenance"


class ExperienceLevel(models.TextChoices):
    BEGINNER = "beginner", "beginner"
    INTERMEDIATE = "intermediate", "intermediate"
    ADVANCED = "advanced", "advanced"


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=254)
    registered_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    public_alias = models.CharField(max_length=80, null=True, blank=True)
    leaderboard_opt_in = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        constraints = [
            models.UniqueConstraint(Lower("email"), name="users_email_lower_unique"),
            models.CheckConstraint(
                condition=models.Q(leaderboard_opt_in=False)
                | (
                    models.Q(public_alias__isnull=False)
                    & GreaterThan(Length(Trim("public_alias")), 0)
                ),
                name="users_opt_in_alias_required",
            ),
        ]
        permissions = [("deactivate_user", "Can deactivate user accounts")]

    def __str__(self):
        return self.email


class Profile(models.Model):
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="profile",
    )
    first_name = models.CharField(max_length=150, blank=True, default="", db_default="")
    last_name = models.CharField(max_length=150, blank=True, default="", db_default="")
    date_of_birth = models.DateField()
    weight_kg = models.DecimalField(max_digits=4, decimal_places=1)
    height_cm = models.DecimalField(max_digits=4, decimal_places=1)
    gender = models.CharField(max_length=20, choices=Gender.choices)
    fitness_goal = models.CharField(max_length=20, choices=FitnessGoal.choices)
    experience_level = models.CharField(max_length=20, choices=ExperienceLevel.choices)
    workouts_per_week = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "profiles"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(weight_kg__gte=Decimal("20.0"))
                & models.Q(weight_kg__lte=Decimal("500.0")),
                name="profiles_weight_kg_range",
            ),
            models.CheckConstraint(
                condition=models.Q(height_cm__gte=Decimal("100.0"))
                & models.Q(height_cm__lte=Decimal("250.0")),
                name="profiles_height_cm_range",
            ),
            models.CheckConstraint(
                condition=models.Q(workouts_per_week__gte=1)
                & models.Q(workouts_per_week__lte=7),
                name="profiles_workouts_per_week_range",
            ),
            models.CheckConstraint(
                condition=models.Q(gender__in=Gender.values),
                name="profiles_gender_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(fitness_goal__in=FitnessGoal.values),
                name="profiles_fitness_goal_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(experience_level__in=ExperienceLevel.values),
                name="profiles_experience_level_valid",
            ),
        ]

    def __str__(self):
        return f"Profile({self.user_id})"


class WeightEntry(models.Model):
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="weight_entries",
    )
    measured_at = models.DateTimeField()
    weight_kg = models.DecimalField(max_digits=4, decimal_places=1)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "weight_entries"
        ordering = ["-measured_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(weight_kg__gte=Decimal("20.0"))
                & models.Q(weight_kg__lte=Decimal("500.0")),
                name="weight_entries_weight_kg_range",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "-measured_at", "-id"],
                name="weight_entries_user_meas_idx",
            ),
        ]

    def __str__(self):
        return (
            f"WeightEntry(user={self.user_id}, {self.weight_kg}kg @ {self.measured_at})"
        )
