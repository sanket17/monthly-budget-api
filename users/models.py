from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import CustomUserManager


class CustomUser(AbstractUser):
    """
    Custom user model for Personal Budget.

    Email is the login credential (USERNAME_FIELD).
    username field is kept (AbstractUser requires it) but set to mirror email.

    CRITICAL: AUTH_USER_MODEL = 'users.CustomUser' must be set in settings
    BEFORE this model's first migration runs. Never change AUTH_USER_MODEL
    after initial migrate.

    Extend this model in future phases for profile fields (e.g., currency preference).
    """

    email = models.EmailField(unique=True)

    # email is the login identifier
    USERNAME_FIELD = "email"

    # REQUIRED_FIELDS must NOT include USERNAME_FIELD.
    # Empty list means only email + password are required for createsuperuser.
    # Django system check error if 'email' appears here.
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        db_table = "users"
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.email
