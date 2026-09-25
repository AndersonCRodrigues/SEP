from django.contrib import admin

from .models import Teacher, TeacherArea


class TeacherAreaInline(admin.TabularInline):
    model = TeacherArea
    extra = 1


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "matricula", "role")

    search_fields = ("first_name", "last_name", "email", "cpf")

    inlines = [TeacherAreaInline]
