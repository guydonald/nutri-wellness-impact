from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import uuid


# -----------------------------
# Utilisateur personnalisé
# -----------------------------
class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, default="default@example.com")
    username = None
    role = models.CharField(
        max_length=20,
        choices=[
            ('patient', _('Patient')),
            ('dietitian', _('Dietitian')),
        ],
        default='patient'
    )
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["role"]

    def __str__(self):
        return f"{self.email} ({_(self.role)})"
