from django.contrib import admin

from core.models import AuditLog, News, Notification


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_published", "is_pinned", "published_at")
    list_filter = ("category", "is_published")
    search_fields = ("title", "body")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("user__username", "title")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Audit jurnali faqat o'qish uchun: yozuvlarni o'zgartirish yoki o'chirish mumkin emas."""
    list_display = ("created_at", "username", "action", "object_repr", "ip_address")
    list_filter = ("action",)
    search_fields = ("username", "object_repr", "details", "ip_address")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
