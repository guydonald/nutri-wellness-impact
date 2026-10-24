from django.shortcuts import redirect
from django.urls import reverse


class ProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # 1. Les dieteticiens passent sans condition
            if getattr(request.user, 'role', None) == 'dietitian':
                return self.get_response(request)

            # 2. On ne verifie que les patients
            if getattr(request.user, 'role', None) == 'patient':

                # --- Laisser passer les requetes HTMX (modales : login, mot de passe, etc.) ---
                # Sinon la modale recoit la page de redirection complete au lieu du fragment.
                if request.headers.get('HX-Request'):
                    return self.get_response(request)

                # --- URLs toujours autorisees ---
                allowed_urls = [
                    reverse('complete_profile'),
                    reverse('account_logout'),
                    reverse('home'),
                    # Pages publiques : le patient peut toujours les consulter
                    reverse('index'),
                    reverse('resume'),
                    reverse('project'),
                    reverse('contact'),
                ]

                # --- Prefixes toujours autorises (comptes, langue, statiques, medias, admin) ---
                allowed_prefixes = [
                    '/accounts/',   # toute la zone allauth (mot de passe, email, etc.)
                    '/i18n/',       # changement de langue
                    '/static/',
                    '/media/',
                    '/admin/',
                    '/sw.js',                 # application installable (PWA)
                    '/manifest.webmanifest',
                    '/offline/',
                ]

                path = request.path
                is_allowed_prefix = any(path.startswith(p) for p in allowed_prefixes)

                # Verification du profil
                has_profile = hasattr(request.user, 'profile') and request.user.profile.age

                if not has_profile and path not in allowed_urls and not is_allowed_prefix:
                    return redirect('complete_profile')

        return self.get_response(request)