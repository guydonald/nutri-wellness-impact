from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _, pgettext_lazy
import uuid


# =========================================================
#  CHOIX PARTAGES
# =========================================================
NIVEAU_CHOICES = [
    ('low', _('Low')),
    ('medium', _('Medium')),
    ('high', _('High')),
]

FREQ_CHOICES = [
    ('rare', _('Rare')),
    ('sometimes', _('Sometimes')),
    ('frequent', _('Frequent')),
]

OUI_NON_CHOICES = [
    ('yes', _('Yes')),
    ('no', _('No')),
]

PATHOLOGIE_CHOICES = [
    ('none', _('None / General follow-up')),
    ('cardiopathy', _('Cardiovascular disease')),
    ('diabetes', _('Diabetes')),
    ('hypertension', _('Hypertension')),
    ('kidney', _('Kidney disease')),
    ('pregnancy', _('Pregnancy / Breastfeeding')),
    ('digestive', _('Digestive issues')),
    ('weight_loss', _('Weight loss')),
    ('weight_gain', _('Weight gain')),
    ('other', _('Other metabolic disease')),
]


# =========================================================
#  PROFIL PATIENT  (= bilan initial, rempli une seule fois)
# =========================================================
class PatientProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')

    # ---- 1. Informations personnelles ----
    birth_date = models.DateField(null=True, blank=True, verbose_name=_("Date of birth"))
    age = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Age"))
    gender = models.CharField(
        max_length=10, blank=True,
        choices=[('Male', _('Male')), ('Female', _('Female'))],
        verbose_name=_("Gender")
    )
    address = models.CharField(max_length=255, blank=True, verbose_name=_("Address"))
    phone = models.CharField(max_length=30, blank=True, verbose_name=_("Phone"))
    occupation = models.CharField(max_length=100, blank=True, verbose_name=_("Occupation"))

    # ---- 2. Motif de consultation ----
    pathology = models.CharField(
        max_length=20, choices=PATHOLOGIE_CHOICES, default='none',
        verbose_name=_("Main pathology")
    )
    consultation_reason = models.TextField(blank=True, verbose_name=_("Reason for consultation"))
    reason_comment = models.TextField(blank=True, verbose_name=_("Comment"))

    # ---- 3. Antecedents medicaux ----
    diagnosis = models.CharField(max_length=255, blank=True, verbose_name=_("Diagnosis"))
    diagnosis_date = models.DateField(null=True, blank=True, verbose_name=_("Diagnosis date"))
    known_diseases = models.TextField(blank=True, verbose_name=_("Known diseases"))
    medical_history = models.TextField(blank=True, verbose_name=_("Medical history"))
    family_history = models.TextField(blank=True, verbose_name=_("Family history (diabetes, hypertension, obesity...)"))
    previous_surgeries = models.TextField(blank=True, verbose_name=_("Previous surgeries"))
    medications = models.TextField(blank=True, verbose_name=_("Current treatments (medications, supplements)"))
    allergies = models.BooleanField(default=False, verbose_name=_("Allergies"))
    food_allergies = models.TextField(blank=True, verbose_name=_("Food allergies"))
    food_intolerances = models.TextField(blank=True, verbose_name=_("Food intolerances"))
    family_history_cvd = models.BooleanField(default=False, verbose_name=_("Family history of CVD"))

    # ---- 4. Habitudes de vie ----
    sleep_hours = models.FloatField(null=True, blank=True, verbose_name=_("Sleep (hours per night)"))
    sleep_quality = models.CharField(
        max_length=10, blank=True,
        choices=[('good', _('Good')), ('fair', _('Fair')), ('poor', _('Poor'))],
        verbose_name=_("Sleep quality")
    )
    activity_level = models.CharField(
        max_length=20, blank=True,
        choices=[
            ('sedentary', _('Sedentary')),
            ('low', _('Low activity')),
            ('moderate', _('Moderate activity')),
            ('intense', _('Intense activity')),
        ],
        verbose_name=_("Activity level")
    )
    activity_type = models.CharField(max_length=150, blank=True, verbose_name=_("Physical activity type"))
    activity_frequency = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Times per week"))
    activity_duration = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Minutes per session"))
    stress_level = models.CharField(max_length=10, blank=True, choices=NIVEAU_CHOICES, verbose_name=_("Stress level"))
    stress_sources = models.TextField(blank=True, verbose_name=_("Main stress sources"))
    smoking = models.BooleanField(default=False, verbose_name=_("Smoking"))
    smoking_frequency = models.CharField(max_length=100, blank=True, verbose_name=_("Smoking frequency"))
    alcohol = models.BooleanField(default=False, verbose_name=_("Alcohol"))
    alcohol_frequency = models.CharField(max_length=100, blank=True, verbose_name=_("Alcohol frequency"))
    sweets = models.BooleanField(default=False, verbose_name=_("Sweets"))
    sweets_frequency = models.CharField(max_length=100, blank=True, verbose_name=_("Sweets frequency"))

    # ---- 5. Donnees anthropometriques ----
    height = models.FloatField(null=True, blank=True, verbose_name=_("Height (cm)"))
    weight = models.FloatField(null=True, blank=True, verbose_name=_("Current weight (kg)"))
    usual_weight = models.FloatField(null=True, blank=True, verbose_name=_("Usual weight (kg)"))
    desired_weight = models.FloatField(null=True, blank=True, verbose_name=_("Desired weight (kg)"))
    waist_circumference = models.FloatField(null=True, blank=True, verbose_name=_("Waist circumference (cm)"))
    hip_circumference = models.FloatField(null=True, blank=True, verbose_name=_("Hip circumference (cm)"))
    bmi = models.FloatField(null=True, blank=True, verbose_name=_("BMI"))
    body_fat_percent = models.FloatField(null=True, blank=True, verbose_name=_("Body fat (%)"))
    blood_pressure_left = models.CharField(max_length=20, blank=True, verbose_name=_("Left blood pressure"))
    blood_pressure_right = models.CharField(max_length=20, blank=True, verbose_name=_("Right blood pressure"))
    other_measures = models.TextField(blank=True, verbose_name=_("Other measures"))

    # ---- 6. Habitudes alimentaires ----
    meals_per_day = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=_("Number of meals per day"))
    has_snacks = models.BooleanField(default=False, verbose_name=_("Snacks included"))
    breakfast_time = models.CharField(max_length=20, blank=True, verbose_name=_("Breakfast time"))
    lunch_time = models.CharField(max_length=20, blank=True, verbose_name=_("Lunch time"))
    dinner_time = models.CharField(max_length=20, blank=True, verbose_name=_("Dinner time"))
    snack_times = models.CharField(max_length=100, blank=True, verbose_name=_("Snack times"))
    meal_place = models.CharField(
        max_length=20, blank=True,
        # pgettext : "Home" seul est traduit "Accueil" (lien du menu) ; ici il faut "A la maison"
        choices=[
            ('home', pgettext_lazy("meal place", "Home")),
            ('work', _('Work')),
            ('outside', _('Eating out')),
        ],
        verbose_name=_("Usual place for meals")
    )
    eat_with = models.CharField(
        max_length=20, blank=True,
        choices=[('alone', _('Alone')), ('family', _('Family')), ('colleagues', _('Colleagues')), ('others', _('Others'))],
        verbose_name=_("People you eat with")
    )

    # Journal alimentaire type
    typical_breakfast = models.TextField(blank=True, verbose_name=_("Typical breakfast"))
    typical_morning_snack = models.TextField(blank=True, verbose_name=_("Typical morning snack"))
    typical_lunch = models.TextField(blank=True, verbose_name=_("Typical lunch"))
    typical_afternoon_snack = models.TextField(blank=True, verbose_name=_("Typical afternoon snack"))
    typical_dinner = models.TextField(blank=True, verbose_name=_("Typical dinner"))
    typical_evening_snack = models.TextField(blank=True, verbose_name=_("Typical evening snack"))

    # Consommation hebdomadaire
    fruits_consumption = models.CharField(max_length=10, blank=True, choices=NIVEAU_CHOICES, verbose_name=_("Fruits consumption"))
    vegetables_consumption = models.CharField(max_length=10, blank=True, choices=NIVEAU_CHOICES, verbose_name=_("Vegetables consumption"))
    fatty_sugary_consumption = models.CharField(max_length=10, blank=True, choices=NIVEAU_CHOICES, verbose_name=_("Fatty/sugary foods consumption"))

    # ---- 7. Hydratation ----
    water_glasses = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=_("Glasses of water per day"))
    water_liters = models.FloatField(null=True, blank=True, verbose_name=_("Litres of water per day"))
    other_drinks = models.TextField(blank=True, verbose_name=_("Other drinks (sodas, juice, alcohol, energy drinks)"))

    # ---- 8. Relation a l'alimentation ----
    appetite = models.CharField(
        max_length=10, blank=True,
        choices=[('low', _('Low')), ('normal', _('Normal')), ('high', _('High'))],
        verbose_name=_("Appetite")
    )
    snacking = models.CharField(max_length=10, blank=True, choices=FREQ_CHOICES, verbose_name=_("Snacking"))
    snacking_moments = models.TextField(blank=True, verbose_name=_("Snacking moments (evening, stress, boredom...)"))
    dietary_restrictions = models.TextField(blank=True, verbose_name=_("Specific restrictions (cultural, religious, ethical)"))
    eating_behaviors = models.TextField(blank=True, verbose_name=_("Particular behaviors (binges, guilt, compulsions...)"))

    # ---- 9. Objectifs et attentes ----
    main_expectations = models.TextField(blank=True, verbose_name=_("Main expectations"))
    goal_timeframe = models.CharField(max_length=150, blank=True, verbose_name=_("Timeframe to reach goals"))
    motivation_level = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=_("Motivation level (0-10)"))

    # ---- 10. Observations du praticien ----
    practitioner_notes = models.TextField(blank=True, verbose_name=_("Practitioner's notes"))
    nutritional_diagnosis = models.TextField(blank=True, verbose_name=_("Nutritional diagnosis"))
    risk_factors = models.TextField(blank=True, verbose_name=_("Risk factors"))
    proposed_dietary_plan = models.TextField(blank=True, verbose_name=_("Proposed dietary plan"))
    specific_advice = models.TextField(blank=True, verbose_name=_("Specific advice"))
    next_appointment = models.DateField(null=True, blank=True, verbose_name=_("Date of next appointment"))

    # ---- Metadonnees ----
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        verbose_name = _("Patient profile")
        verbose_name_plural = _("Patient profiles")

    def save(self, *args, **kwargs):
        if self.weight and self.height:
            h = self.height / 100 if self.height > 3 else self.height
            if h > 0:
                self.bmi = round(self.weight / (h * h), 2)
        super().save(*args, **kwargs)

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

    @property
    def waist_hip_ratio(self):
        """Rapport tour de taille / tour de hanches (indicateur de risque cardio)."""
        if self.waist_circumference and self.hip_circumference and self.hip_circumference > 0:
            return round(self.waist_circumference / self.hip_circumference, 2)
        return None

    @property
    def is_complete(self):
        """Le bilan est considere rempli si les bases y sont."""
        return bool(self.age and self.gender and self.height and self.weight)

    def __str__(self):
        return _("Profile of %(email)s") % {"email": self.user.email}


