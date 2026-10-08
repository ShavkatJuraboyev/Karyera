from django.contrib import admin

from events.models import Event, EventRegistration


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_type", "start_at", "location", "is_published")
    list_filter = ("event_type", "is_published")
    search_fields = ("title", "location")


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "attended", "created_at")
    list_filter = ("attended",)
