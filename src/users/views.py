from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.conf import settings
from allauth.account.views import LoginView, SignupView
from allauth.account.forms import LoginForm, SignupForm
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect

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

        return render(request, "contact.html", {"success": True})

    return render(request, "contact.html")
