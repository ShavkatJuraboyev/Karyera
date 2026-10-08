from django.contrib import admin

from vacancies.models import Application, Vacancy


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = ("title", "employer", "region", "status", "deadline", "published_at")
    list_filter = ("status", "employment_type", "region")
    search_fields = ("title", "employer__name")
    filter_horizontal = ("directions",)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("applicant", "vacancy", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("applicant__username", "applicant__last_name", "vacancy__title")
