from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from .models import PatientProfile, Consultation, FoodDiary, MealPlan

User = get_user_model()


# =========================================================
#  BILAN INITIAL - decoupe en sections
# =========================================================
class BilanSection1Form(forms.ModelForm):
    """1. Informations personnelles + motif"""
    class Meta:
        model = PatientProfile
        fields = [
            'birth_date', 'age', 'gender', 'address', 'phone', 'occupation',
            'pathology', 'consultation_reason', 'reason_comment',
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'consultation_reason': forms.Textarea(attrs={'rows': 2}),
            'reason_comment': forms.Textarea(attrs={'rows': 2}),
        }


class BilanSection2Form(forms.ModelForm):
    """3. Antecedents medicaux"""
    class Meta:
        model = PatientProfile
        fields = [
            'diagnosis', 'diagnosis_date', 'known_diseases', 'medical_history',
            'family_history', 'previous_surgeries', 'medications',
            'allergies', 'food_allergies', 'food_intolerances', 'family_history_cvd',
        ]
        widgets = {
            'diagnosis_date': forms.DateInput(attrs={'type': 'date'}),
            'known_diseases': forms.Textarea(attrs={'rows': 2}),
            'medical_history': forms.Textarea(attrs={'rows': 2}),
            'family_history': forms.Textarea(attrs={'rows': 2}),
            'previous_surgeries': forms.Textarea(attrs={'rows': 2}),
            'medications': forms.Textarea(attrs={'rows': 2}),
            'food_allergies': forms.Textarea(attrs={'rows': 2}),
            'food_intolerances': forms.Textarea(attrs={'rows': 2}),
        }


class BilanSection3Form(forms.ModelForm):
    """4. Habitudes de vie"""
    class Meta:
        model = PatientProfile
        fields = [
            'sleep_hours', 'sleep_quality',
            'activity_level', 'activity_type', 'activity_frequency', 'activity_duration',
            'stress_level', 'stress_sources',
            'smoking', 'smoking_frequency',
            'alcohol', 'alcohol_frequency',
            'sweets', 'sweets_frequency',
        ]
        widgets = {
            'stress_sources': forms.Textarea(attrs={'rows': 2}),
        }


class BilanSection4Form(forms.ModelForm):
    """5. Donnees anthropometriques"""
    class Meta:
        model = PatientProfile
        fields = [
            'height', 'weight', 'usual_weight', 'desired_weight',
            'waist_circumference', 'hip_circumference', 'body_fat_percent',
            'blood_pressure_left', 'blood_pressure_right', 'other_measures',
        ]
        widgets = {
            'other_measures': forms.Textarea(attrs={'rows': 2}),
        }


class BilanSection5Form(forms.ModelForm):
    """6. Habitudes alimentaires + 7. Hydratation"""
    class Meta:
        model = PatientProfile
        fields = [
            'meals_per_day', 'has_snacks',
            'breakfast_time', 'lunch_time', 'dinner_time', 'snack_times',
            'meal_place', 'eat_with',
            'typical_breakfast', 'typical_morning_snack', 'typical_lunch',
            'typical_afternoon_snack', 'typical_dinner', 'typical_evening_snack',
            'fruits_consumption', 'vegetables_consumption', 'fatty_sugary_consumption',
            'water_glasses', 'water_liters', 'other_drinks',
        ]
        widgets = {
            'typical_breakfast': forms.Textarea(attrs={'rows': 2}),
            'typical_morning_snack': forms.Textarea(attrs={'rows': 2}),
            'typical_lunch': forms.Textarea(attrs={'rows': 2}),
            'typical_afternoon_snack': forms.Textarea(attrs={'rows': 2}),
            'typical_dinner': forms.Textarea(attrs={'rows': 2}),
            'typical_evening_snack': forms.Textarea(attrs={'rows': 2}),
            'other_drinks': forms.Textarea(attrs={'rows': 2}),
            'breakfast_time': forms.TextInput(attrs={'placeholder': '07:00'}),
            'lunch_time': forms.TextInput(attrs={'placeholder': '13:00'}),
            'dinner_time': forms.TextInput(attrs={'placeholder': '19:30'}),
        }


