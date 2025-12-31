from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.sessions.models import Session
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class MonAdaptateurCompte(DefaultAccountAdapter):
    
    def login(self, request, user):
        # 1. On cherche les sessions actives en base de données
        sessions = Session.objects.filter(expire_date__gte=timezone.now())
        
        count = 0
        for session in sessions:
            try:
                data = session.get_decoded()
                # On vérifie si l'ID de l'utilisateur correspond
                if data.get('_auth_user_id') == str(user.pk):
                    # On supprime l'ancienne session
                    session.delete()
                    count += 1
            except Exception:
                continue
        
        if count > 0:
            print(f"--- [SÉCURITÉ] {count} ancienne(s) session(s) supprimée(s) pour {user.username} ---")
        
        # 2. On appelle la méthode originale pour finaliser la connexion
        return super().login(request, user)