# =========================================================
#  CONSULTATION  (= fiche de suivi, a chaque rendez-vous)
# =========================================================
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

    # ---- Mesures cliniques ----
    weight = models.FloatField(null=True, blank=True, verbose_name=_("Weight (kg)"))
    blood_pressure = models.CharField(max_length=20, blank=True, verbose_name=_("Blood pressure"))
    blood_pressure_right = models.CharField(max_length=20, blank=True, verbose_name=_("Right blood pressure"))
    heart_rate = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=_("Heart rate (bpm)"))

    # ---- Bilan biologique ----
    total_cholesterol = models.FloatField(null=True, blank=True, verbose_name=_("Total cholesterol"))
    ldl = models.FloatField(null=True, blank=True, verbose_name=_("LDL"))
    hdl = models.FloatField(null=True, blank=True, verbose_name=_("HDL"))
    triglycerides = models.FloatField(null=True, blank=True, verbose_name=_("Triglycerides"))
    hba1c = models.FloatField(null=True, blank=True, verbose_name=_("HbA1c (%)"))

    # ---- Suivi general ----
    appetite = models.CharField(
        max_length=10, blank=True,
        choices=[('low', _('Low')), ('normal', _('Normal')), ('high', _('High'))],
        verbose_name=_("Appetite")
    )
    observations = models.TextField(blank=True, verbose_name=_("Observations"))

    # ---- Parametres specifiques CARDIOPATHIE ----
    edema = models.BooleanField(default=False, verbose_name=_("Edema"))
    wound_healing = models.CharField(
        max_length=10, blank=True,
        choices=[('good', _('Good')), ('fair', _('Fair')), ('poor', _('Poor'))],
        verbose_name=_("Wound healing")
    )
    salt_intake = models.CharField(max_length=10, blank=True, choices=NIVEAU_CHOICES, verbose_name=_("Salt intake"))
    protein_intake = models.CharField(max_length=10, blank=True, choices=NIVEAU_CHOICES, verbose_name=_("Protein intake"))
    hydration_level = models.CharField(max_length=10, blank=True, choices=NIVEAU_CHOICES, verbose_name=_("Hydration"))
    fruits_veg_intake = models.CharField(max_length=10, blank=True, choices=NIVEAU_CHOICES, verbose_name=_("Fruits/Vegetables"))

    # ---- Signes d'alerte ----
    alert_rapid_weight_loss = models.BooleanField(default=False, verbose_name=_("Rapid weight loss"))
    alert_fatigue = models.BooleanField(default=False, verbose_name=_("Significant fatigue"))
    alert_wound = models.BooleanField(default=False, verbose_name=_("Non-healing wound"))
    alert_appetite_loss = models.BooleanField(default=False, verbose_name=_("Decreased appetite"))
    alert_edema = models.BooleanField(default=False, verbose_name=_("Edema present"))

    # ---- Analyse et prescription ----
    nutritional_diagnosis = models.TextField(blank=True, verbose_name=_("Nutritional Diagnosis (PES)"))
    goals = models.TextField(blank=True, verbose_name=_("Nutritional goals"))
    intervention_plan = models.TextField(blank=True, verbose_name=_("Intervention plan"))
    next_appointment = models.DateField(null=True, blank=True, verbose_name=_("Follow-up date"))

    class Meta:
        ordering = ['-date_consultation']
        verbose_name = _("Consultation")
        verbose_name_plural = _("Consultations")

    @property
    def bmi(self):
        if self.weight and self.patient_profile and self.patient_profile.height:
            h = self.patient_profile.height / 100 if self.patient_profile.height > 3 else self.patient_profile.height
            if h > 0:
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

    @property
    def has_alerts(self):
        """Au moins un signe d'alerte est coche."""
        return any([
            self.alert_rapid_weight_loss, self.alert_fatigue, self.alert_wound,
            self.alert_appetite_loss, self.alert_edema
        ])

    def __str__(self):
        return _("Consultation of %(email)s - %(date)s") % {"email": self.patient.email, "date": self.date_consultation}


