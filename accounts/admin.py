from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts.models import Direction, Faculty, User
from core.models import AuditLog
from core.services import audit


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "full_name", "email", "role", "faculty", "is_active")
    list_filter = ("role", "is_active", "faculty")
    search_fields = ("username", "first_name", "last_name", "email", "phone")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Karyera SIES", {"fields": ("patronymic", "phone", "role", "faculty", "telegram_chat_id")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Karyera SIES", {"fields": ("role", "faculty", "email", "first_name", "last_name")}),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        changed = ", ".join(form.changed_data) if change else "yangi foydalanuvchi"
        action = AuditLog.Action.ROLE_CHANGE if ("role" in form.changed_data or "is_active" in form.changed_data) else (
            AuditLog.Action.USER_UPDATE if change else AuditLog.Action.USER_CREATE)
        audit(action, request=request, obj=obj, details=f"Django admin: {changed}")


class DirectionInline(admin.TabularInline):
    model = Direction
    extra = 0


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    inlines = [DirectionInline]


@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    list_display = ("name", "faculty", "code", "is_active")
    list_filter = ("faculty", "is_active")
    search_fields = ("name", "code")
