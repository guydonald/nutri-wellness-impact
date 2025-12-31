from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index_home, name='index'),
    path('resume', views.index_resume, name='resume'),
    path('project', views.index_project, name='project'),
    path('contact', views.index_contact, name='contact'),
    path('accounts/', include('allauth.urls')),
]