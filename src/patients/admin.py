from django.contrib import admin, messages
from django.core.management import call_command
from django.conf import settings
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import Truncator

from .models import (
    Consultation, FoodDiary, InboxMessage, InboxReply, MealPlan, PatientProfile, QueuedEmail,
)


# =========================================================
#  Petits utilitaires d'affichage
# =========================================================
def badge(text, color):
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 10px;border-radius:20px;'
        'font-size:11px;font-weight:700;white-space:nowrap;">{}</span>', color, text)


def patient_link(user):
    if not user:
        return "—"
    url = reverse("admin:users_customuser_change", args=[user.pk])
    name = f"{user.first_name} {user.last_name}".strip() or user.email
    return format_html('<a href="{}">{}</a>', url, name)


def short(text, n=80):
    return Truncator(text or "").chars(n) or "—"


# =========================================================
#  PROFIL PATIENT (bilan initial)
# =========================================================
class ConsultationInline(admin.TabularInline):
    model = Consultation
    fk_name = "patient_profile"
    extra = 0
    fields = ("date_consultation", "weight", "blood_pressure", "heart_rate", "dietitian", "next_appointment")
    readonly_fields = ("date_consultation",)
    show_change_link = True
    verbose_name = "Consultation"
    verbose_name_plural = "Consultations de ce patient"


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("patient", "email", "age", "gender", "pathology", "imc", "updated_at")
    list_filter = ("pathology", "gender", "activity_level", "meal_place", "updated_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "phone")
    list_select_related = ("user",)
    date_hierarchy = "updated_at"
    list_per_page = 30
    readonly_fields = ("user", "bmi", "created_at", "updated_at")
    inlines = [ConsultationInline]

    fieldsets = (
        ("1. Informations personnelles", {"fields": (
            "user", ("birth_date", "age", "gender"), ("phone", "occupation"), "address")}),
        ("2. Motif de consultation", {"fields": ("pathology", "consultation_reason", "reason_comment")}),
        ("3. Antécédents médicaux", {"classes": ("collapse",), "fields": (
            ("diagnosis", "diagnosis_date"), "known_diseases", "medical_history", "family_history",
            "previous_surgeries", "medications", ("allergies", "family_history_cvd"),
            "food_allergies", "food_intolerances")}),
        ("4. Habitudes de vie", {"classes": ("collapse",), "fields": (
            ("sleep_hours", "sleep_quality"), ("activity_level", "activity_type"),
            ("activity_frequency", "activity_duration"), ("stress_level", "stress_sources"),
            ("smoking", "smoking_frequency"), ("alcohol", "alcohol_frequency"),
            ("sweets", "sweets_frequency"))}),
        ("5. Mesures", {"fields": (
            ("height", "weight", "bmi"), ("usual_weight", "desired_weight"),
            ("waist_circumference", "hip_circumference", "body_fat_percent"),
            ("blood_pressure_left", "blood_pressure_right"), "other_measures")}),
        ("6. Habitudes alimentaires et hydratation", {"classes": ("collapse",), "fields": (
            ("meals_per_day", "has_snacks"), ("breakfast_time", "lunch_time", "dinner_time", "snack_times"),
            ("meal_place", "eat_with"),
            "typical_breakfast", "typical_morning_snack", "typical_lunch",
            "typical_afternoon_snack", "typical_dinner", "typical_evening_snack",
            ("fruits_consumption", "vegetables_consumption", "fatty_sugary_consumption"),
            ("water_glasses", "water_liters"), "other_drinks")}),
        ("7. Relation à l'alimentation et objectifs", {"classes": ("collapse",), "fields": (
            ("appetite", "snacking"), "snacking_moments", "dietary_restrictions", "eating_behaviors",
            "main_expectations", ("goal_timeframe", "motivation_level"))}),
        ("8. Notes de la nutritionniste", {"classes": ("collapse",), "fields": (
            "practitioner_notes", "nutritional_diagnosis", "risk_factors",
            "proposed_dietary_plan", "specific_advice", "next_appointment")}),
        ("Dates", {"fields": (("created_at", "updated_at"),)}),
    )

    @admin.display(description="Patient", ordering="user__last_name")
    def patient(self, obj):
        return patient_link(obj.user)

    @admin.display(description="E-mail", ordering="user__email")
    def email(self, obj):
        return obj.user.email

    @admin.display(description="IMC", ordering="bmi")
    def imc(self, obj):
        if not obj.bmi:
            return "—"
        colors = {"info": "#0dcaf0", "success": "#5a8f3d", "warning": "#f4a020", "danger": "#d62828"}
        status = obj.bmi_status
        return badge(f"{obj.bmi} · {status['label']}", colors.get(status["color"], "#999"))


# =========================================================
#  CONSULTATIONS
# =========================================================
@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ("date_consultation", "patient_name", "weight", "imc", "blood_pressure",
                    "alertes", "dietitian", "next_appointment")
    list_filter = ("date_consultation", "dietitian", "alert_rapid_weight_loss", "alert_fatigue",
                   "alert_wound", "alert_appetite_loss", "alert_edema")
    search_fields = ("patient__email", "patient__first_name", "patient__last_name")
    list_select_related = ("patient", "dietitian", "patient_profile")
    date_hierarchy = "date_consultation"
    list_per_page = 30
    autocomplete_fields = ("patient",)
    readonly_fields = ("date_consultation",)
    fieldsets = (
        ("Patient", {"fields": ("patient", "patient_profile", "dietitian", "date_consultation")}),
        ("Mesures cliniques", {"fields": (("weight", "heart_rate"), ("blood_pressure", "blood_pressure_right"))}),
        ("Bilan biologique", {"classes": ("collapse",), "fields": (
            ("total_cholesterol", "ldl", "hdl"), ("triglycerides", "hba1c"))}),
        ("Suivi", {"fields": ("appetite", "observations", ("edema", "wound_healing"),
                              ("salt_intake", "protein_intake"), ("hydration_level", "fruits_veg_intake"))}),
        ("Signes d'alerte", {"fields": (("alert_rapid_weight_loss", "alert_fatigue", "alert_wound"),
                                        ("alert_appetite_loss", "alert_edema"))}),
        ("Analyse et prescription", {"fields": ("nutritional_diagnosis", "goals", "intervention_plan",
                                                "next_appointment")}),
    )

    @admin.display(description="Patient", ordering="patient__last_name")
    def patient_name(self, obj):
        return patient_link(obj.patient)

    @admin.display(description="IMC")
    def imc(self, obj):
        return obj.bmi or "—"

    @admin.display(description="Alertes")
    def alertes(self, obj):
        return badge("Alerte", "#d62828") if obj.has_alerts else "—"


# =========================================================
#  PLAN ALIMENTAIRE ET JOURNAL
# =========================================================
@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = ("patient_name", "day", "petit_dejeuner", "dejeuner", "diner")
    list_filter = ("day",)
    search_fields = ("patient__email", "patient__first_name", "patient__last_name")
    list_select_related = ("patient",)
    ordering = ("patient__last_name", "day")

    @admin.display(description="Patient", ordering="patient__last_name")
    def patient_name(self, obj):
        return patient_link(obj.patient)

    @admin.display(description="Petit-déjeuner")
    def petit_dejeuner(self, obj):
        return short(obj.breakfast, 50)

    @admin.display(description="Déjeuner")
    def dejeuner(self, obj):
        return short(obj.lunch, 50)

    @admin.display(description="Dîner")
    def diner(self, obj):
        return short(obj.dinner, 50)


@admin.register(FoodDiary)
class FoodDiaryAdmin(admin.ModelAdmin):
    list_display = ("date", "patient_name", "meal_time", "repas", "beverage")
    list_filter = ("meal_time", "beverage", "date")
    search_fields = ("patient__email", "patient__first_name", "patient__last_name", "description")
    list_select_related = ("patient",)
    date_hierarchy = "date"
    list_per_page = 40

    @admin.display(description="Patient", ordering="patient__last_name")
    def patient_name(self, obj):
        return patient_link(obj.patient)

    @admin.display(description="Ce qui a été mangé")
    def repas(self, obj):
        return short(obj.description, 90)


# =========================================================
#  MESSAGES REÇUS
# =========================================================
class InboxReplyInline(admin.StackedInline):
    model = InboxReply
    extra = 0
    readonly_fields = ("author", "subject", "body", "created_at")
    can_delete = False
    verbose_name = "Réponse envoyée"
    verbose_name_plural = "Réponses envoyées"

    def has_add_permission(self, request, obj=None):
        return False  # on repond depuis l'application (page Messages), qui envoie l'e-mail


@admin.register(InboxMessage)
class InboxMessageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "type_badge", "expediteur", "apercu", "lu", "nb_reponses")
    list_filter = ("kind", "is_read", "created_at")
    search_fields = ("name", "email", "phone", "message")
    date_hierarchy = "created_at"
    list_per_page = 30
    readonly_fields = ("kind", "patient", "name", "email", "phone", "message", "created_at")
    fields = ("kind", "patient", ("name", "email", "phone"), "message", "is_read", "created_at")
    inlines = [InboxReplyInline]
    actions = ["marquer_lu", "marquer_non_lu"]

    @admin.display(description="Type", ordering="kind")
    def type_badge(self, obj):
        return badge("Bilan", "#5a8f3d") if obj.kind == "bilan" else badge("Contact", "#1d4f91")

    @admin.display(description="De")
    def expediteur(self, obj):
        return obj.name or obj.email or "—"

    @admin.display(description="Message")
    def apercu(self, obj):
        if obj.kind == "bilan":
            return "A rempli / mis à jour son bilan"
        return short(obj.message, 80)

    @admin.display(description="Lu", boolean=True, ordering="is_read")
    def lu(self, obj):
        return obj.is_read

    @admin.display(description="Réponses")
    def nb_reponses(self, obj):
        return obj.replies.count() or "—"

    @admin.action(description="Marquer comme lu")
    def marquer_lu(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description="Marquer comme non lu")
    def marquer_non_lu(self, request, queryset):
        queryset.update(is_read=False)


