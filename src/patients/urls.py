from django.urls import path

from . import views

urlpatterns = [
    # --- Redirection apres connexion ---
    path('home/', views.home_redirect_view, name='home'),

    # --- Espace patient (tableau de bord guide) ---
    path('my-space/', views.patient_home, name='patient_home'),

    # --- Profil patient ---
    path('complete_profile/', views.complete_profile, name='complete_profile'),
    path('profile/patient/', views.PatientProfileView.as_view(), name='patient_profile'),
    path('profile/patient/edit/', views.patient_profile_update_view, name='patient_profile_update'),

    # --- Bilan initial (formulaire de consultation dietetique) ---
    path('bilan/', views.bilan_view, name='bilan'),
    path('bilan/<uuid:patient_id>/', views.bilan_view, name='bilan_patient'),

    # --- Espace dieteticien ---
    path('dietitian/dashboard/', views.DietitianPatientListView.as_view(), name='dietitian_dashboard'),
    path('dietitian/statistics/', views.dietitian_stats_view, name='dietitian_statistics'),
    path('dietitian/users/', views.dietitian_users, name='dietitian_users'),
    path('dietitian/activity/seen/', views.activity_mark_seen, name='activity_mark_seen'),
    path('dietitian/users/<uuid:user_id>/toggle-active/', views.dietitian_toggle_user, name='dietitian_toggle_user'),
    path('dietitian/inbox/', views.dietitian_inbox, name='dietitian_inbox'),
    path('dietitian/inbox/read-all/', views.inbox_mark_all_read, name='inbox_mark_all_read'),
    path('dietitian/inbox/<uuid:message_id>/toggle/', views.inbox_toggle_read, name='inbox_toggle_read'),
    path('dietitian/inbox/<uuid:message_id>/delete/', views.inbox_delete, name='inbox_delete'),
    path('dietitian/inbox/<uuid:message_id>/reply/', views.inbox_reply, name='inbox_reply'),
    path('dietitian/patient/<uuid:user_id>/details/modal/', views.dietitian_patient_profile_modal, name='dietitian_patient_profile_modal'),
    path('export/patients/excel/', views.export_patients_excel, name='export_patients_excel'),

    # --- Dossiers medicaux ---
    path('patient/<uuid:patient_id>/record/', views.patient_medical_record, name='patient_record'),
    path('my-medical-file/', views.my_medical_record, name='my_medical_record'),

    # --- Consultations ---
    path('patient/<uuid:patient_id>/consultation/add/', views.create_consultation, name='create_consultation'),
    path('edit-consultation/<uuid:consult_id>/', views.edit_consultation, name='edit_consultation'),
    path('delete-consultation/<uuid:consult_id>/', views.delete_consultation, name='delete_consultation'),

    # --- Journal alimentaire ---
    path('my-diary/add/', views.add_food_entry, name='add_food_entry'),
    path('edit-food/<uuid:entry_id>/', views.edit_food_entry, name='edit_food_entry'),
    path('delete-food/<uuid:entry_id>/', views.delete_food_entry, name='delete_food_entry'),

    # --- Plan alimentaire ---
    path('patient/<uuid:patient_id>/meal-plan/', views.manage_meal_plan, name='manage_meal_plan'),

    # --- Emails ---
    path('patient/<uuid:patient_id>/prepare-email/', views.prepare_email, name='prepare_email'),
    path('patient/<uuid:patient_id>/send-email/', views.send_patient_email, name='send_patient_email'),

    # --- Exports PDF ---
    path('patient/<uuid:patient_id>/pdf/bilan/', views.export_bilan_pdf, name='export_bilan_pdf'),
    path('patient/<uuid:patient_id>/pdf/suivi/', views.export_suivi_pdf, name='export_suivi_pdf'),
    path('patient/<uuid:patient_id>/pdf/plan/', views.export_plan_pdf, name='export_plan_pdf'),
]