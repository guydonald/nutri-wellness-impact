from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import PatientProfileForm, ConsultationForm, FoodDiaryForm
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
import openpyxl, json
from .models import PatientProfile, FoodDiary, Consultation, MealPlan
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from .forms import UserUpdateForm, PatientProfileUpdateForm
from .models import PatientProfile
from django.views.generic import ListView
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db import transaction # Pour s'assurer que les deux sauvegardes sont atomiques
from users.models import CustomUser
from django.db.models import Count, Avg
from django.forms import modelformset_factory


User = get_user_model()


class IsDietitianMixin(UserPassesTestMixin):
    def test_func(self):
        # Vérifie si l'utilisateur est une Diététicienne
        return self.request.user.is_authenticated and self.request.user.role == "dietitian"

# Mixin personnalisé pour vérifier le rôle de l'utilisateur
class IsPatientMixin(UserPassesTestMixin):
    def test_func(self):
        # Vérifie si l'utilisateur est un Patient
        return self.request.user.is_authenticated and self.request.user.role == "patient"

# Fonction de test pour le décorateur user_passes_test (utilisé pour les FBV)
def is_patient_check(user):
    return user.is_authenticated and user.role == "patient"

def is_dietitian_check(user):
    """Vérifie si l'utilisateur est authentifié et a le rôle 'dietitian'."""
    return user.is_authenticated and user.role == "dietitian"


class DietitianPatientListView(LoginRequiredMixin, IsDietitianMixin, ListView):
    # Nous listons les objets User (car nous avons besoin du nom, de l'email, etc.)
    model = User 
    template_name = 'dietitians/patient_list.html'
    context_object_name = 'patients'
    paginate_by = 10 # Optionnel: pour la pagination

    def get_queryset(self):
        queryset = User.objects.filter(role='patient').order_by('last_name').select_related('profile').order_by('-date_joined')
        
        # Optionnel : Ajoutez ici la recherche si l'utilisateur entre un terme
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Nombre total de patients (sans pagination)
        context['total_patients'] = User.objects.filter(role='patient').count()
        # Optionnel : nombre actifs / inactifs
        context['active_patients'] = User.objects.filter(role='patient', is_active=True).count()
        context['inactive_patients'] = User.objects.filter(role='patient', is_active=False).count()
        return context


@login_required
def home_redirect_view(request):
    user = request.user

    if user.role == 'dietitian':
        return redirect('dietitian_statistics')

    elif user.role == 'patient':
        # On vérifie si le profil existe
        profile_exists = hasattr(user, 'profile')
        if profile_exists and user.profile.age:
            return redirect('my_medical_record')
        else:
            return redirect('complete_profile')

    print("DEBUG: Aucun rôle détecté, déconnexion")
    return redirect('account_logout')


@login_required
@user_passes_test(is_dietitian_check, login_url='/') # Utilisez le check que nous avons défini
def dietitian_patient_profile_modal(request, user_id):
    # 1. Récupérer l'utilisateur Patient
    patient = get_object_or_404(User, id=user_id, role='patient')
    
    # 2. Récupérer son profil PatientProfile associé (s'il existe)
    try:
        profile = patient.profile # Utilise related_name='profile' défini dans PatientProfile
    except:
        profile = None # Le profil n'existe pas encore

    context = {
        'patient': patient,
        'profile': profile,
    }
    
    # Rendre un template très léger (fragment HTML)
    return render(request, 'dietitians/partials/patient_profile_detail.html', context)

@login_required
def complete_profile(request):
    if request.user.role != 'patient':
        return redirect('home')

    # Le signal a normalement déjà créé le profil, on le récupère simplement
    profile, created = PatientProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = PatientProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            if request.user.role == 'dietitian':
                return redirect('dietitian_dashboard') # ou la liste des patients
            else:
                # Pour le patient, on peut l'envoyer vers son dashboard ou son record
                return redirect('patient_record', patient_id=profile.id)
    else:
        form = PatientProfileForm(instance=profile)

    return render(request, 'patients/patient_profile_form.html', {'form': form})


