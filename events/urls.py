from django.urls import path

from core.crud import crud_patterns
from events import views
from events.forms import EventForm
from events.models import Event

app_name = "events"

urlpatterns = [
    path("tadbirlar/", views.event_list, name="list"),
    path("tadbirlar/<int:pk>/", views.event_detail, name="detail"),
    path("tadbirlar/<int:pk>/royxat/", views.register, name="register"),
    path("tadbirlar/<int:pk>/bekor/", views.cancel, name="cancel"),
    path("kabinet/tadbirlarim/", views.my_events, name="mine"),
    path("boshqaruv/tadbirlar/<int:pk>/ishtirokchilar/", views.participants, name="participants"),
] + crud_patterns(
    slug="tadbirlar", name="manage", namespace="events", model=Event, form_class=EventForm, title="Karyera tadbirlari",
    columns=[("Nomi", "title"), ("Turi", "get_event_type_display"), ("Boshlanishi", "start_at"), ("Joyi", "location"),
             ("Ro'yxatdan o'tgan", "registered_count"), ("E'lon", "is_published")],
    search_fields=("title", "location"),
    pre_save=lambda request, obj, created: setattr(obj, "created_by", obj.created_by or request.user),
    extra_links=[("Ishtirokchilar", "participants", "pk")],
)
