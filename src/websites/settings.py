from pathlib import Path
from django.utils.translation import gettext_lazy as _
import os


SITE_ID = 1
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-dombq04k=vdkh#)_8@&o_#pke6xq0q^nl*urkkom0v^o@(2_2%'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Application definition

INSTALLED_APPS = [
    'unfold',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'users.apps.UsersConfig',
    'patients',
    'community',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    "crispy_forms",
    "crispy_bootstrap5",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "allauth.account.middleware.AccountMiddleware",
    'django.middleware.locale.LocaleMiddleware',

    # Ton nouveau middleware (Remplace 'patients' par le nom de ton app)
    'patients.middleware.ProfileCompletionMiddleware',
]

ROOT_URLCONF = 'websites.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'websites.wsgi.application'


SOCIALACCOUNT_PROVIDERS = {
    'google': {
        # For each OAuth based provider, either add a ``SocialApp``
        # (``socialaccount`` app) containing the required client
        # credentials, or list them here:
        'APP': {
            'client_id': '123',
            'secret': '456',
            'key': ''
        }
    }
}


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'fr' # Langue par défaut
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('fr', _('Français')),
    ('en', _('English')),
]


LOCALE_PATHS = [
    BASE_DIR / 'locale/',
]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, "websites/static")]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# 🔐 Modèle personnalisé
AUTH_USER_MODEL = 'users.CustomUser'

# 🎨 Formulaires
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# 🧩 Adapter et formulaire Allauth
ACCOUNT_ADAPTER = "users.adapters.MonAdaptateurCompte"
MFA_ADAPTER = "allauth.mfa.adapter.DefaultMFAAdapter"

ACCOUNT_FORMS = {'signup': 'users.forms.CustomSignupForm'}

# 🔑 Authentification
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_USER_MODEL_USERNAME_FIELD = None

# 🧾 Champs obligatoires à l'inscription
ACCOUNT_SIGNUP_FIELDS = [
    "email*",
    "password1",
    "password2",
]

# ✅ Email obligatoire et vérification
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_PHONE_VERIFICATION_ENABLED = False
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = 'home'
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = "/accounts/login/"
ACCOUNT_EMAIL_CONFIRMATION_REDIRECT_URL = 'home'  # ou vers une page intermédiaire si besoin

# 🔐 Redirections après actions
LOGIN_REDIRECT_URL = 'home'
ACCOUNT_LOGIN_REDIRECT_URL = 'home'
ACCOUNT_SIGNUP_REDIRECT_URL = '/accounts/confirm-email/'
ACCOUNT_LOGOUT_REDIRECT_URL = "/"

# ⏱️ Codes de sécurité
ACCOUNT_LOGIN_BY_CODE_ENABLED = True
ACCOUNT_LOGIN_BY_CODE_TIMEOUT = 300
ACCOUNT_LOGIN_BY_CODE_MAX_ATTEMPTS = 3
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = True

ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED = True
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_TIMEOUT = 600
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_MAX_ATTEMPTS = 3

ACCOUNT_PASSWORD_RESET_BY_CODE_TIMEOUT = 600
ACCOUNT_PASSWORD_RESET_BY_CODE_MAX_ATTEMPTS = 3

# 🧠 Sécurité anti-abus
ACCOUNT_PREVENT_ENUMERATION = True
ACCOUNT_RATE_LIMITS = {
    "login": "5/m",
    "signup": "3/m",
    "confirm_email": "3/m",
    "request_login_code": "3/m",
    "login_failed": "5/m",  # remplace les anciens LIMIT/TIMEOUT
}

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
# En production, activez : SECURE_SSL_REDIRECT = True

EMAIL_HOST = "smtp.zoho.com"
EMAIL_HOST_USER = "guydon@zohomail.com"
EMAIL_USE_TLS = False
EMAIL_USE_SSL = True
DEFAULT_FROM_EMAIL = "guydon@zohomail.com"
EMAIL_PORT = 465
EMAIL_HOST_PASSWORD = "WCT9KMBd1XwC"
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"