class PatientProfileView(LoginRequiredMixin, IsPatientMixin, DetailView):
    # Le modèle principal de cette vue est PatientProfile
    model = PatientProfile
    # Le template à utiliser pour l'affichage
    template_name = 'patients/patient_profile.html'
    # Le nom de la variable d'objet dans le template
    context_object_name = 'profile'

    def get_object(self, queryset=None):
        """
        Récupère le profil Patient associé à l'utilisateur connecté.
        Si l'objet n'existe pas, cela lèvera une erreur 404.
        """
        return get_object_or_404(PatientProfile, user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ajouter l'objet User au contexte pour l'affichage des infos de base
        context['user'] = self.request.user
        return context
    


@login_required
@user_passes_test(is_patient_check)
def patient_profile_update_view(request):
    # Récupérer les instances à modifier
    user_instance = request.user
    
    # Récupérer ou créer l'instance PatientProfile
    # Note: On utilise get_or_create au cas où l'utilisateur n'aurait pas encore de profil
    profile_instance, created = PatientProfile.objects.get_or_create(user=user_instance)

    if request.method == 'POST':
        # Instancier les formulaires avec les données POST et les instances existantes
        user_form = UserUpdateForm(request.POST, instance=user_instance)
        profile_form = PatientProfileUpdateForm(request.POST, instance=profile_instance)
        
        if user_form.is_valid() and profile_form.is_valid():
            try:
                with transaction.atomic():
                    user_form.save()
                    profile_form.save()
                
                messages.success(request, 'Votre profil a été mis à jour avec succès !')
                return redirect('patient_profile') # Rediriger vers la page d'affichage
                
            except Exception as e:
                messages.error(request, f"Une erreur s'est produite lors de la sauvegarde : {e}")
                
        else:
            messages.error(request, 'Veuillez corriger les erreurs dans les formulaires.')
    
    else:
        # Créer les formulaires pour la requête GET avec les données actuelles
        user_form = UserUpdateForm(instance=user_instance)
        profile_form = PatientProfileUpdateForm(instance=profile_instance)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile_instance, # Pour afficher des informations non modifiables si nécessaire
    }
    return render(request, 'patients/patient_profile_update.html', context)


# Export sur fichier excel
@login_required
def export_patients_excel(request):
    # 1. Création du fichier Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Liste des Patients"

    # 2. En-têtes basés sur tes modèles
    headers = [
        'Fist name', 'Last Name', 'Email', 'Nom d\'utilisateur', 'Rôle', 
        'Âge', 'Genre', 'Profession', 'Niveau d\'activité', 
        'Diagnostic', 'Taille (cm)', 'Poids (kg)', 'IMC (BMI)'
    ]
    ws.append(headers)

    # 3. Récupération des données avec filtrage (identique à ta liste)
    search_query = request.GET.get('q')
    patients = User.objects.filter(role='patient').order_by('last_name')
    
    if search_query:
        patients = patients.filter(
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query) | 
            Q(email__icontains=search_query)
        )

    # 4. Remplissage des lignes
    for patient in patients:
        # On utilise le related_name='profile' que tu as défini dans ton modèle
        profile = getattr(patient, 'profile', None) 
        
        row = [
            patient.first_name,
            patient.last_name,
            patient.email,
            patient.username,
            patient.role,
            profile.age if profile else "N/A",
            profile.get_gender_display() if profile else "N/A", # Pour avoir 'Male' au lieu de 'M'
            profile.occupation if profile else "N/A",
            profile.get_activity_level_display() if profile else "N/A",
            profile.diagnosis if profile else "N/A",
            profile.height if profile else "N/A",
            profile.weight if profile else "N/A",
            profile.bmi if profile else "N/A",
        ]
        ws.append(row)

    # 5. Configuration de la réponse HTTP pour le téléchargement
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=export_patients_complet.xlsx'
    wb.save(response)
    
    return response


