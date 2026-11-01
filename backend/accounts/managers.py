from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email):
        if not email or not email.strip():
            raise ValueError("Email is required.")
        return super().normalize_email(email.strip()).lower()

    def create_user(self, email, password=None, **extra_fields):
        if not password:
            raise ValueError("Password is required.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Superuser requires is_staff=True and is_superuser=True.")
        return self.create_user(email, password, **extra_fields)
