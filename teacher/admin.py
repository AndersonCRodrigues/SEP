from django.contrib import admin
from .models import Teacher, TeacherArea


class TeacherAreaInline(admin.TabularInline):
    model = TeacherArea
    extra = 1


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("nome_completo", "email", "matricula", "role")

    search_fields = ("nome_completo", "email", "cpf")

    inlines = (TeacherAreaInline,)