@login_required
@user_passes_test(is_dietitian_check, login_url='/')
def dietitian_stats_view(request):
    # 1. Étude du Sexe
    gender_stats = PatientProfile.objects.values('gender').annotate(total=Count('gender'))
    
    # 2. Étude des Allergies (Boolean)
    allergy_stats = PatientProfile.objects.values('allergies').annotate(total=Count('allergies'))
    
    # 3. Étude du Niveau d'Activité
    activity_stats = PatientProfile.objects.values('activity_level').annotate(total=Count('activity_level'))
    
    # 4. Top 5 des Professions (Occupation)
    occupation_stats = PatientProfile.objects.values('occupation').annotate(total=Count('occupation')).order_by('-total')[:5]

    # 5. Moyennes générales (Poids, Taille, Âge)
    averages = PatientProfile.objects.aggregate(
        avg_age=Avg('age'),
        avg_weight=Avg('weight'),
        avg_height=Avg('height'),
        avg_bmi=Avg('bmi')
    )

    context = {
        # CORRECTION : On force la conversion en string pour le JSON
        'gender_labels': json.dumps([str(item['gender']) for item in gender_stats]),
        'gender_data': json.dumps([item['total'] for item in gender_stats]),
        
        # CORRECTION : Ici aussi
        'allergy_labels': json.dumps([str(_("Avec Allergies")), str(_("Sans Allergies"))]),
        'allergy_data': json.dumps([
            next((item['total'] for item in allergy_stats if item['allergies']), 0),
            next((item['total'] for item in allergy_stats if not item['allergies']), 0)
        ]),

        # CORRECTION : On s'assure que le choix de niveau d'activité est bien casté en string
        'activity_labels': json.dumps([
            str(dict(PatientProfile.activity_level.field.choices).get(item['activity_level'], item['activity_level'])) 
            for item in activity_stats
        ]),
        'activity_data': json.dumps([item['total'] for item in activity_stats]),

        'occ_labels': json.dumps([str(item['occupation']) for item in occupation_stats if item['occupation']]),
        'occ_data': json.dumps([item['total'] for item in occupation_stats if item['occupation']]),

        'averages': averages,
    }
    return render(request, 'dietitians/statistics.html', context)


@login_required
@user_passes_test(is_dietitian_check)
def create_consultation(request, patient_id):
    patient = get_object_or_404(User, id=patient_id, role='patient')
    
    if request.method == 'POST':
        form = ConsultationForm(request.POST)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.patient = patient
            consultation.dietitian = request.user
            consultation.save()

            # Si c'est du HTMX, on peut dire à la page de se rafraîchir
            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'consultationSaved'})
            return redirect('dietitian_dashboard') 
        
    else:
        form = ConsultationForm()
    
    return render(request, 'dietitians/consultation_form.html', {'form': form, 'patient': patient})


@login_required
def add_food_entry(request):
    if request.method == 'POST':
        form = FoodDiaryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.patient = request.user
            entry.save()
            return redirect('my_medical_record') # Redirige vers son espace
    else:
        form = FoodDiaryForm()
    return render(request, 'patients/add_food.html', {'form': form})


@login_required
def edit_food_entry(request, entry_id):
    entry = get_object_or_404(FoodDiary, id=entry_id, patient=request.user)
    if request.method == 'POST':
        form = FoodDiaryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            # On peut ajouter un petit message flash ici
    return redirect('my_medical_record')


@login_required
def delete_food_entry(request, entry_id):
    entry = get_object_or_404(FoodDiary, id=entry_id, patient=request.user)
    entry.delete()
    messages.warning(request, "Le repas a été supprimé.")
    return redirect('my_medical_record')


@login_required
@user_passes_test(is_dietitian_check)
def patient_medical_record(request, patient_id):
    patient = get_object_or_404(User, id=patient_id, role='patient')
    
    # 1. Données pour le GRAPHIQUE (non paginées)
    chart_history = patient.consultations.all().order_by('date_consultation')
    meal_plans = MealPlan.objects.filter(patient=patient).order_by('day')
    
    # 2. Pagination des CONSULTATIONS
    all_history = patient.consultations.all().order_by('-date_consultation')
    paginator_h = Paginator(all_history, 10) # 5 par page
    page_h = request.GET.get('page_h')
    history_paginated = paginator_h.get_page(page_h)
    
    # 3. Pagination du JOURNAL ALIMENTAIRE
    all_food = patient.food_entries.all().order_by('-date')
    paginator_f = Paginator(all_food, 10) # 10 par page
    page_f = request.GET.get('page_f')
    food_paginated = paginator_f.get_page(page_f)
    
    return render(request, 'dietitians/patient_record.html', {
        'patient': patient,
        'meal_plans': meal_plans,
        'chart_history': chart_history, # Pour le canvas JS
        'history': history_paginated,   # Pour les cartes HTML
        'food_log': food_paginated      # Pour le tableau HTML
    })


