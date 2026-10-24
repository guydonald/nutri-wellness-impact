from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm
from django.urls import reverse
from django.utils.html import format_html

from .models import CustomUser


# ---------------------------------------------------------------
#  En-tetes de l'admin (s'applique a tout le site d'administration)
# ---------------------------------------------------------------
admin.site.site_header = "Nutri-Wellness Impact — Administration"
admin.site.site_title = "Nutri-Wellness Admin"
admin.site.index_title = "Tableau de bord"


class CustomUserCreationForm(BaseUserCreationForm):
    class Meta:
        model = CustomUser
        fields = ("email", "first_name", "last_name", "role")


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = "__all__"


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = ("nom", "email", "role_badge", "statut", "dossier", "date_joined", "last_login")
    list_display_links = ("nom", "email")
    list_filter = ("role", "is_active", "is_staff", "date_joined")
    search_fields = ("email", "first_name", "last_name", "phone_number")
    ordering = ("-date_joined",)
    date_hierarchy = "date_joined"
    list_per_page = 30
    readonly_fields = ("date_joined", "last_login", "updated_at")

    fieldsets = (
        ("Identité", {"fields": ("email", "first_name", "last_name", "phone_number", "profile_picture")}),
        ("Rôle et accès", {"fields": ("role", "is_active", "password"),
                           "description": "Un compte désactivé ne peut plus se connecter."}),
        ("Administration Django (réservé)", {"classes": ("collapse",),
                                              "fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("date_joined", "last_login", "updated_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "role", "password1", "password2")}),
    )

    @admin.display(description="Nom", ordering="last_name")
    def nom(self, obj):
        full = f"{obj.first_name} {obj.last_name}".strip()
        return full or "—"

    @admin.display(description="Rôle", ordering="role")
    def role_badge(self, obj):
        color = "#f4a020" if obj.role == "dietitian" else "#5a8f3d"
        return format_html('<span style="background:{};color:#fff;padding:2px 10px;border-radius:20px;'
                           'font-size:11px;font-weight:700;">{}</span>', color, obj.get_role_display())

    @admin.display(description="Compte", boolean=False, ordering="is_active")
    def statut(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#5a8f3d;font-weight:700;">{}</span>', "● Actif")
        return format_html('<span style="color:#999;font-weight:700;">{}</span>', "○ Désactivé")

    @admin.display(description="Dossier")
    def dossier(self, obj):
        if obj.role != "patient":
            return "—"
        profile = getattr(obj, "profile", None)
        if not profile:
            return format_html('<span style="color:#999;">{}</span>', "Pas de profil")
        url = reverse("admin:patients_patientprofile_change", args=[profile.pk])
        return format_html('<a href="{}">Voir le profil</a>', url)
