from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index_home, name='index'),
    path('resume', views.index_resume, name='resume'),
    path('project', views.index_project, name='project'),
    path('contact', views.index_contact, name='contact'),
    path('manifest.webmanifest', views.pwa_manifest, name='pwa_manifest'),
    path('sw.js', views.pwa_service_worker, name='pwa_service_worker'),
    path('offline/', views.pwa_offline, name='pwa_offline'),
    path('accounts/login/', views.CustomLoginView.as_view(), name='account_login'),
    path('accounts/signup/', views.CustomSignupView.as_view(), name='account_signup'),
    path('accounts/logout/', views.CustomLogoutView.as_view(), name='account_logout'),
    path('accounts/password/change/', views.CustomPasswordChangeView.as_view(), name='account_change_password'),
    path('accounts/password/reset/', views.CustomPasswordResetView.as_view(), name='account_reset_password'),
    path('accounts/confirm-email/<str:key>/', views.CustomConfirmEmailView.as_view(), name='account_confirm_email'),
    path('accounts/confirm-email/', views.CustomConfirmEmailView.as_view(), name='account_confirm_email_no_key'),
    path('accounts/confirm-email/sent/', views.CustomEmailVerificationSentView.as_view(), name='account_email_verification_sent'),
    path('accounts/email/', views.CustomEmailView.as_view(), name='account_email'),
    path('accounts/', include('allauth.urls')),
]