# =========================================================
#  PLAN ALIMENTAIRE (inchange)
# =========================================================
class MealPlan(models.Model):
    DAYS = [
        ('1', _('Day 1')), ('2', _('Day 2')), ('3', _('Day 3')),
        ('4', _('Day 4')), ('5', _('Day 5')), ('6', _('Day 6')), ('7', _('Day 7'))
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meal_plans')
    day = models.CharField(max_length=1, choices=DAYS)

    breakfast = models.TextField(blank=True, verbose_name=_("Breakfast"))
    morning_snack = models.TextField(blank=True, verbose_name=_("Morning snack"))
    lunch = models.TextField(blank=True, verbose_name=_("Lunch"))
    afternoon_snack = models.TextField(blank=True, verbose_name=_("Afternoon snack"))
    dinner = models.TextField(blank=True, verbose_name=_("Dinner"))
    evening_snack = models.TextField(blank=True, verbose_name=_("Evening snack"))

    class Meta:
        unique_together = ['patient', 'day']
        ordering = ['day']

    def __str__(self):
        return _("Plan %(day)s - %(email)s") % {"day": self.get_day_display(), "email": self.patient.email}


# =========================================================
#  JOURNAL ALIMENTAIRE (inchange)
# =========================================================
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

# =========================================================
#  BOITE DE RECEPTION DE LA NUTRITIONNISTE
#  (messages du formulaire de contact + bilans remplis par les patients)
# =========================================================
class InboxMessage(models.Model):
    KIND_CONTACT = 'contact'
    KIND_BILAN = 'bilan'
    KIND_CHOICES = [
        (KIND_CONTACT, _("Contact form message")),
        (KIND_BILAN, _("Assessment filled in by a patient")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_CONTACT, verbose_name=_("Type"))
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
        related_name='inbox_messages', verbose_name=_("Patient")
    )
    name = models.CharField(max_length=150, blank=True, verbose_name=_("Name"))
    email = models.EmailField(blank=True, verbose_name=_("Email"))
    phone = models.CharField(max_length=30, blank=True, verbose_name=_("Phone"))
    message = models.TextField(blank=True, verbose_name=_("Message"))
    is_read = models.BooleanField(default=False, verbose_name=_("Read"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Received on"))

    class Meta:
        ordering = ['is_read', '-created_at']
        verbose_name = _("Inbox message")
        verbose_name_plural = _("Inbox messages")

    def __str__(self):
        return "%s - %s" % (self.get_kind_display(), self.name or self.email)

    @classmethod
    def notify_bilan(cls, patient):
        """Previent la nutritionniste qu'un patient a enregistre son bilan.
        Un seul avis non lu par patient : on le remonte au lieu d'en empiler."""
        from django.utils import timezone
        existing = cls.objects.filter(kind=cls.KIND_BILAN, patient=patient, is_read=False).first()
        if existing:
            cls.objects.filter(pk=existing.pk).update(created_at=timezone.now())
            return existing, False
        return cls.objects.create(
            kind=cls.KIND_BILAN, patient=patient,
            name=patient.get_full_name(), email=patient.email,
        ), True


class InboxReply(models.Model):
    """Reponse de la nutritionniste a un message, envoyee par e-mail depuis l'application."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(InboxMessage, on_delete=models.CASCADE, related_name='replies', verbose_name=_("Message"))
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name=_("Author"))
    subject = models.CharField(max_length=255, verbose_name=_("Subject"))
    body = models.TextField(verbose_name=_("Reply"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Sent on"))

    class Meta:
        ordering = ['created_at']
        verbose_name = _("Reply")
        verbose_name_plural = _("Replies")

    def __str__(self):
        return self.subject


# =========================================================
#  FILE D'ATTENTE DES E-MAILS
#  Le site enregistre l'e-mail ici et repond tout de suite ;
#  la commande "process_email_queue" (tache permanente) les envoie en arriere-plan.
# =========================================================
class QueuedEmail(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_SENT, _("Sent")),
        (STATUS_FAILED, _("Failed")),
    ]
    MAX_ATTEMPTS = 5

    # Categorie (en-tete X-Nutri-Category). Les e-mails "account" (codes de connexion,
    # mot de passe oublie...) ne gardent PAS leur contenu une fois envoyes : un code
    # lisible dans la base serait une faille. Les autres gardent tout pour l'historique.
    CATEGORY_ACCOUNT = 'account'
    CATEGORY_CHOICES = [
        ('account', _("Account (codes, password)")),
        ('notification', _("Notification to dietitians")),
        ('reply', _("Reply to a message")),
        ('patient', _("Email to a patient")),
        ('other', _("Other")),
    ]
    HEADER_CATEGORY = 'X-Nutri-Category'

    subject = models.CharField(max_length=255, verbose_name=_("Subject"))
    body = models.TextField(blank=True, verbose_name=_("Content"))
    html_body = models.TextField(blank=True, verbose_name=_("HTML content"))
    from_email = models.CharField(max_length=254, blank=True, verbose_name=_("Sender"))
    to = models.JSONField(default=list, verbose_name=_("Recipients"))
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_ACCOUNT,
                                db_index=True, verbose_name=_("Category"))
    body_erased = models.BooleanField(default=False, verbose_name=_("Content erased after sending"))
    cc = models.JSONField(default=list, blank=True)
    bcc = models.JSONField(default=list, blank=True)
    reply_to = models.JSONField(default=list, blank=True)
    headers = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True,
                              verbose_name=_("Status"))
    attempts = models.PositiveSmallIntegerField(default=0, verbose_name=_("Attempts"))
    last_error = models.TextField(blank=True, verbose_name=_("Last error"))
    next_attempt_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Next attempt"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created on"))
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Sent on"))

    class Meta:
        ordering = ['created_at']
        verbose_name = _("Queued email")
        verbose_name_plural = _("Queued emails")

    def __str__(self):
        return "%s -> %s (%s)" % (self.subject, ", ".join(self.to), self.get_status_display())

    def mark_sent(self):
        """Marque l'e-mail comme envoye ; efface le contenu des e-mails de compte (codes)."""
        from django.utils import timezone
        self.status = self.STATUS_SENT
        self.sent_at = timezone.now()
        self.last_error = ""
        if self.category == self.CATEGORY_ACCOUNT:
            self.body = ""
            self.html_body = ""
            self.body_erased = True
