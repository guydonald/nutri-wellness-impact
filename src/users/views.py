import logging
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.views.decorators.http import require_POST
from django.views.decorators.cache import cache_control

# Allauth imports
from allauth.account.models import EmailAddress, EmailConfirmation
from allauth.account.stages import LoginStageController, EmailVerificationStage
from allauth.account.internal import flows
from allauth.account.views import (
    LoginView, SignupView, EmailView, LogoutView,
    ConfirmEmailView, PasswordChangeView, PasswordResetView,
    PasswordResetDoneView, PasswordResetFromKeyView, EmailVerificationSentView
)


# ============================================================
# PAGES PUBLIQUES
# ============================================================
def index_home(request):
    return render(request, 'index.html')

def index_resume(request):
    return render(request, 'resume.html')

def index_project(request):
    return render(request, 'projects.html')

def index_contact(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        email = (request.POST.get("email") or "").strip()
        phone = (request.POST.get("phone") or "").strip()
        message = (request.POST.get("message") or "").strip()

        if not message:
            messages.error(request, _("Please write your message."))
            return redirect('contact')

        # 1. Le message est d'abord ENREGISTRE : la nutritionniste le retrouve dans son bureau
        #    (rubrique Messages), meme si l'envoi de l'email echoue.
        from patients.models import InboxMessage
        InboxMessage.objects.create(
            kind=InboxMessage.KIND_CONTACT,
            name=name[:150], email=email[:254], phone=phone[:30], message=message,
        )

        # 2. Toutes les dieteticiennes sont prevenues par e-mail (en arriere-plan si EMAIL_QUEUE=True)
        from patients.notifications import notify_new_contact_message
        if not notify_new_contact_message(request, name, email, phone, message):
            # aucune dieteticienne enregistree : on garde l'ancienne adresse de contact
            try:
                from patients.notifications import send_app_email
                send_app_email(
                    "Nouveau message de %s" % name,
                    "Nom: %s\nEmail: %s\nTéléphone: %s\n\nMessage:\n%s" % (name, email, phone, message),
                    ["contact@nutri-wellnessimpact.com"], category="notification",
                    reply_to=[email] if email else None,
                )
            except Exception:
                logging.getLogger(__name__).exception("Envoi de l'email de contact impossible")

        messages.success(request, _("Your message has been sent successfully! We will get back to you soon."))
        return redirect('contact')

    return render(request, "contact.html")


# ============================================================
# BASE AUTH (logique HTMX partagee)
# ============================================================
class BaseAuthView:
    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return [self.ajax_template_name]
        return [self.template_name]

    def form_valid(self, form):
        # Comportement normal (cree la session)
        response = super().form_valid(form)
        # En HTMX : code 204 + header de redirection HTMX au lieu du 302 standard
        if self.request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Redirect': self.get_success_url()})
        return response

    def get_success_url(self):
        return reverse("index")


class CustomLoginView(BaseAuthView, LoginView):
    template_name = "account/login.html"
    ajax_template_name = "account/partials/login_form.html"

    def form_valid(self, form):
        # 1. Force la connexion pour creer la session
        auth_login(self.request, form.user)
        if self.request.headers.get('HX-Request'):
            success_url = reverse("home")
            return HttpResponse(status=204, headers={'HX-Redirect': success_url})
        return super().form_valid(form)


class CustomSignupView(BaseAuthView, SignupView):
    template_name = "account/signup.html"
    ajax_template_name = "account/partials/signup_form.html"

    def form_valid(self, form):
        # La classe parente gere la sauvegarde et l'envoi de l'email
        response = super().form_valid(form)
        # En HTMX : renvoie le fragment de saisie du code
        if self.request.headers.get('HX-Request'):
            html = render_to_string("account/partials/email_verification_code.html", request=self.request)
            return HttpResponse(html)
        return response


class CustomLogoutView(BaseAuthView, LogoutView):
    template_name = "account/logout.html"
    ajax_template_name = "account/partials/logout_confirm.html"

    def get_next_redirect_url(self):
        return reverse_lazy("home")


class CustomPasswordChangeView(BaseAuthView, PasswordChangeView):
    template_name = "account/password_change.html"
    ajax_template_name = "account/partials/password_change_form.html"

    def form_valid(self, form):
        PasswordChangeView.form_valid(self, form)
        if self.request.headers.get('HX-Request'):
            return render(self.request, "account/partials/password_change_done_inner.html")
        return redirect(self.success_url)


class CustomPasswordResetView(PasswordResetView):
    """Demande de reinitialisation - PAGE PLEINE (plus de modale).
 
    On n'herite plus de BaseAuthView ni ne force success_url :
    allauth gere lui-meme la redirection vers la saisie du code.
    """
    template_name = "account/password_reset.html"


class CustomPasswordResetDoneView(PasswordResetDoneView):
    """Confirmation d'envoi - PAGE PLEINE."""
    template_name = "account/password_reset_done.html"


class CustomPasswordResetFromKeyView(PasswordResetFromKeyView):
    """Saisie du nouveau mot de passe - PAGE PLEINE."""
    template_name = "account/password_reset_from_key.html"
    success_url = reverse_lazy("account_reset_password_from_key_done")


class CustomEmailVerificationSentView(BaseAuthView, EmailVerificationSentView):
    template_name = "account/verification_sent.html"
    ajax_template_name = "account/partials/email_verification_code.html"


class CustomConfirmEmailView(TemplateView):
    template_name = "account/email_confirm.html"
    ajax_template_name = "account/partials/email_verification_code.html"  # Fragment pour la modale

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return [self.ajax_template_name]
        return [self.template_name]

    @staticmethod
    def _normalize(code):
        # Enleve tirets/espaces et met en majuscules pour une comparaison robuste.
        # allauth 65+ genere des codes au format XXXX-XXXX (RFC 8628).
        return (code or "").replace("-", "").replace(" ", "").strip().upper()

    def post(self, request, *args, **kwargs):
        code_saisi = self._normalize(request.POST.get('code', ''))
        process = flows.email_verification_by_code.EmailVerificationProcess.resume(request)
        stage = LoginStageController.enter(request, EmailVerificationStage.key)

        code_attendu = self._normalize(process.code) if process else None

        if process and code_attendu and code_attendu == code_saisi:
            process.finish()
            EmailAddress.objects.filter(email=process.state.get("email")).update(verified=True)
            if stage:
                stage.exit()

            messages.success(request, _("Congratulations, your account has been validated!"))

            if request.headers.get('HX-Request'):
                return HttpResponse(status=204, headers={'HX-Redirect': reverse('account_login')})
            return redirect('account_login')

        # Code faux ou expire
        if request.headers.get('HX-Request'):
            return render(request, self.ajax_template_name, {'error': _("Invalid or expired code.")})

        messages.error(request, _("Invalid code."))
        return self.render_to_response(self.get_context_data())


class CustomEmailView(BaseAuthView, EmailView):
    template_name = "account/email_confirm.html"
    ajax_template_name = "account/partials/email_verification_code.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('HX-Request'):
            messages.success(self.request, _("A new code has been sent!"))
            return render(self.request, self.ajax_template_name)
        return response


# ============================================================
# APPLICATION INSTALLABLE (PWA)
# ============================================================
@cache_control(max_age=86400, public=True)
def pwa_manifest(request):
    return render(request, "pwa/manifest.webmanifest", content_type="application/manifest+json")


@cache_control(max_age=0, no_cache=True)  # le navigateur doit toujours voir la derniere version
def pwa_service_worker(request):
    response = render(request, "pwa/sw.js", content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response


def pwa_offline(request):
    return render(request, "pwa/offline.html")
