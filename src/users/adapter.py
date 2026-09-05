from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.sessions.models import Session
from django.utils import timezone

class OnlyOneSessionAdapter(DefaultAccountAdapter):
    def login(self, request, user):
        # Avant de connecter l'utilisateur, on tue ses autres sessions
        active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
        for session in active_sessions:
            data = session.get_decoded()
            if data.get('_auth_user_id') == str(user.id):
                session.delete()
        
        # On appelle la méthode de connexion normale
        super().login(request, user)