class BilanSection6Form(forms.ModelForm):
    """8. Relation a l'alimentation + 9. Objectifs"""
    class Meta:
        model = PatientProfile
        fields = [
            'appetite', 'snacking', 'snacking_moments',
            'dietary_restrictions', 'eating_behaviors',
            'main_expectations', 'goal_timeframe', 'motivation_level',
        ]
        widgets = {
            'snacking_moments': forms.Textarea(attrs={'rows': 2}),
            'dietary_restrictions': forms.Textarea(attrs={'rows': 2}),
            'eating_behaviors': forms.Textarea(attrs={'rows': 2}),
            'main_expectations': forms.Textarea(attrs={'rows': 3}),
            'motivation_level': forms.NumberInput(attrs={'min': 0, 'max': 10}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Le maximum n'etait verifie que par le navigateur : on le controle aussi cote serveur
        from django.core.validators import MaxValueValidator
        self.fields['motivation_level'].validators.append(MaxValueValidator(10))


class BilanPraticienForm(forms.ModelForm):
    """10-13. Reserve a la nutritionniste"""
    class Meta:
        model = PatientProfile
        fields = [
            'practitioner_notes', 'nutritional_diagnosis', 'risk_factors',
            'proposed_dietary_plan', 'specific_advice', 'next_appointment',
        ]
        widgets = {
            'practitioner_notes': forms.Textarea(attrs={'rows': 4}),
            'nutritional_diagnosis': forms.Textarea(attrs={'rows': 3}),
            'risk_factors': forms.Textarea(attrs={'rows': 2}),
            'proposed_dietary_plan': forms.Textarea(attrs={'rows': 4}),
            'specific_advice': forms.Textarea(attrs={'rows': 3}),
            'next_appointment': forms.DateInput(attrs={'type': 'date'}),
        }


class EssentialProfileForm(forms.ModelForm):
    """Premiere etape du patient : seulement l'essentiel (moins de 2 minutes).
    Le bilan complet se remplit ensuite, a son rythme, depuis son espace."""
    class Meta:
        model = PatientProfile
        fields = ['age', 'gender', 'height', 'weight', 'phone', 'pathology']
        widgets = {
            'age': forms.NumberInput(attrs={'min': 1, 'max': 120, 'placeholder': '35'}),
            'height': forms.NumberInput(attrs={'step': '0.1', 'placeholder': '165'}),
            'weight': forms.NumberInput(attrs={'step': '0.1', 'placeholder': '70'}),
            'phone': forms.TextInput(attrs={'placeholder': '+237 6XX XX XX XX'}),
        }
        labels = {
            'pathology': _("Why are you consulting?"),
        }
        help_texts = {
            'phone': _("Optional - lets your dietitian reach you."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Les 4 informations indispensables pour calculer l'IMC et demarrer le suivi
        for name in ('age', 'gender', 'height', 'weight'):
            self.fields[name].required = True


class PatientProfileForm(forms.ModelForm):
    """Bilan complet en un seul formulaire (pour la nutritionniste)."""
    class Meta:
        model = PatientProfile
        exclude = ['user', 'bmi', 'created_at', 'updated_at']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'diagnosis_date': forms.DateInput(attrs={'type': 'date'}),
            'next_appointment': forms.DateInput(attrs={'type': 'date'}),
            'motivation_level': forms.NumberInput(attrs={'min': 0, 'max': 10}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault('rows', 2)


class PersonalInfoForm(forms.ModelForm):
    """Page "Modifier mon profil" du patient : seulement ses informations personnelles.
    Tout le reste (sante, habitudes, repas...) se modifie dans le bilan, etape par etape.
    SECURITE : la liste est fermee -> un patient ne peut pas toucher aux notes de la nutritionniste."""
    class Meta:
        model = PatientProfile
        fields = ['birth_date', 'age', 'gender', 'phone', 'occupation', 'address']
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'phone': forms.TextInput(attrs={'placeholder': '+237 6XX XX XX XX'}),
        }


# Alias de compatibilite avec l'ancien code
PatientProfileUpdateForm = PersonalInfoForm


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        }


# =========================================================
#  CONSULTATION
# =========================================================
class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = [
            'weight', 'blood_pressure', 'blood_pressure_right', 'heart_rate',
            'total_cholesterol', 'ldl', 'hdl', 'triglycerides', 'hba1c',
            'appetite', 'observations',
            'edema', 'wound_healing', 'salt_intake', 'protein_intake',
            'hydration_level', 'fruits_veg_intake',
            'alert_rapid_weight_loss', 'alert_fatigue', 'alert_wound',
            'alert_appetite_loss', 'alert_edema',
            'nutritional_diagnosis', 'goals', 'intervention_plan', 'next_appointment',
        ]
        widgets = {
            'next_appointment': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'observations': forms.Textarea(attrs={'rows': 3}),
            'nutritional_diagnosis': forms.Textarea(attrs={'rows': 3, 'placeholder': _('Problem, Etiology, Signs/Symptoms (PES)...')}),
            'goals': forms.Textarea(attrs={'rows': 3}),
            'intervention_plan': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


# =========================================================
#  JOURNAL & PLAN (inchanges)
# =========================================================
class FoodDiaryForm(forms.ModelForm):
    class Meta:
        model = FoodDiary
        fields = ['meal_time', 'description', 'beverage']
        widgets = {
            'meal_time': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': _('E.g.: whole bread, boiled egg, skimmed milk...'),
                'class': 'form-control'
            }),
        }


class MealPlanForm(forms.ModelForm):
    class Meta:
        model = MealPlan
        fields = ['day', 'breakfast', 'morning_snack', 'lunch', 'afternoon_snack', 'dinner', 'evening_snack']
        widgets = {
            'breakfast': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'morning_snack': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'lunch': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'afternoon_snack': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'dinner': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'evening_snack': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'day': forms.Select(attrs={'class': 'form-select'}),
        }