import json

import openpyxl
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Count, F, Q
from django.forms import modelformset_factory
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView
import io
from datetime import datetime, time as dtime, timedelta

from django.utils import timezone
from django.http import FileResponse
from .pdf_export import generer_bilan_pdf, generer_plan_pdf, generer_suivi_pdf

from .forms import (
    BilanPraticienForm,
    BilanSection1Form,
    BilanSection2Form,
    BilanSection3Form,
    BilanSection4Form,
    BilanSection5Form,
    BilanSection6Form,
    ConsultationForm,
    EssentialProfileForm,
    FoodDiaryForm,
    PatientProfileForm,
    PatientProfileUpdateForm,
    UserUpdateForm,
)
from .models import Consultation, FoodDiary, InboxMessage, InboxReply, MealPlan, PatientProfile

User = get_user_model()


# =========================================================
#  CONTROLE D'ACCES
# =========================================================
class IsDietitianMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and getattr(self.request.user, 'role', None) == "dietitian"


class IsPatientMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and getattr(self.request.user, 'role', None) == "patient"


def is_patient_check(user):
    return user.is_authenticated and getattr(user, 'role', None) == "patient"


def is_dietitian_check(user):
    return user.is_authenticated and getattr(user, 'role', None) == "dietitian"


# =========================================================
#  TABLEAU DE BORD DIETETICIEN
# =========================================================
class DietitianPatientListView(LoginRequiredMixin, IsDietitianMixin, ListView):
    model = User
    template_name = 'dietitians/patient_list.html'
    context_object_name = 'patients'
    paginate_by = 10

    def get_queryset(self):
        queryset = User.objects.filter(role='patient').select_related('profile').order_by('-date_joined')
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
                | Q(email__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base = User.objects.filter(role='patient')
        context['total_patients'] = base.count()
        context['active_patients'] = base.filter(is_active=True).count()
        context['inactive_patients'] = base.filter(is_active=False).count()
        return context


@login_required
def home_redirect_view(request):
    role = getattr(request.user, 'role', None)

    if role == 'dietitian':
        return redirect('dietitian_statistics')

    if role == 'patient':
        profile = getattr(request.user, 'profile', None)
        if profile and profile.age:
            return redirect('patient_home')
        return redirect('complete_profile')

    return redirect('account_logout')


@login_required
@user_passes_test(is_dietitian_check, login_url='/')
def dietitian_patient_profile_modal(request, user_id):
    patient = get_object_or_404(User, id=user_id, role='patient')
    profile = getattr(patient, 'profile', None)
    return render(request, 'dietitians/partials/patient_profile_detail.html', {
        'patient': patient,
        'profile': profile,
    })


# =========================================================
#  BILAN INITIAL (formulaire de consultation dietetique)
# =========================================================
SECTION_FORMS = [
    ('form1', BilanSection1Form),
    ('form2', BilanSection2Form),
    ('form3', BilanSection3Form),
    ('form4', BilanSection4Form),
    ('form5', BilanSection5Form),
    ('form6', BilanSection6Form),
]


# Chaque etape du bilan : formulaire, icone et phrase d'explication
BILAN_STEP_META = [
    ('form1', 'bi-person-vcard', _("Who you are and why you are consulting.")),
    ('form2', 'bi-capsule', _("Illnesses, treatments and allergies. Only what you know.")),
    ('form3', 'bi-moon-stars', _("Sleep, physical activity, stress and habits.")),
    ('form4', 'bi-rulers', _("Height, weight and other measurements if you know them. Your dietitian will take the others.")),
    ('form5', 'bi-egg-fried', _("What a usual day of meals looks like for you, and what you drink.")),
    ('form6', 'bi-bullseye', _("Your appetite, your eating habits and what you expect from the follow-up.")),
]


def _bilan_steps(profile, is_dietitian):
    """Liste des etapes (avec avancement) ; la nutritionniste a une 7e etape : ses notes."""
    sections, _percent = _bilan_progress(profile)
    # Champs deja donnes a l'inscription (age, sexe, taille, poids...) : ne comptent pas
    # pour savoir si le patient a "commence" une etape du bilan.
    essentials = set(EssentialProfileForm._meta.fields)
    steps = []
    for idx, (sec, (key, icon, intro)) in enumerate(zip(sections, BILAN_STEP_META), start=1):
        form_class = dict(SECTION_FORMS)[key]
        started = any(
            getattr(profile, f, None) not in (None, '')
            for f in form_class._meta.fields
            if f not in essentials and PatientProfile._meta.get_field(f).get_internal_type() != 'BooleanField'
        )
        steps.append({'num': idx, 'key': key, 'form_class': form_class, 'icon': icon, 'intro': intro,
                      'title': sec['title'], 'filled': sec['filled'], 'total': sec['total'], 'started': started})
    if is_dietitian:
        filled = sum(1 for f in BilanPraticienForm._meta.fields if getattr(profile, f, None) not in (None, ''))
        steps.append({'num': len(steps) + 1, 'key': 'form7', 'form_class': BilanPraticienForm,
                      'icon': 'bi-journal-medical', 'title': _("Practitioner's Notes"),
                      'intro': _("Your observations, diagnosis and dietary plan. Not visible to the patient."),
                      'filled': filled, 'total': len(BilanPraticienForm._meta.fields), 'started': bool(filled)})
    return steps


@login_required
def bilan_view(request, patient_id=None):
    """
    Bilan initial, UNE ETAPE PAR PAGE (chaque etape est enregistree avant de passer a la suivante).
      /bilan/?step=2              -> le patient remplit le sien
      /bilan/<patient_id>/?step=2 -> la nutritionniste remplit celui d'un patient
    Boutons du formulaire (champ "action") : next, prev, goto_<n>, quit, finish.
    """
    is_dietitian = is_dietitian_check(request.user)

    if patient_id:
        # SECURITE : seule la nutritionniste accede au bilan d'un autre
        if not is_dietitian:
            return HttpResponseForbidden(_("Access denied."))
        patient = get_object_or_404(User, id=patient_id, role='patient')
        profile, _created = PatientProfile.objects.get_or_create(user=patient)
        base_url = reverse('bilan_patient', args=[patient_id])
    else:
        # SECURITE : un dieteticien n'a pas de bilan personnel
        if not is_patient_check(request.user):
            return redirect('dietitian_dashboard')
        profile, _created = PatientProfile.objects.get_or_create(user=request.user)
        patient = request.user
        base_url = reverse('bilan')

    steps = _bilan_steps(profile, is_dietitian)
    total = len(steps)
    if 'step' not in request.GET and request.method == 'GET':
        # Reprendre la ou on s'etait arrete : premiere etape pas encore commencee.
        # (les infos donnees a l'inscription ne comptent pas : un nouveau patient commence a l'etape 1)
        num = next((s['num'] for s in steps if not s['started']), 1)
    else:
        try:
            num = min(max(int(request.GET.get('step', 1)), 1), total)
        except (TypeError, ValueError):
            num = 1
    step = steps[num - 1]

    if request.method == 'POST':
        form = step['form_class'](request.POST, instance=profile, prefix=step['key'])
        action = request.POST.get('action', 'next')
        if form.is_valid():
            form.save()
            if action == 'prev':
                return redirect('%s?step=%d' % (base_url, max(num - 1, 1)))
            if action.startswith('goto_'):
                try:
                    target = min(max(int(action[5:]), 1), total)
                except ValueError:
                    target = num
                return redirect('%s?step=%d' % (base_url, target))
            if action in ('quit', 'finish') or (action == 'next' and num == total):
                return _bilan_leave(request, patient, patient_id, finished=(action != 'quit'))
            # Etape suivante + bandeau "etape terminee"
            return redirect('%s?step=%d&done=%d' % (base_url, num + 1, num))
        messages.error(request, _("Please check the highlighted fields."))
        has_errors = True
    else:
        form = step['form_class'](instance=profile, prefix=step['key'])
        has_errors = False

    # Etape qui vient d'etre terminee (affichee en haut de la page suivante)
    done_step = None
    try:
        done_num = int(request.GET.get('done', 0))
        if 1 <= done_num <= total:
            done_step = steps[done_num - 1]
    except (TypeError, ValueError):
        pass

    _sections, percent = _bilan_progress(profile)
    return render(request, 'patients/bilan_form.html', {
        'profile': profile,
        'patient': patient,
        'form': form,
        'step': step,
        'steps': steps,
        'step_num': num,
        'steps_total': total,
        'steps_left': total - num,
        'is_last': num == total,
        'done_step': done_step,
        'has_errors': has_errors,
        'bilan_percent': percent,
        'step_percent': int(round(100 * (num - 1) / total)),
    })


def _bilan_leave(request, patient, patient_id, finished):
    """Sortie du bilan (bouton "Terminer" ou "Enregistrer et quitter")."""
    if patient_id:
        messages.success(request, _("Assessment saved successfully!"))
        return redirect('patient_record', patient_id=patient_id)
    # Le patient a rempli son bilan : la nutritionniste est prevenue (bureau + e-mail, une fois)
    _msg, is_new = InboxMessage.notify_bilan(patient)
    if is_new:
        from .notifications import notify_new_bilan
        notify_new_bilan(request, patient)
    return redirect(reverse('patient_home') + ('?saved=done' if finished else '?saved=1'))


@login_required
@user_passes_test(is_patient_check, login_url='/')
def complete_profile(request):
    """Etape 1 du patient : 6 champs essentiels au lieu du bilan complet."""
    profile, _created = PatientProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = EssentialProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _("Welcome! Your space is ready."))
            return redirect('patient_home')
        messages.error(request, _("Please check the highlighted fields."))
    else:
        form = EssentialProfileForm(instance=profile)

    return render(request, 'patients/start_profile.html', {'form': form})