# =========================================================
#  HISTORIQUE DES E-MAILS
# =========================================================
@admin.register(QueuedEmail)
class QueuedEmailAdmin(admin.ModelAdmin):
    list_display = ("created_at", "sujet", "destinataires", "categorie", "statut", "sent_at", "attempts")
    list_filter = ("status", "category", "created_at")
    search_fields = ("subject", "to")
    date_hierarchy = "created_at"
    list_per_page = 50
    actions = ["renvoyer"]
    fieldsets = (
        (None, {"fields": ("subject", "from_email", "to", "category", "status")}),
        ("Contenu", {"fields": ("body", "body_erased")}),
        ("Envoi", {"fields": (("created_at", "sent_at"), ("attempts", "next_attempt_at"), "last_error")}),
    )

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]  # historique : lecture seule

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Sujet", ordering="subject")
    def sujet(self, obj):
        return short(obj.subject, 70)

    @admin.display(description="Destinataires")
    def destinataires(self, obj):
        return ", ".join(obj.to)

    @admin.display(description="Catégorie", ordering="category")
    def categorie(self, obj):
        return obj.get_category_display()

    @admin.display(description="Statut", ordering="status")
    def statut(self, obj):
        colors = {"pending": "#f4a020", "sent": "#5a8f3d", "failed": "#d62828"}
        return badge(obj.get_status_display(), colors.get(obj.status, "#999"))

    @admin.action(description="Renvoyer les e-mails sélectionnés")
    def renvoyer(self, request, queryset):
        erased = queryset.filter(body_erased=True).count()
        n = queryset.filter(body_erased=False).update(
            status=QueuedEmail.STATUS_PENDING, attempts=0, next_attempt_at=None, last_error="")
        if not getattr(settings, "EMAIL_QUEUE", False):
            call_command("process_email_queue")  # pas de tache en arriere-plan : on envoie tout de suite
        self.message_user(request, f"{n} e-mail(s) remis à l'envoi.", messages.SUCCESS)
        if erased:
            self.message_user(request, f"{erased} e-mail(s) de compte ignoré(s) : leur contenu (code) "
                                       "a été effacé par sécurité.", messages.WARNING)
