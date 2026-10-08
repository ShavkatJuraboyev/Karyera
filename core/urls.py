from django.urls import path

from accounts.models import Direction, Faculty
from core import views
from core.crud import crud_patterns
from core.forms_manage import DirectionForm, FacultyForm, NewsForm
from core.models import News

app_name = "core"


def _faculty_can_delete(obj):
    if obj.directions.exists() or obj.students.exists() or obj.staff_users.exists():
        return False, "Bu fakultetga yo'nalishlar, talabalar yoki xodimlar bog'langan. O'chirish o'rniga uni «Faol emas» holatiga o'tkazing."
    return True, ""


def _direction_can_delete(obj):
    if obj.students.exists():
        return False, "Bu yo'nalishda talabalar mavjud. O'chirish o'rniga uni «Faol emas» holatiga o'tkazing."
    return True, ""


def _news_pre_save(request, obj, created):
    if created:
        obj.author = request.user


urlpatterns = [
    path("", views.home, name="home"),
    path("yonaltirish/", views.redirect_by_role, name="redirect_by_role"),
    path("yangiliklar/", views.news_list, name="news_list"),
    path("yangiliklar/<int:pk>/", views.news_detail, name="news_detail"),
    path("bildirishnomalar/", views.notifications, name="notifications"),
    path("bildirishnomalar/oqildi/", views.notifications_read_all, name="notifications_read_all"),
    path("bildirishnomalar/<int:pk>/ochish/", views.notification_open, name="notification_open"),
    path("malumotnoma/yonalishlar/", views.directions_json, name="directions_json"),
    path("health/", views.health, name="health"),
    path("boshqaruv/audit/", views.audit_list, name="audit_list"),
]
urlpatterns += crud_patterns(
    slug="fakultetlar", name="faculty", namespace="core", model=Faculty, form_class=FacultyForm, title="Fakultetlar",
    columns=[("Nomi", "name"), ("Kodi", "code"), ("Faol", "is_active")], search_fields=("name", "code"), can_delete=_faculty_can_delete,
)
urlpatterns += crud_patterns(
    slug="yonalishlar", name="direction", namespace="core", model=Direction, form_class=DirectionForm, title="Ta'lim yo'nalishlari",
    columns=[("Yo'nalish", "name"), ("Fakultet", "faculty"), ("Shifri", "code"), ("Faol", "is_active")],
    search_fields=("name", "code", "faculty__name"), can_delete=_direction_can_delete,
    queryset=lambda: Direction.objects.select_related("faculty"),
)
urlpatterns += crud_patterns(
    slug="yangiliklar", name="news_manage", namespace="core", model=News, form_class=NewsForm, title="Yangiliklar va e'lonlar",
    columns=[("Sarlavha", "title"), ("Turkum", "get_category_display"), ("E'lon vaqti", "published_at"), ("E'lon qilingan", "is_published"), ("Qadalgan", "is_pinned")],
    search_fields=("title", "body"), multipart=True, pre_save=_news_pre_save,
)