# =========================================================
#  ESPACE PATIENT : tableau de bord guide
# =========================================================
BILAN_SECTION_TITLES = [
    _("Identity and reason for consulting"),
    _("Health history"),
    _("Daily life"),
    _("Body measurements"),
    _("Meals and drinks"),
    _("Appetite and goals"),
]


def _bilan_progress(profile):
    """Avancement du bilan, section par section (les cases a cocher sont ignorees :
    on ne peut pas distinguer 'non' de 'pas encore repondu')."""
    sections = []
    total_filled = total_fields = 0
    for (name, FormClass), title in zip(SECTION_FORMS, BILAN_SECTION_TITLES):
        filled = count = 0
        for field_name in FormClass._meta.fields:
            field = PatientProfile._meta.get_field(field_name)
            if field.get_internal_type() == 'BooleanField':
                continue
            count += 1
            value = getattr(profile, field_name, None) if profile else None
            if value not in (None, ''):
                filled += 1
        sections.append({
            'key': name, 'title': title, 'filled': filled, 'total': count,
            'percent': int(round(100 * filled / count)) if count else 0,
        })
        total_filled += filled
        total_fields += count
    percent = int(round(100 * total_filled / total_fields)) if total_fields else 0
    return sections, percent


@login_required
@user_passes_test(is_patient_check, login_url='/')
def patient_home(request):
    """Page d'accueil du patient : ou il en est, et quoi faire ensuite."""
    profile, _created = PatientProfile.objects.get_or_create(user=request.user)
    sections, bilan_percent = _bilan_progress(profile)

    week_ago = timezone.localdate() - timedelta(days=7)
    meals_total = request.user.food_entries.count()
    meals_week = request.user.food_entries.filter(date__gte=week_ago).count()
    has_plan = MealPlan.objects.filter(patient=request.user).exists()
    last_consult = request.user.consultations.order_by('-date_consultation').first()

    steps = [
        {
            'key': 'account', 'icon': 'bi-person-check', 'done': True,
            'title': _("Create your account"),
            'text': _("Done - welcome to Nutri-Wellness Impact."),
        },
        {
            'key': 'essentials', 'icon': 'bi-person-vcard', 'done': profile.is_complete,
            'title': _("Give the essentials"),
            'text': _("Age, height and weight: the basis of your follow-up."),
            'url': reverse('complete_profile'), 'cta': _("Complete my information"),
        },
        {
            'key': 'bilan', 'icon': 'bi-clipboard2-heart', 'done': bilan_percent >= 70,
            'title': _("Fill in your nutrition assessment"),
            'text': _("About 10 minutes. You can stop and come back later: everything you enter is saved."),
            'url': reverse('bilan'), 'cta': _("Continue my assessment") if bilan_percent else _("Start my assessment"),
            'percent': bilan_percent,
        },
        {
            'key': 'diary', 'icon': 'bi-egg-fried', 'done': meals_total > 0,
            'title': _("Write down what you eat"),
            'text': _("Note your meals for a few days. Your dietitian uses them to adapt your plan."),
            'url': reverse('my_medical_record') + '?tab=diary&add=1', 'cta': _("Log a meal"),
        },
        {
            'key': 'plan', 'icon': 'bi-card-checklist', 'done': has_plan, 'waiting': not has_plan,
            'title': _("Receive your meal plan"),
            'text': _("Your plan is ready: check it every day.") if has_plan
                    else _("Your dietitian prepares it after your consultation. Nothing to do on your side."),
            'url': reverse('my_medical_record') + '?tab=plan', 'cta': _("See my plan"),
        },
    ]
    next_step = next((st for st in steps if not st['done'] and not st.get('waiting')), None)
    done_count = sum(1 for st in steps if st['done'])

    return render(request, 'patients/home_patient.html', {
        'profile': profile,
        'steps': steps,
        'next_step': next_step,
        'done_count': done_count,
        'steps_total': len(steps),
        'progress_percent': int(round(100 * done_count / len(steps))),
        'meals_week': meals_week,
        'has_plan': has_plan,
        'last_consult': last_consult,
        'just_saved': request.GET.get('saved') in ('1', 'done'),
        'bilan_finished': request.GET.get('saved') == 'done',
    })


