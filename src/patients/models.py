from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import uuid

# -----------------------------
# Profil Patient
# -----------------------------
class PatientProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')

    age = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Âge"))
    gender = models.CharField(
        max_length=10,
        choices=[
            ('Male', _('Homme')),
            ('Female', _('Femme')),
        ],
        verbose_name=_("Sexe")
    )
    occupation = models.CharField(max_length=100, blank=True, verbose_name=_("Profession"))
    activity_level = models.CharField(
        max_length=20,
        choices=[
            ('sedentary', _('Sédentaire')),
            ('low', _('Faible activité')),
            ('moderate', _('Activité modérée')),
            ('intense', _('Activité intense')),
        ],
        verbose_name=_("Niveau d'activité")
    )

    diagnosis = models.CharField(max_length=255, blank=True, verbose_name=_("Diagnostic"))
    diagnosis_date = models.DateField(null=True, blank=True, verbose_name=_("Date du diagnostic"))
    medical_history = models.TextField(blank=True, verbose_name=_("Antécédents médicaux"))
    medications = models.TextField(blank=True, verbose_name=_("Médicaments"))
    allergies = models.BooleanField(default=False, verbose_name=_("Allergies"))
    family_history_cvd = models.BooleanField(default=False, verbose_name=_("Antécédents familiaux de MCV"))

    height = models.FloatField(null=True, blank=True, verbose_name=_("Taille (cm)"))
    weight = models.FloatField(null=True, blank=True, verbose_name=_("Poids (kg)"))
    bmi = models.FloatField(null=True, blank=True, verbose_name=_("IMC"))
    waist_circumference = models.FloatField(null=True, blank=True, verbose_name=_("Tour de taille"))
    body_fat_percent = models.FloatField(null=True, blank=True, verbose_name=_("Masse grasse (%)"))

    def save(self, *args, **kwargs):
        if self.weight and self.height:
            h = self.height / 100 if self.height > 3 else self.height
            self.bmi = round(self.weight / (h * h), 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return _("Profil de %(email)s") % {"email": self.user.email}


# -----------------------------
# Consultation
# -----------------------------
class Consultation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient_profile = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, null=True, blank=True)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='consultations')
    dietitian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dietitian_consultations',
        limit_choices_to={'role': 'dietitian'}
    )
    date_consultation = models.DateField(auto_now_add=True, verbose_name=_("Date de consultation"))

    blood_pressure = models.CharField(max_length=20, blank=True, verbose_name=_("Tension artérielle"))
    total_cholesterol = models.FloatField(null=True, blank=True, verbose_name=_("Cholestérol total"))
    ldl = models.FloatField(null=True, blank=True, verbose_name=_("LDL"))
    hdl = models.FloatField(null=True, blank=True, verbose_name=_("HDL"))
    triglycerides = models.FloatField(null=True, blank=True, verbose_name=_("Triglycérides"))
    hba1c = models.FloatField(null=True, blank=True, verbose_name=_("HbA1c (%)"))
    weight = models.FloatField(verbose_name=_("Poids (kg)"), null=True, blank=True)

    nutritional_diagnosis = models.TextField(verbose_name=_("Diagnostic Nutritionnel (PES)"))
    goals = models.TextField(verbose_name=_("Objectifs nutritionnels"))
    intervention_plan = models.TextField(verbose_name=_("Plan d'intervention"))

    next_appointment = models.DateField(null=True, blank=True, verbose_name=_("Date de suivi"))

    @property
    def bmi(self):
        if self.weight and self.patient_profile.height:
            h = self.patient_profile.height / 100 if self.patient_profile.height > 3 else self.patient_profile.height
            return round(self.weight / (h ** 2), 1)
        return None

    @property
    def bmi_status(self):
        val = self.bmi
        if not val: return {"label": _("Inconnu"), "color": "secondary"}
        if val < 18.5: return {"label": _("Insuffisance pondérale"), "color": "info"}
        if val < 25: return {"label": _("Normal"), "color": "success"}
        if val < 30: return {"label": _("Surpoids"), "color": "warning"}
        return {"label": _("Obésité"), "color": "danger"}

    def __str__(self):
        return _("Consultation de %(email)s - %(date)s") % {"email": self.patient.email, "date": self.date_consultation}


# -----------------------------
# Plan Alimentaire
# -----------------------------
class MealPlan(models.Model):
    DAYS = [
        ('1', _('Jour 1')), ('2', _('Jour 2')), ('3', _('Jour 3')),
        ('4', _('Jour 4')), ('5', _('Jour 5')), ('6', _('Jour 6')), ('7', _('Jour 7'))
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meal_plans')
    day = models.CharField(max_length=1, choices=DAYS)

    breakfast = models.TextField(verbose_name=_("Petit-déjeuner"))
    morning_snack = models.TextField(verbose_name=_("Collation Matin"), blank=True)
    lunch = models.TextField(verbose_name=_("Déjeuner"))
    afternoon_snack = models.TextField(verbose_name=_("Collation Après-midi"), blank=True)
    dinner = models.TextField(verbose_name=_("Dîner"))
    evening_snack = models.TextField(verbose_name=_("Collation Soir"), blank=True)

    class Meta:
        unique_together = ['patient', 'day']
        ordering = ['day']

    def __str__(self):
        return _("Plan %(day)s - %(email)s") % {"day": self.get_day_display(), "email": self.patient.email}


# -----------------------------
# Journal Alimentaire
# -----------------------------
class FoodDiary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='food_entries')
    date = models.DateField(auto_now_add=True, verbose_name=_("Date"))
    meal_time = models.CharField(
        max_length=20,
        choices=[
            ('breakfast', _('Petit-déjeuner')),
            ('snack_am', _('Collation Matin')),
            ('lunch', _('Déjeuner')),
            ('snack_pm', _('Collation Après-midi')),
            ('dinner', _('Dîner')),
        ],
        verbose_name=_("Moment du repas")
    )
    description = models.TextField(verbose_name=_("Qu'avez-vous mangé ?"))
    beverage = models.BooleanField(default=False, verbose_name=_("Consommation de boisson sucrée ?"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes_generales = models.TextField(verbose_name=_("Instructions globales"), blank=True)
    is_active = models.BooleanField(default=True, verbose_name=_("Plan actuel"))

    class Meta:
        verbose_name = _("Plan alimentaire")
        ordering = ['-date'] # Pour que ça s'affiche du Jour 1 au Jour 7

    def __str__(self):
        return _("%(email)s - %(date)s - %(meal)s") % {
            "email": self.patient.email,
            "date": self.date,
            "meal": self.get_meal_time_display()
        }