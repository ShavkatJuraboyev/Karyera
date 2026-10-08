from django.contrib import admin

from employers.models import Employer


@admin.register(Employer)
class EmployerAdmin(admin.ModelAdmin):
    list_display = ("name", "stir", "region", "status", "cooperation", "created_at")
    list_filter = ("status", "cooperation", "region")
    search_fields = ("name", "stir", "contact_name")
