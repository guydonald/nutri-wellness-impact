from django.contrib import admin
from .models import PatientProfile, Consultation, MealPlan, FoodDiary

# Register your models here.
admin.site.register(PatientProfile)
admin.site.register(Consultation)
admin.site.register(MealPlan)
admin.site.register(FoodDiary)