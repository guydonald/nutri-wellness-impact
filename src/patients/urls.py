from django.urls import path
from . import views

urlpatterns = [
    path('complete_profile/', views.complete_profile, name='complete_profile'),
    path('profile/patient/', views.PatientProfileView.as_view(), name='patient_profile'),
    path('home/', views.home_redirect_view, name='home'),
    path('profile/patient/', views.PatientProfileView.as_view(), name='patient_profile'),
    path('profile/patient/edit/', views.patient_profile_update_view, name='patient_profile_update'),
    path('dietitian/dashboard/', views.DietitianPatientListView.as_view(), name='dietitian_dashboard'),
    path('dietitian/patient/<uuid:user_id>/details/modal/', views.dietitian_patient_profile_modal, name='dietitian_patient_profile_modal'),
    path('export/patients/excel/', views.export_patients_excel, name='export_patients_excel'),
    path('dietitian/statistics/', views.dietitian_stats_view, name='dietitian_statistics'),
    path('patient/<uuid:patient_id>/consultation/add/', views.create_consultation, name='create_consultation'),
    path('patient/<uuid:patient_id>/record/', views.patient_medical_record, name='patient_record'),
    path('my-diary/add/', views.add_food_entry, name='add_food_entry'),
    path('my-medical-file/', views.my_medical_record, name='my_medical_record'),
    path('edit-food/<uuid:entry_id>/', views.edit_food_entry, name='edit_food_entry'),
    path('delete-food/<uuid:entry_id>/', views.delete_food_entry, name='delete_food_entry'),
    path('edit-consultation/<uuid:consult_id>/', views.edit_consultation, name='edit_consultation'),
    path('delete-consultation/<uuid:consult_id>/', views.delete_consultation, name='delete_consultation'),
    path('patient/<uuid:patient_id>/meal-plan/', views.manage_meal_plan, name='manage_meal_plan'),
]