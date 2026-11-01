from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.functions import Length, Lower, Trim
from django.db.models.lookups import GreaterThan
from django.utils import timezone

from .managers import UserManager


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