class PatientProfileView(LoginRequiredMixin, IsPatientMixin, DetailView):
    model = PatientProfile
    template_name = 'patients/patient_profile.html'
    context_object_name = 'profile'

    def get_object(self, queryset=None):
        profile, _created = PatientProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context


@login_required
@user_passes_test(is_patient_check, login_url='/')
def patient_profile_update_view(request):
    user_instance = request.user
    profile_instance, _created = PatientProfile.objects.get_or_create(user=user_instance)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user_instance)
        profile_form = PatientProfileUpdateForm(request.POST, instance=profile_instance)

        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user_form.save()
                profile_form.save()
            messages.success(request, _("Your profile has been updated successfully!"))
            return redirect('patient_profile')
        messages.error(request, _("Please correct the errors in the form."))
    else:
        user_form = UserUpdateForm(instance=user_instance)
        profile_form = PatientProfileUpdateForm(instance=profile_instance)

    return render(request, 'patients/patient_profile_update.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile_instance,
    })


# =========================================================
#  EXPORT EXCEL  (reserve a la nutritionniste)
# =========================================================
@login_required
@user_passes_test(is_dietitian_check, login_url='/')
def export_patients_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Patients"

    headers = [
        str(_("First name")), str(_("Last name")), str(_("Email")), str(_("Role")),
        str(_("Age")), str(_("Gender")), str(_("Occupation")), str(_("Activity level")),
        str(_("Main pathology")), str(_("Diagnosis")),
        str(_("Height (cm)")), str(_("Current weight (kg)")), str(_("BMI")),
        str(_("Waist circumference (cm)")), str(_("Hip circumference (cm)")),
        str(_("Motivation level (0-10)")),
    ]
    ws.append(headers)

    search_query = request.GET.get('q')
    patients = User.objects.filter(role='patient').select_related('profile').order_by('last_name')
    if search_query:
        patients = patients.filter(
            Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(email__icontains=search_query)
        )

    for patient in patients:
        p = getattr(patient, 'profile', None)
        ws.append([
            patient.first_name,
            patient.last_name,
            patient.email,
            patient.get_role_display(),
            p.age if p else "",
            p.get_gender_display() if p else "",
            p.occupation if p else "",
            p.get_activity_level_display() if p else "",
            p.get_pathology_display() if p else "",
            p.diagnosis if p else "",
            p.height if p else "",
            p.weight if p else "",
            p.bmi if p else "",
            p.waist_circumference if p else "",
            p.hip_circumference if p else "",
            p.motivation_level if p else "",
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=export_patients.xlsx'
    wb.save(response)
    return response


# =========================================================
#  STATISTIQUES
# =========================================================
@login_required
@user_passes_test(is_dietitian_check, login_url='/')
def dietitian_stats_view(request):
    gender_stats = PatientProfile.objects.exclude(gender='').values('gender').annotate(total=Count('gender'))
    allergy_stats = PatientProfile.objects.values('allergies').annotate(total=Count('allergies'))
    activity_stats = PatientProfile.objects.exclude(activity_level='').values('activity_level').annotate(total=Count('activity_level'))
    occupation_stats = (
        PatientProfile.objects.exclude(occupation='')
        .values('occupation').annotate(total=Count('occupation')).order_by('-total')[:5]
    )
    pathology_stats = PatientProfile.objects.values('pathology').annotate(total=Count('pathology')).order_by('-total')

    averages = PatientProfile.objects.aggregate(
        avg_age=Avg('age'),
        avg_weight=Avg('weight'),
        avg_height=Avg('height'),
        avg_bmi=Avg('bmi'),
    )

    gender_choices = dict(PatientProfile._meta.get_field('gender').choices or [])
    activity_choices = dict(PatientProfile._meta.get_field('activity_level').choices or [])
    pathology_choices = dict(PatientProfile._meta.get_field('pathology').choices or [])

    context = {
        'gender_labels': json.dumps([str(gender_choices.get(i['gender'], i['gender'])) for i in gender_stats]),
        'gender_data': json.dumps([i['total'] for i in gender_stats]),

        'allergy_labels': json.dumps([str(_("With allergies")), str(_("Without allergies"))]),
        'allergy_data': json.dumps([
            next((i['total'] for i in allergy_stats if i['allergies']), 0),
            next((i['total'] for i in allergy_stats if not i['allergies']), 0),
        ]),

        'activity_labels': json.dumps([str(activity_choices.get(i['activity_level'], i['activity_level'])) for i in activity_stats]),
        'activity_data': json.dumps([i['total'] for i in activity_stats]),

        'occ_labels': json.dumps([str(i['occupation']) for i in occupation_stats]),
        'occ_data': json.dumps([i['total'] for i in occupation_stats]),

        'pathology_labels': json.dumps([str(pathology_choices.get(i['pathology'], i['pathology'])) for i in pathology_stats]),
        'pathology_data': json.dumps([i['total'] for i in pathology_stats]),

        'averages': averages,
    }
    return render(request, 'dietitians/statistics.html', context)


# =========================================================
#  CONSULTATIONS  (reserve a la nutritionniste)
# =========================================================
@login_required
@user_passes_test(is_dietitian_check, login_url='/')
def create_consultation(request, patient_id):
    patient = get_object_or_404(User, id=patient_id, role='patient')
    profile = getattr(patient, 'profile', None)

    if request.method == 'POST':
        form = ConsultationForm(request.POST)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.patient = patient
            consultation.patient_profile = profile
            consultation.dietitian = request.user
            consultation.save()
            messages.success(request, _("Consultation saved successfully!"))

            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Trigger': 'consultationSaved'})
            return redirect('patient_record', patient_id=patient.id)
    else:
        form = ConsultationForm()

    return render(request, 'dietitians/consultation_form.html', {'form': form, 'patient': patient})


@login_required
@user_passes_test(is_dietitian_check, login_url='/')
def edit_consultation(request, consult_id):
    """SECURITE : reserve a la nutritionniste + validation par formulaire."""
    consult = get_object_or_404(Consultation, id=consult_id)

    if request.method == 'POST':
        form = ConsultationForm(request.POST, instance=consult)
        if form.is_valid():
            form.save()
            messages.success(request, _("Consultation updated."))
        else:
            messages.error(request, _("Please check the highlighted fields."))
    return redirect('patient_record', patient_id=consult.patient.id)


@login_required
@user_passes_test(is_dietitian_check, login_url='/')
@require_POST
def delete_consultation(request, consult_id):
    """SECURITE : POST obligatoire (evite la suppression par simple lien)."""
    consult = get_object_or_404(Consultation, id=consult_id)
    patient_id = consult.patient.id
    consult.delete()
    messages.warning(request, _("The consultation has been permanently deleted."))
    return redirect('patient_record', patient_id=patient_id)


# =========================================================
#  JOURNAL ALIMENTAIRE  (le patient ne touche que le sien)
# =========================================================
@login_required
@user_passes_test(is_patient_check, login_url='/')
def add_food_entry(request):
    if request.method == 'POST':
        form = FoodDiaryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.patient = request.user
            entry.save()
            messages.success(request, _("Meal saved."))
            return redirect('my_medical_record')
        messages.error(request, _("Please check the highlighted fields."))
        return redirect('my_medical_record')

    return render(request, 'patients/add_food.html', {'form': FoodDiaryForm()})


@login_required
@user_passes_test(is_patient_check, login_url='/')
@require_POST
def edit_food_entry(request, entry_id):
    # SECURITE : patient=request.user -> impossible de modifier celui d'un autre
    entry = get_object_or_404(FoodDiary, id=entry_id, patient=request.user)
    form = FoodDiaryForm(request.POST, instance=entry)
    if form.is_valid():
        form.save()
        messages.success(request, _("Meal updated."))
    else:
        messages.error(request, _("Please check the highlighted fields."))
    return redirect('my_medical_record')


@login_required
@user_passes_test(is_patient_check, login_url='/')
@require_POST
def delete_food_entry(request, entry_id):
    """SECURITE : POST obligatoire + verrouille sur le patient courant."""
    entry = get_object_or_404(FoodDiary, id=entry_id, patient=request.user)
    entry.delete()
    messages.warning(request, _("The meal has been deleted."))
    return redirect('my_medical_record')


# =========================================================
#  DOSSIERS MEDICAUX
# =========================================================
def _record_context(patient, request):
    """Contexte commun aux deux vues de dossier medical."""
    all_history = patient.consultations.all().order_by('-date_consultation')
    all_food = patient.food_entries.all().order_by('-date')

    return {
        'patient': patient,
        'profile': getattr(patient, 'profile', None),
        'meal_plans': MealPlan.objects.filter(patient=patient).order_by('day'),
        'chart_history': patient.consultations.all().order_by('date_consultation'),
        'history': Paginator(all_history, 10).get_page(request.GET.get('page_h')),
        'food_log': Paginator(all_food, 10).get_page(request.GET.get('page_f')),
    }


@login_required
@user_passes_test(is_dietitian_check, login_url='/')
def patient_medical_record(request, patient_id):
    patient = get_object_or_404(User, id=patient_id, role='patient')
    context = _record_context(patient, request)
    return render(request, 'dietitians/patient_record.html', context)


@login_required
@user_passes_test(is_patient_check, login_url='/')
def my_medical_record(request):
    context = _record_context(request.user, request)
    context['food_form'] = FoodDiaryForm()
    return render(request, 'patients/my_record.html', context)


# =========================================================
#  PLAN ALIMENTAIRE  (reserve a la nutritionniste)
# =========================================================
@login_required
@user_passes_test(is_dietitian_check, login_url='/')
def manage_meal_plan(request, patient_id):
    patient = get_object_or_404(User, id=patient_id, role='patient')

    MealPlanFormSet = modelformset_factory(
        MealPlan,
        fields=('day', 'breakfast', 'morning_snack', 'lunch', 'afternoon_snack', 'dinner', 'evening_snack'),
        extra=0,
        max_num=7,
    )

    queryset = MealPlan.objects.filter(patient=patient).order_by('day')

    if request.method == 'POST':
        formset = MealPlanFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            with transaction.atomic():
                for instance in formset.save(commit=False):
                    instance.patient = patient
                    instance.save()
            messages.success(request, _("Meal plan updated successfully!"))
            return redirect('patient_record', patient_id=patient.id)
        messages.error(request, _("Please check the highlighted fields."))
    else:
        if not queryset.exists():
            MealPlanFormSet.extra = 7
            formset = MealPlanFormSet(queryset=MealPlan.objects.none())
        else:
            formset = MealPlanFormSet(queryset=queryset)

    return render(request, 'dietitians/manage_meal_plan.html', {
        'formset': formset,
        'patient': patient,
    })


# =========================================================
#  EMAIL AU PATIENT  (reserve a la nutritionniste)
# =========================================================
@login_required
@user_passes_test(is_dietitian_check, login_url='/')
def prepare_email(request, patient_id):
    patient = get_object_or_404(User, id=patient_id, role='patient')
    return render(request, 'dietitians/partials/email_form.html', {'patient': patient})


@login_required
@user_passes_test(is_dietitian_check, login_url='/')
@require_POST
def send_patient_email(request, patient_id):
    """SECURITE : connexion + role + POST obligatoires ; pas de detail technique expose."""
    patient = get_object_or_404(User, id=patient_id, role='patient')

    subject = (request.POST.get('subject') or '').strip()
    message = (request.POST.get('message') or '').strip()

    if not subject or not message:
        return HttpResponse(
            '<div class="alert alert-warning border-0">%s</div>' % _("Subject and message are required.")
        )

    greeting = patient.get_full_name() or patient.email
    full_message = "%s %s,\n\n%s\n\n%s\nNutri-Wellness Impact" % (
        _("Hello"), greeting, message, _("Kind regards,")
    )

    try:
        from .notifications import send_app_email
        send_app_email(subject, full_message, [patient.email], category="patient",
                       reply_to=[request.user.email] if request.user.email else None)
    except Exception:
        # On ne revele aucun detail technique a l'utilisateur
        return HttpResponse(
            '<div class="alert alert-danger border-0">%s</div>'
            % _("The email could not be sent. Please try again later.")
        )

    return HttpResponse(
        '<div class="alert alert-success border-0 d-flex align-items-center">'
        '<i class="bi bi-check-circle-fill me-2"></i><div>%s</div></div>'
        '<script>setTimeout(function(){'
        'var m=bootstrap.Modal.getInstance(document.getElementById("emailModal"));'
        'if(m){m.hide();}}, 2500);</script>' % _("Email sent successfully!")
    )


def _pdf_reponse(buffer, nom_fichier):
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=nom_fichier)
 
 
def _slug_patient(patient):
    base = (patient.get_full_name() or patient.email).replace(" ", "_")
    return "".join(c for c in base if c.isalnum() or c in "_-")
 
 
def _acces_dossier(request, patient_id):
    """
    Renvoie le patient si l'utilisateur a le droit d'acceder a son dossier.
    - la nutritionniste accede a tous les patients
    - un patient n'accede qu'a son propre dossier
    """
    if is_dietitian_check(request.user):
        return get_object_or_404(User, id=patient_id, role='patient')
    if str(request.user.id) == str(patient_id):
        return request.user
    raise Http404
 
 
@login_required
def export_bilan_pdf(request, patient_id):
    patient = _acces_dossier(request, patient_id)
    profile, _created = PatientProfile.objects.get_or_create(user=patient)
    buffer = io.BytesIO()
    generer_bilan_pdf(buffer, patient, profile)
    return _pdf_reponse(buffer, "bilan_%s.pdf" % _slug_patient(patient))
 
 
@login_required
def export_suivi_pdf(request, patient_id):
    patient = _acces_dossier(request, patient_id)
    profile = getattr(patient, 'profile', None)
    consultations = patient.consultations.all().order_by('-date_consultation')
    buffer = io.BytesIO()
    generer_suivi_pdf(buffer, patient, profile, consultations)
    return _pdf_reponse(buffer, "suivi_%s.pdf" % _slug_patient(patient))
 
 
@login_required
def export_plan_pdf(request, patient_id):
    patient = _acces_dossier(request, patient_id)
    profile = getattr(patient, 'profile', None)
    plans = MealPlan.objects.filter(patient=patient).order_by('day')
    buffer = io.BytesIO()
    generer_plan_pdf(buffer, patient, profile, plans)
    return _pdf_reponse(buffer, "plan_alimentaire_%s.pdf" % _slug_patient(patient))
 

# =========================================================
#  BOITE DE RECEPTION  (bureau de la nutritionniste)
# =========================================================
@login_required
@user_passes_test(is_dietitian_check, login_url='/')
def dietitian_inbox(request):
    """Deux onglets : "A traiter" (non lus) et "Historique" (lus ou repondus).
    Des qu'un message est marque comme lu ou qu'on y repond, il passe dans l'historique."""
    box = request.GET.get('box', 'new')
    if box not in ('new', 'history'):
        box = 'new'
    kind = request.GET.get('kind', 'all')
    if kind not in ('all', InboxMessage.KIND_CONTACT, InboxMessage.KIND_BILAN):
        kind = 'all'

    qs = (InboxMessage.objects.select_related('patient').prefetch_related('replies__author')
          .filter(is_read=(box == 'history')).order_by('-created_at'))
    if kind != 'all':
        qs = qs.filter(kind=kind)
    page = Paginator(qs, 15).get_page(request.GET.get('page'))
    return render(request, 'dietitians/inbox.html', {
        'page_obj': page,
        'box': box,
        'kind': kind,
        'unread_total': InboxMessage.objects.filter(is_read=False).count(),
        'history_total': InboxMessage.objects.filter(is_read=True).count(),
    })


@login_required
@user_passes_test(is_dietitian_check, login_url='/')
@require_POST
def inbox_toggle_read(request, message_id):
    msg = get_object_or_404(InboxMessage, id=message_id)
    msg.is_read = not msg.is_read
    msg.save(update_fields=['is_read'])
    return redirect(request.POST.get('next') or 'dietitian_inbox')


@login_required
@user_passes_test(is_dietitian_check, login_url='/')
@require_POST
def inbox_mark_all_read(request):
    InboxMessage.objects.filter(is_read=False).update(is_read=True)
    messages.success(request, _("All messages are marked as read."))
    return redirect('dietitian_inbox')


@login_required
@user_passes_test(is_dietitian_check, login_url='/')
@require_POST
def inbox_delete(request, message_id):
    get_object_or_404(InboxMessage, id=message_id).delete()
    messages.warning(request, _("The message has been deleted."))
    return redirect(request.POST.get('next') or 'dietitian_inbox')


# =========================================================
#  UTILISATEURS : vue d'ensemble pour la nutritionniste
#  (qui est inscrit, qui se connecte, qui a rempli son bilan, activite recente)
# =========================================================
USER_FILTERS = ('all', 'active', 'inactive', 'new', 'never', 'dormant', 'bilan_todo')


@login_required
@user_passes_test(is_dietitian_check, login_url='/')
def dietitian_users(request):
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    patients = User.objects.filter(role='patient')
    stats = {
        'total': patients.count(),
        'active': patients.filter(is_active=True).count(),
        'inactive': patients.filter(is_active=False).count(),
        'new_week': patients.filter(date_joined__gte=week_ago).count(),
        'new_month': patients.filter(date_joined__gte=month_ago).count(),
        'seen_week': patients.filter(last_login__gte=week_ago).count(),
        'never': patients.filter(last_login__isnull=True).count(),
        'dietitians': User.objects.filter(role='dietitian').count(),
        'bilan_todo': patients.filter(
            Q(profile__isnull=True) | Q(profile__age__isnull=True) | Q(profile__weight__isnull=True)).count(),
    }

    # ---- Liste filtree ----
    show = request.GET.get('show', 'all')
    if show not in USER_FILTERS:
        show = 'all'
    role = request.GET.get('role', 'patient')
    if role not in ('patient', 'dietitian', 'all'):
        role = 'patient'
    q = (request.GET.get('q') or '').strip()

    qs = User.objects.select_related('profile').annotate(
        meals_count=Count('food_entries', distinct=True),
        consult_count=Count('consultations', distinct=True),
    )
    if role != 'all':
        qs = qs.filter(role=role)
    if q:
        qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q)
                       | Q(email__icontains=q) | Q(profile__phone__icontains=q))
    if show == 'active':
        qs = qs.filter(is_active=True)
    elif show == 'inactive':
        qs = qs.filter(is_active=False)
    elif show == 'new':
        qs = qs.filter(date_joined__gte=week_ago)
    elif show == 'never':
        qs = qs.filter(last_login__isnull=True)
    elif show == 'dormant':
        # se sont deja connectes, mais pas depuis 30 jours
        qs = qs.filter(last_login__lt=month_ago)
    elif show == 'bilan_todo':
        qs = qs.filter(role='patient').filter(
            Q(profile__isnull=True) | Q(profile__age__isnull=True) | Q(profile__weight__isnull=True))

    order = request.GET.get('order', 'recent')
    ordering = {
        'recent': ['-date_joined'],
        'login': [F('last_login').desc(nulls_last=True)],
        'name': ['last_name', 'first_name', 'email'],
    }.get(order, ['-date_joined'])
    qs = qs.order_by(*ordering)

    page = Paginator(qs, 20).get_page(request.GET.get('page'))
    rows = []
    bilan_done = 0
    for u in page:
        profile = getattr(u, 'profile', None)
        percent = _bilan_progress(profile)[1] if (profile and u.role == 'patient') else None
        rows.append({'user': u, 'profile': profile, 'bilan_percent': percent})

    # Nombre de bilans bien avances (>= 70 %) sur l'ensemble des patients
    for profile in PatientProfile.objects.filter(user__role='patient'):
        if _bilan_progress(profile)[1] >= 70:
            bilan_done += 1
    stats['bilan_done'] = bilan_done

    # ---- Activite recente : seulement le nouveau (non vu), sauf si on demande l'historique ----
    activity_all = request.GET.get('activity') == 'all'
    seen = request.user.activity_seen_at
    new_events = _recent_activity(since=seen)
    activity_new_count = len(new_events)
    events = _recent_activity() if activity_all else new_events
    activity_page = Paginator(events, 8).get_page(request.GET.get('apage'))

    return render(request, 'dietitians/users.html', {
        'stats': stats,
        'rows': rows,
        'page_obj': page,
        'show': show,
        'role': role,
        'order': order,
        'q': q,
        'activity_page': activity_page,
        'activity_all': activity_all,
        'activity_new_count': activity_new_count,
    })


