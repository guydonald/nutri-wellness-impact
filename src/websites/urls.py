from django.contrib import admin
from django.views.generic import TemplateView
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('', include('patients.urls')),
    path('', include('forum.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('google922b44e7298d2a4b.html', TemplateView.as_view(template_name='google922b44e7298d2a4b.html'), name='google-verification'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
