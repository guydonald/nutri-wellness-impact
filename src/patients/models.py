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

    age = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Age"))
    gender = models.CharField(
        max_length=10,
        choices=[
            ('Male', _('Male')),
            ('Female', _('Female')),
        ],
        verbose_name=_("Gender")
    )
    occupation = models.CharField(max_length=100, blank=True, verbose_name=_("Occupation"))
    activity_level = models.CharField(
        max_length=20,
        choices=[
            ('sedentary', _('Sedentary')),
            ('low', _('Low activity')),
            ('moderate', _('Moderate activity')),
            ('intense', _('Intense activity')),
        ],
        verbose_name=_("Activity level")
    )

    diagnosis = models.CharField(max_length=255, blank=True, verbose_name=_("Diagnosis"))
    diagnosis_date = models.DateField(null=True, blank=True, verbose_name=_("Diagnosis date"))
    medical_history = models.TextField(blank=True, verbose_name=_("Medical history"))
    medications = models.TextField(blank=True, verbose_name=_("Medications"))
    allergies = models.BooleanField(default=False, verbose_name=_("Allergies"))
    family_history_cvd = models.BooleanField(default=False, verbose_name=_("Family history of CVD"))

    height = models.FloatField(null=True, blank=True, verbose_name=_("Height (cm)"))
    weight = models.FloatField(null=True, blank=True, verbose_name=_("Weight (kg)"))
    bmi = models.FloatField(null=True, blank=True, verbose_name=_("BMI"))
    waist_circumference = models.FloatField(null=True, blank=True, verbose_name=_("Waist circumference"))
    body_fat_percent = models.FloatField(null=True, blank=True, verbose_name=_("Body fat (%)"))

    def save(self, *args, **kwargs):
        if self.weight and self.height:
            h = self.height / 100 if self.height > 3 else self.height
            self.bmi = round(self.weight / (h * h), 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return _("Profile of %(email)s") % {"email": self.user.email}


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
    date_consultation = models.DateField(auto_now_add=True, verbose_name=_("Consultation date"))

    blood_pressure = models.CharField(max_length=20, blank=True, verbose_name=_("Blood pressure"))
    total_cholesterol = models.FloatField(null=True, blank=True, verbose_name=_("Total cholesterol"))
    ldl = models.FloatField(null=True, blank=True, verbose_name=_("LDL"))
    hdl = models.FloatField(null=True, blank=True, verbose_name=_("HDL"))
    triglycerides = models.FloatField(null=True, blank=True, verbose_name=_("Triglycerides"))
    hba1c = models.FloatField(null=True, blank=True, verbose_name=_("HbA1c (%)"))
    weight = models.FloatField(verbose_name=_("Weight (kg)"), null=True, blank=True)

    nutritional_diagnosis = models.TextField(verbose_name=_("Nutritional Diagnosis (PES)"))
    goals = models.TextField(verbose_name=_("Nutritional goals"))
    intervention_plan = models.TextField(verbose_name=_("Intervention plan"))

    next_appointment = models.DateField(null=True, blank=True, verbose_name=_("Follow-up date"))

    @property
    def bmi(self):
        if self.weight and self.patient_profile and self.patient_profile.height:
            h = self.patient_profile.height / 100 if self.patient_profile.height > 3 else self.patient_profile.height
            return round(self.weight / (h ** 2), 1)
        return None

    @property
    def bmi_status(self):
        val = self.bmi
        if not val:
            return {"label": _("Unknown"), "color": "secondary"}
        if val < 18.5:
            return {"label": _("Underweight"), "color": "info"}
        if val < 25:
            return {"label": _("Normal"), "color": "success"}
        if val < 30:
            return {"label": _("Overweight"), "color": "warning"}
        return {"label": _("Obesity"), "color": "danger"}

    def __str__(self):
        return _("Consultation of %(email)s - %(date)s") % {"email": self.patient.email, "date": self.date_consultation}


# -----------------------------
# Plan Alimentaire
# -----------------------------
class MealPlan(models.Model):
    DAYS = [
        ('1', _('Day 1')), ('2', _('Day 2')), ('3', _('Day 3')),
        ('4', _('Day 4')), ('5', _('Day 5')), ('6', _('Day 6')), ('7', _('Day 7'))
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meal_plans')
    day = models.CharField(max_length=1, choices=DAYS)

    breakfast = models.TextField(verbose_name=_("Breakfast"))
    morning_snack = models.TextField(verbose_name=_("Morning snack"), blank=True)
    lunch = models.TextField(verbose_name=_("Lunch"))
    afternoon_snack = models.TextField(verbose_name=_("Afternoon snack"), blank=True)
    dinner = models.TextField(verbose_name=_("Dinner"))
    evening_snack = models.TextField(verbose_name=_("Evening snack"), blank=True)

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
            ('breakfast', _('Breakfast')),
            ('snack_am', _('Morning snack')),
            ('lunch', _('Lunch')),
            ('snack_pm', _('Afternoon snack')),
            ('dinner', _('Dinner')),
        ],
        verbose_name=_("Meal time")
    )
    description = models.TextField(verbose_name=_("What did you eat?"))
    beverage = models.BooleanField(default=False, verbose_name=_("Sugary drink consumed?"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes_generales = models.TextField(verbose_name=_("General instructions"), blank=True)
    is_active = models.BooleanField(default=True, verbose_name=_("Current plan"))

    class Meta:
        verbose_name = _("Meal plan")
        ordering = ['-date']

    def __str__(self):
        return _("%(email)s - %(date)s - %(meal)s") % {
            "email": self.patient.email,
            "date": self.date,
            "meal": self.get_meal_time_display()
        }