def _recent_activity(since=None, per_source=200):
    """Fil d'activite : inscriptions, bilans, repas notes, consultations, messages.
    since : n'afficher que ce qui est arrive apres cette date (le reste a deja ete vu)."""
    def recent(qs, field):
        if since:
            qs = qs.filter(**{field + '__gt': since})
        return qs.order_by('-' + field)[:per_source]

    events = []
    for u in recent(User.objects.filter(role='patient'), 'date_joined'):
        events.append({'when': u.date_joined, 'icon': 'bi-person-plus', 'color': '#1d4f91',
                       'who': u, 'text': _("created an account")})
    for p in recent(PatientProfile.objects.select_related('user').filter(
            updated_at__isnull=False, user__role='patient'), 'updated_at'):
        events.append({'when': p.updated_at, 'icon': 'bi-clipboard2-heart', 'color': '#5a8f3d',
                       'who': p.user, 'text': _("updated their assessment")})
    for f in recent(FoodDiary.objects.select_related('patient'), 'created_at'):
        events.append({'when': f.created_at, 'icon': 'bi-egg-fried', 'color': '#f4a020',
                       'who': f.patient, 'text': _("logged a meal")})
    consults = Consultation.objects.select_related('patient')
    if since:
        consults = consults.filter(date_consultation__gt=timezone.localdate(since))
    for c in consults.order_by('-date_consultation')[:per_source]:
        when = timezone.make_aware(datetime.combine(c.date_consultation, dtime(12, 0)))
        events.append({'when': when, 'icon': 'bi-heart-pulse', 'color': '#d62828',
                       'who': c.patient, 'text': _("had a consultation")})
    for m in recent(InboxMessage.objects.filter(kind=InboxMessage.KIND_CONTACT), 'created_at'):
        events.append({'when': m.created_at, 'icon': 'bi-chat-left-text', 'color': '#6f42c1',
                       'who': None, 'name': m.name or m.email, 'text': _("sent a message")})
    events = [e for e in events if e['when'] and (not since or e['when'] > since)]
    events.sort(key=lambda e: e['when'], reverse=True)
    return events


