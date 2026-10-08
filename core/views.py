from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.models import Direction, Role, User
from accounts.permissions import STAFF_ROLES, role_required
from core.models import AuditLog, News, Notification
from events.models import Event
from employers.models import Employer
from students.models import EmploymentStatus, StudentProfile
from vacancies.models import Vacancy


def home(request):
    graduates = StudentProfile.objects.filter(user__role=Role.GRADUATE)
    hired = graduates.filter(employment_status__in=[EmploymentStatus.EMPLOYED, EmploymentStatus.SELF_EMPLOYED]).count()
    stats = {
        "vacancies": Vacancy.objects.published().count(),
        "employers": Employer.objects.filter(status=Employer.Status.APPROVED).count(),
        "candidates": User.objects.filter(role__in=[Role.STUDENT, Role.GRADUATE], is_active=True).count(),
        "hired": hired,
    }
    return render(request, "core/home.html", {
        "stats": stats,
        "vacancies": Vacancy.objects.published().select_related("employer").order_by("-published_at")[:6],
        "events": Event.objects.filter(is_published=True, start_at__gte=timezone.now()).order_by("start_at")[:3],
        "news": News.objects.filter(is_published=True, published_at__lte=timezone.now())[:3],
    })


@login_required
def redirect_by_role(request):
    role = request.user.role
    if role in (Role.STUDENT, Role.GRADUATE):
        return redirect("students:profile")
    if role == Role.EMPLOYER:
        return redirect("employers:dashboard")
    return redirect("reports:dashboard")


def news_list(request):
    qs = News.objects.filter(is_published=True, published_at__lte=timezone.now())
    category = request.GET.get("category", "")
    if category in News.Category.values:
        qs = qs.filter(category=category)
    page = Paginator(qs, 9).get_page(request.GET.get("page"))
    return render(request, "core/news_list.html", {"page": page, "category": category, "categories": News.Category.choices})


def news_detail(request, pk):
    qs = News.objects.all()
    if not (request.user.is_authenticated and request.user.role in STAFF_ROLES):
        qs = qs.filter(is_published=True, published_at__lte=timezone.now())
    return render(request, "core/news_detail.html", {"item": get_object_or_404(qs, pk=pk)})


@login_required
def notifications(request):
    qs = Notification.objects.filter(user=request.user)
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "core/notifications.html", {"page": page})


@login_required
def notification_open(request, pk):
    item = get_object_or_404(Notification, pk=pk, user=request.user)
    if not item.is_read:
        item.is_read = True
        item.save(update_fields=["is_read"])
    target = item.link or reverse("core:notifications")
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}) or not target.startswith("/"):
        target = reverse("core:notifications")
    return redirect(target)


@login_required
@require_POST
def notifications_read_all(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, "Barcha bildirishnomalar o'qilgan deb belgilandi.")
    return redirect("core:notifications")


def directions_json(request):
    """Fakultet tanlanganda yo'nalishlar ro'yxati (bog'langan tanlov maydonlari uchun)."""
    qs = Direction.objects.filter(is_active=True)
    faculty = request.GET.get("faculty", "")
    if faculty.isdigit():
        qs = qs.filter(faculty_id=int(faculty))
    else:
        qs = qs.none()
    return JsonResponse({"results": [{"id": d.pk, "name": d.name} for d in qs.order_by("name")]})


def health(request):
    """Server monitoringi uchun sog'liq tekshiruvi."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db = "ok"
    except Exception:
        db = "error"
    code = 200 if db == "ok" else 503
    return JsonResponse({"status": "ok" if db == "ok" else "error", "database": db, "time": timezone.now().isoformat()}, status=code)


@role_required(Role.ADMIN)
def audit_list(request):
    qs = AuditLog.objects.select_related("user")
    g = request.GET
    action = g.get("action", "")
    q = g.get("q", "").strip()
    if action in AuditLog.Action.values:
        qs = qs.filter(action=action)
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(object_repr__icontains=q) | Q(details__icontains=q) | Q(ip_address__icontains=q))
    if g.get("date_from"):
        qs = qs.filter(created_at__date__gte=g["date_from"]) if _valid_date(g["date_from"]) else qs
    if g.get("date_to"):
        qs = qs.filter(created_at__date__lte=g["date_to"]) if _valid_date(g["date_to"]) else qs
    page = Paginator(qs, 30).get_page(g.get("page"))
    return render(request, "core/audit_list.html", {"page": page, "g": g, "actions": AuditLog.Action.choices})


def _valid_date(value):
    from datetime import datetime
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def handler403(request, exception=None):
    return render(request, "403.html", status=403)


def handler404(request, exception=None):
    return render(request, "404.html", status=404)


def handler500(request):
    return render(request, "500.html", status=500)
