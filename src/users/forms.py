from django import forms
from allauth.account.forms import SignupForm
from allauth.account.adapter import get_adapter
from django.utils.translation import gettext_lazy as _


class CustomSignupForm(SignupForm):
    first_name = forms.CharField(label=_("First name"), max_length=150, required=True)
    last_name = forms.CharField(label=_("Last name"), max_length=150, required=True)

    def save(self, request):
        # Creation de l'utilisateur via Allauth
        user = super().save(request)

        if not user:
            raise ValueError(_("Unable to create the user."))

        # Attribution des champs personnalises
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.role = getattr(user, "role", "patient") or "patient"  # Securite si le champ est absent

        user.save()
        self.user = user

        return user