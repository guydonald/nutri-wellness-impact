from django.shortcuts import redirect
from django.urls import reverse

class ProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # 1. On laisse passer les diététiciens sans condition
            if request.user.role == 'dietitian':
                return self.get_response(request)

            # 2. On vérifie seulement les patients
            if request.user.role == 'patient':
                allowed_urls = [
                    reverse('complete_profile'),
                    reverse('account_logout'),
                    reverse('home'), # Ajoute 'home' ici pour laisser la vue pivot travailler
                    '/i18n/',
                ]
                
                # Vérification du profil
                has_profile = hasattr(request.user, 'profile') and request.user.profile.age
                if not has_profile and request.path not in allowed_urls and not request.path.startswith('/static/'):
                    return redirect('complete_profile')

        return self.get_response(request)