from django import forms
from .models import PatientProfile, Consultation, FoodDiary, MealPlan
from django.contrib.auth import get_user_model


class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = PatientProfile
        fields = [
            'age', 'gender', 'occupation', 'activity_level',
            'diagnosis', 'diagnosis_date', 'medical_history',
            'medications', 'allergies', 'family_history_cvd',
            'height', 'weight', 'waist_circumference', 'body_fat_percent',
        ]
        widgets = {
            'diagnosis_date': forms.DateInput(attrs={'type': 'date'}),
            'medical_history': forms.Textarea(attrs={'rows': 3}),
            'medications': forms.Textarea(attrs={'rows': 2}),
        }


User = get_user_model()

# Formulaire pour modifier le modèle User (nom, prénom, email)
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        # Vous pouvez ajouter des widgets si vous voulez des classes CSS spécifiques
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'readonly': 'readonly'}), # Email en lecture seule
        }

# Formulaire pour modifier le modèle PatientProfile
class PatientProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = PatientProfile
        exclude = ['user', 'bmi'] # 'user' et 'bmi' sont exclus car ils sont gérés automatiquement
        
        widgets = {
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'activity_level': forms.Select(attrs={'class': 'form-select'}),
            'diagnosis_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            # Vous pouvez mettre en forme tous les autres champs ici
        }

    # Optionnel: Calcul de l'IMC lors de la sauvegarde du formulaire
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Exemple de calcul simple (vous devrez peut-être affiner ceci)
        if instance.height and instance.weight:
            height_m = instance.height  # Suppose que height est en mètres
            weight_kg = instance.weight
            if height_m > 0:
                instance.bmi = round(weight_kg / (height_m ** 2), 2)
        
        if commit:
            instance.save()
        return instance
    

class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = [
            'blood_pressure', 'total_cholesterol', 'ldl', 'hdl', 
            'triglycerides', 'hba1c', 'weight', 'nutritional_diagnosis', 
            'goals', 'intervention_plan', 'next_appointment'
        ]
        widgets = {
            'date_consultation': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'next_appointment': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'nutritional_diagnosis': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Problème, Étiologie, Signes/Symptômes (PES)...'}),
            'goals': forms.Textarea(attrs={'rows': 3}),
            'intervention_plan': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

    
class FoodDiaryForm(forms.ModelForm):
    class Meta:
        model = FoodDiary
        fields = ['meal_time', 'description', 'beverage']
        widgets = {
            'meal_time': forms.Select(attrs={'class': 'form-select',}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Ex: Pain complet, œuf bouilli, lait écrémé...', 'class':"form-control"}),
        }


# patients/forms.py
class MealPlanForm(forms.ModelForm):
    class Meta:
        model = MealPlan
        fields = ['day', 'breakfast', 'lunch', 'dinner']
        widgets = {
            'breakfast': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'lunch': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'dinner': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'day': forms.Select(attrs={'class': 'form-select'}),
        }