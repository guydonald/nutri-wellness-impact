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
from django.db.models import Avg, Count, Q
from django.forms import modelformset_factory
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView
import io
from datetime import timedelta

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
from .models import Consultation, FoodDiary, MealPlan, PatientProfile

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


def _build_bilan_forms(profile, data=None, include_praticien=False):
    """Instancie chaque section sur la meme instance de profil."""
    ctx = {}
    for name, FormClass in SECTION_FORMS:
        ctx[name] = FormClass(data, instance=profile, prefix=name)
    if include_praticien:
        ctx['form7'] = BilanPraticienForm(data, instance=profile, prefix='form7')
    return ctx


@login_required
def bilan_view(request, patient_id=None):
    """
    Bilan initial.
      /bilan/              -> le patient remplit le sien
      /bilan/<patient_id>/ -> la nutritionniste remplit celui d'un patient
    """
    is_dietitian = is_dietitian_check(request.user)

    if patient_id:
        # SECURITE : seule la nutritionniste accede au bilan d'un autre
        if not is_dietitian:
            return HttpResponseForbidden(_("Access denied."))
        patient = get_object_or_404(User, id=patient_id, role='patient')
        profile, _created = PatientProfile.objects.get_or_create(user=patient)
    else:
        # SECURITE : un dieteticien n'a pas de bilan personnel
        if not is_patient_check(request.user):
            return redirect('dietitian_dashboard')
        profile, _created = PatientProfile.objects.get_or_create(user=request.user)
        patient = request.user

    if request.method == 'POST':
        forms_ctx = _build_bilan_forms(profile, request.POST, include_praticien=is_dietitian)
        if all(f.is_valid() for f in forms_ctx.values()):
            with transaction.atomic():
                for f in forms_ctx.values():
                    f.save()
            messages.success(request, _("Assessment saved successfully!"))
            if patient_id:
                return redirect('patient_record', patient_id=patient_id)
            return redirect('patient_home')
        messages.error(request, _("Please check the highlighted fields."))
    else:
        forms_ctx = _build_bilan_forms(profile, include_praticien=is_dietitian)

    forms_ctx['profile'] = profile
    forms_ctx['patient'] = patient
    sections, percent = _bilan_progress(profile)
    forms_ctx['sections'] = {sec['key']: sec for sec in sections}
    forms_ctx['bilan_percent'] = percent
    return render(request, 'patients/bilan_form.html', forms_ctx)


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
        send_mail(
            subject=subject,
            message=full_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[patient.email],
            fail_silently=False,
        )
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
 