@login_required
@user_passes_test(is_dietitian_check, login_url='/')
@require_POST
def activity_mark_seen(request):
    """Tout ce qui est deja affiche disparait du fil (reste visible dans l'historique)."""
    request.user.activity_seen_at = timezone.now()
    request.user.save(update_fields=['activity_seen_at'])
    messages.success(request, _("Recent activity marked as seen."))
    return redirect(request.POST.get('next') or 'dietitian_users')


@login_required
@user_passes_test(is_dietitian_check, login_url='/')
@require_POST
def dietitian_toggle_user(request, user_id):
    """Active / desactive un compte patient (un compte desactive ne peut plus se connecter)."""
    target = get_object_or_404(User, id=user_id, role='patient')
    target.is_active = not target.is_active
    target.save(update_fields=['is_active'])
    if target.is_active:
        messages.success(request, _("The account has been reactivated."))
    else:
        messages.warning(request, _("The account has been deactivated: this person can no longer log in."))
    return redirect(request.POST.get('next') or 'dietitian_users')



@login_required
@user_passes_test(is_dietitian_check, login_url='/')
@require_POST
def inbox_reply(request, message_id):
    """Repondre a un message depuis l'application : l'e-mail part a l'expediteur
    (ou au patient) et la reponse reste visible sous le message."""
    msg = get_object_or_404(InboxMessage, id=message_id)
    back = request.POST.get('next') or reverse('dietitian_inbox')
    body = (request.POST.get('body') or '').strip()
    recipient = msg.email or (msg.patient.email if msg.patient else '')
    if not body:
        messages.error(request, _("Please write your reply."))
        return redirect(back)
    if not recipient:
        messages.error(request, _("This message has no email address: you cannot reply by email."))
        return redirect(back)

    if msg.kind == InboxMessage.KIND_BILAN:
        subject = str(_("Your nutrition assessment"))
    else:
        subject = "Re: %s" % (str(_("Your message to Nutri-Wellness Impact")))
    greeting = msg.name or (msg.patient.get_full_name() if msg.patient else '') or recipient
    signature = request.user.get_full_name() if request.user.get_full_name() != request.user.email else ''
    text = "%s %s,\n\n%s\n\n%s\n%s\nNutri-Wellness Impact" % (
        _("Hello"), greeting, body, _("Kind regards,"), signature)
    if msg.kind == InboxMessage.KIND_CONTACT and msg.message:
        text += "\n\n----- %s -----\n%s" % (_("Your message"), msg.message)

    from .notifications import send_app_email
    try:
        send_app_email(subject, text, [recipient], category="reply",
                       reply_to=[request.user.email] if request.user.email else None)
    except Exception:
        messages.error(request, _("The email could not be sent. Please try again later."))
        return redirect(back)

    InboxReply.objects.create(message=msg, author=request.user, subject=subject, body=body)
    if not msg.is_read:
        msg.is_read = True
        msg.save(update_fields=['is_read'])
    messages.success(request, _("Your reply has been sent to %(email)s.") % {'email': recipient})
    return redirect(back)