@login_required
def edit_consultation(request, consult_id):
    consult = get_object_or_404(Consultation, id=consult_id)
    if request.method == 'POST':
        # On met à jour manuellement ou via un Form
        consult.weight = request.POST.get('weight')
        consult.blood_pressure = request.POST.get('blood_pressure')
        consult.hba1c = request.POST.get('hba1c')
        consult.total_cholesterol = request.POST.get('total_cholesterol')
        consult.nutritional_diagnosis = request.POST.get('nutritional_diagnosis')
        consult.intervention_plan = request.POST.get('intervention_plan')
        consult.save()
        messages.success(request, "Consultation mise à jour.")
    return redirect('patient_record', patient_id=consult.patient.id)

@login_required
def delete_consultation(request, consult_id):
    consult = get_object_or_404(Consultation, id=consult_id)
    patient_id = consult.patient.id # On stocke l'ID avant de supprimer
    consult.delete()
    messages.warning(request, "La consultation a été définitivement supprimée.")
    return redirect('patient_record', patient_id=patient_id)


@login_required
def my_medical_record(request):
    patient = request.user
    if patient.role != 'patient':
        messages.error(request, "Accès réservé aux patients.")
        return redirect('home')
    
    # 1. Données pour le GRAPHIQUE (non paginées)
    chart_history = patient.consultations.all().order_by('date_consultation')
    meal_plans = MealPlan.objects.filter(patient=patient).order_by('day')
    
    # 2. Pagination des CONSULTATIONS
    all_history = patient.consultations.all().order_by('-date_consultation')
    paginator_h = Paginator(all_history, 10) # 10 par page
    page_h = request.GET.get('page_h')
    history_paginated = paginator_h.get_page(page_h)
    
    # 3. Pagination du JOURNAL ALIMENTAIRE
    all_food = patient.food_entries.all().order_by('-date')
    paginator_f = Paginator(all_food, 10) # 10 par page
    page_f = request.GET.get('page_f')
    food_paginated = paginator_f.get_page(page_f)
    
    return render(request, 'patients/my_record.html', {
        'patient': patient,
        'meal_plans': meal_plans,
        'chart_history': chart_history, # Pour le canvas JS
        'history': history_paginated,   # Pour les cartes HTML
        'food_log': food_paginated,     # Pour le tableau HTML
        'food_form': FoodDiaryForm()
    })


@login_required
@user_passes_test(lambda u: u.role == 'dietitian') # Vérification simple du rôle
def manage_meal_plan(request, patient_id):
    patient = get_object_or_404(User, id=patient_id, role='patient')
    
    # Définition du FormSet
    MealPlanFormSet = modelformset_factory(
        MealPlan, 
        fields=('day', 'breakfast', 'morning_snack', 'lunch', 'afternoon_snack', 'dinner', 'evening_snack'),
        extra=0, # On met 0 car on va pré-générer ou filtrer les existants
        max_num=7
    )

    # On récupère ce qui existe déjà pour ce patient
    queryset = MealPlan.objects.filter(patient=patient).order_by('day')

    if request.method == 'POST':
        # On passe le queryset ici pour que Django sache quels IDs mettre à jour
        formset = MealPlanFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.patient = patient
                instance.save()
            messages.success(request, _("Plan alimentaire mis à jour avec succès !"))
            return redirect('patient_record', patient_id=patient.id)
    else:
        # S'il n'y a rien en base, on peut soit laisser vide, 
        # soit forcer l'affichage de 7 formulaires vierges
        if not queryset.exists():
            formset = MealPlanFormSet(queryset=MealPlan.objects.none())
            # On force 7 formulaires vides si c'est la première fois
            formset.extra = 7 
        else:
            formset = MealPlanFormSet(queryset=queryset)

    return render(request, 'dietitians/manage_meal_plan.html', {
        'formset': formset,
        'patient': patient
    })