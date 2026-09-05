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
from django.views.generic import TemplateView
from django.views.decorators.http import require_POST

# Allauth imports
from allauth.account.models import EmailAddress, EmailConfirmation
from allauth.account.stages import LoginStageController, EmailVerificationStage
from allauth.account.internal import flows
from allauth.account.views import (
    LoginView, SignupView, EmailView, LogoutView, 
    ConfirmEmailView, PasswordChangeView, PasswordResetView, 
    PasswordResetDoneView, PasswordResetFromKeyView, EmailVerificationSentView
)

# Create your views here.
def index_home(request):
    return render(request, 'index.html')

def index_resume(request):
    return render(request, 'resume.html')

def index_project(request):
    return render(request, 'projects.html')

def index_contact(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        message = request.POST.get("message")

        subject = f"Nouveau message de {name}"
        body = f"""
        Nom: {name}
        Email: {email}
        Téléphone: {phone}
        
        Message:
        {message}
        """

        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,   # expéditeur
            ["contact@nutri-wellness.com"],  # destinataire
            fail_silently=False,
        )

        messages.success(request, "Your message has been sent successfully! We will get back to you soon.")
        return redirect('contact')

    return render(request, "contact.html")


class BaseAuthView:
    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return [self.ajax_template_name]
        return [self.template_name]

    def form_valid(self, form):
        # On appelle le comportement normal (qui crée la session)
        response = super().form_valid(form)
        
        # Si c'est HTMX, au lieu de renvoyer un code 302 (redirection standard),
        # on renvoie un code 204 avec le header de redirection HTMX
        if self.request.headers.get('HX-Request'):
            return HttpResponse(status=204, headers={'HX-Redirect': self.get_success_url()})
        return response
    def get_success_url(self):
        return reverse("index")

class CustomLoginView(BaseAuthView, LoginView):
    template_name = "account/login.html"
    ajax_template_name = "account/partials/login_form.html"

    def form_valid(self, form):
        # 1. On force la connexion pour créer la session
        auth_login(self.request, form.user)
        
        if self.request.headers.get('HX-Request'):
            # 2. On redirige vers l'URL nommée 'home' (qui est ton home_redirect_view)
            success_url = reverse("home") 
            return HttpResponse(status=204, headers={'HX-Redirect': success_url})
        
        return super().form_valid(form)


class CustomSignupView(BaseAuthView, SignupView):
    template_name = "account/signup.html"
    ajax_template_name = "account/partials/signup_form.html"

    def form_valid(self, form):
        # 1. On laisse la classe parente gérer la sauvegarde UNIQUE et l'envoi d'email
        response = super().form_valid(form)
        
        # 2. Si c'est du HTMX, au lieu de rediriger, on renvoie le fragment OTP
        if self.request.headers.get('HX-Request'):
            # IMPORTANT : Allauth a déjà créé self.user lors du super().form_valid(form)
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
            # On renvoie le fragment de succès (que nous allons créer juste en dessous)
            return render(self.request, "account/partials/password_change_done_inner.html")
        return redirect(self.success_url)

class CustomPasswordResetView(BaseAuthView, PasswordResetView):
    template_name = "account/password_reset.html"
    ajax_template_name = "account/partials/password_reset_form.html"
    success_url = reverse_lazy("account_reset_password_done")

class CustomPasswordResetDoneView(BaseAuthView, PasswordResetDoneView):
    template_name = "account/password_reset_done.html"
    ajax_template_name = "account/partials/password_reset_done_inner.html"

class CustomPasswordResetFromKeyView(BaseAuthView, PasswordResetFromKeyView):
    template_name = "account/password_reset_from_key.html"
    ajax_template_name = "account/partials/password_reset_from_key_inner.html"
    success_url = reverse_lazy("index")

    def form_valid(self, form):
        # 1. On exécute le changement de mot de passe (logique Allauth)
        response = super(PasswordResetFromKeyView, self).form_valid(form)
        
        # 2. Si c'est du HTMX, on renvoie le fragment de succès au lieu de rediriger
        if self.request.headers.get('HX-Request'):
            return render(self.request, "account/partials/password_reset_from_key_done_inner.html")
        
        return response
        
class CustomEmailVerificationSentView(BaseAuthView, EmailVerificationSentView):
    template_name = "account/verification_sent.html"
    ajax_template_name = "account/partials/email_verification_code.html"

class CustomConfirmEmailView(TemplateView):
    template_name = "account/email_confirm.html"
    ajax_template_name = "account/partials/email_verification_code.html" # Fragment pour la modale

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return [self.ajax_template_name]
        return [self.template_name]

    def post(self, request, *args, **kwargs):
        code_saisi = request.POST.get('code', '').strip().upper()
        process = flows.email_verification_by_code.EmailVerificationProcess.resume(request)
        stage = LoginStageController.enter(request, EmailVerificationStage.key)
        
        if process and process.code == code_saisi:
            process.finish()
            EmailAddress.objects.filter(email=process.state.get("email")).update(verified=True)
            if stage: stage.exit()
            
            messages.success(request, "Congratulations, your account is validated !")
            
            if request.headers.get('HX-Request'):
                # Redirection forcée de toute la page vers le login
                return HttpResponse(status=204, headers={'HX-Redirect': reverse('account_login')})
            return redirect('account_login')
        
        # SI LE CODE EST FAUX :
        if request.headers.get('HX-Request'):
            # On renvoie juste le fragment avec l'erreur
            return render(request, self.ajax_template_name, {'error': "Invalid or expired code."})
            
        messages.error(request, "Invalid code.")
        return self.render_to_response(self.get_context_data())

# --- VUE EMAIL (CORRIGÉE) ---
class CustomEmailView(BaseAuthView, EmailView):
    template_name = "account/email_confirm.html" # Correction du nom du fichier
    ajax_template_name = "account/partials/email_verification_code.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('HX-Request'):
            messages.success(self.request, "A new code has been sent!")
            return render(self.request, self.ajax_template_name)
        return response
