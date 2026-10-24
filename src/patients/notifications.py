"""Previent par e-mail toutes les dieteticiennes actives.
Avec EMAIL_QUEUE=True l'e-mail part en arriere-plan : la page du patient n'attend pas."""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.urls import reverse

logger = logging.getLogger(__name__)


def send_app_email(subject, body, to, category="other", reply_to=None):
    """Envoie un e-mail du site en le classant dans l'historique (categorie conservee)."""
    from .models import QueuedEmail
    msg = EmailMessage(
        subject=subject, body=body, from_email=settings.DEFAULT_FROM_EMAIL, to=list(to),
        reply_to=list(reply_to or []), headers={QueuedEmail.HEADER_CATEGORY: category},
    )
    return msg.send(fail_silently=False)


def _dietitian_emails():
    User = get_user_model()
    return list(
        User.objects.filter(role="dietitian", is_active=True)
        .exclude(email="").values_list("email", flat=True)
    )


def _notify(subject, body, reply_to=None):
    recipients = _dietitian_emails()
    for email in recipients:  # un e-mail par personne : personne ne voit l'adresse des autres
        try:
            send_app_email(subject, body, [email], category="notification", reply_to=reply_to)
        except Exception:
            logger.exception("Notification e-mail impossible vers %s", email)
    return len(recipients)


def notify_new_bilan(request, patient):
    name = patient.get_full_name() or patient.email
    url = request.build_absolute_uri(reverse("bilan_patient", args=[patient.id]))
    inbox = request.build_absolute_uri(reverse("dietitian_inbox"))
    subject = "Nouveau bilan nutritionnel : %s" % name
    body = (
        "Bonjour,\n\n"
        "%s vient de remplir (ou mettre à jour) son bilan nutritionnel.\n\n"
        "Voir le bilan : %s\n"
        "Tous vos messages : %s\n\n"
        "Nutri-Wellness Impact"
    ) % (name, url, inbox)
    return _notify(subject, body)


def notify_new_contact_message(request, name, email, phone, message):
    inbox = request.build_absolute_uri(reverse("dietitian_inbox"))
    subject = "Nouveau message de %s" % (name or email or "un visiteur")
    body = (
        "Bonjour,\n\n"
        "Vous avez reçu un nouveau message via le formulaire de contact.\n\n"
        "Nom : %s\nE-mail : %s\nTéléphone : %s\n\n"
        "Message :\n%s\n\n"
        "Répondez directement à cet e-mail, ou depuis votre espace : %s\n\n"
        "Nutri-Wellness Impact"
    ) % (name, email, phone, message, inbox)
    return _notify(subject, body, reply_to=[email] if email else None)
