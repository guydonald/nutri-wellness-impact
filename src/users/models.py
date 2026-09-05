from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid

class CustomUserManager(BaseUserManager):
    def create_user(self, email, role="patient", password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, role="dietitian", password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, role, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(unique=True, max_length=254)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(
        max_length=20,
        choices=[
            ('patient', _('Patient')),
            ('dietitian', _('Dietitian')),
        ],
        default='patient'
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["role"]

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.email} ({_(self.role)})"

    def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.email

    def get_short_name(self):
        return self.first_name or self.email

