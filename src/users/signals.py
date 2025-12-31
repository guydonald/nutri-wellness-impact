from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in # Import nécessaire pour la session
from django.dispatch import receiver
from django.conf import settings
from django.contrib.sessions.models import Session
from django.utils import timezone
from patients.models import PatientProfile

# --- SIGNAL 1 : Création du profil patient ---
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_patient_profile(sender, instance, created, **kwargs):
    if created and getattr(instance, 'role', None) == 'patient':
        PatientProfile.objects.create(user=instance)

# --- SIGNAL 2 : Limiter à une seule session (Déconnexion des autres) ---
@receiver(user_logged_in)
def remove_other_sessions(sender, request, user, **kwargs):
    # On récupère toutes les sessions actives
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    
    for session in sessions:
        try:
            data = session.get_decoded()
            # On vérifie si l'ID de l'utilisateur correspond
            if data.get('_auth_user_id') == str(user.id):
                # Si ce n'est pas la session actuelle, on la supprime
                if session.session_key != request.session.session_key:
                    session.delete()
                    print(f"✅ SÉCURITÉ : Ancienne session déconnectée pour {user.username}")
        except Exception:
            continue