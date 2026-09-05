from django.contrib import admin
from .models import Teacher

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("nome_completo", "email", "matricula", "role")
    
    search_fields = ("nome_completo", "email", "cpf")
    
    filter_horizontal = ("acting_areas",)