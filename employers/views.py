from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import Region, Role
from accounts.permissions import STAFF_ROLES, role_required
from core.models import AuditLog
from core.services import audit, notify
from employers.forms import EmployerForm, EmployerModerationForm
from employers.models import Employer
from vacancies.models import Application, Vacancy


def get_employer(user):
    try:
        return user.employer
    except Employer.DoesNotExist:
        raise Http404("Ish beruvchi profili topilmadi")


@role_required(Role.EMPLOYER)
def dashboard(request):
    employer = get_employer(request.user)
    vacancies = employer.vacancies.all()
    apps = Application.objects.filter(vacancy__employer=employer)
    from events.models import Event
    context = {
        "employer": employer,
        "counts": {
            "total": vacancies.count(),
            "published": vacancies.filter(status=Vacancy.Status.PUBLISHED).count(),
            "pending": vacancies.filter(status=Vacancy.Status.PENDING).count(),
            "draft": vacancies.filter(status=Vacancy.Status.DRAFT).count(),
            "applications": apps.count(),
            "new_applications": apps.filter(status=Application.Status.SENT).count(),
            "interviews": apps.filter(status=Application.Status.INTERVIEW).count(),
            "accepted": apps.filter(status=Application.Status.ACCEPTED).count(),
        },
        "recent_applications": apps.select_related("applicant", "vacancy").order_by("-created_at")[:8],
        "events": Event.objects.filter(is_published=True, start_at__gte=timezone.now()).order_by("start_at")[:4],
    }
    return render(request, "employers/dashboard.html", context)


@role_required(Role.EMPLOYER)
def profile_edit(request):
    employer = get_employer(request.user)
    form = EmployerForm(request.POST or None, request.FILES or None, instance=employer)
    if request.method == "POST" and form.is_valid():
        # STIR o'zgartirilsa qayta tasdiqlash talab qilinadi
        stir_changed = "stir" in form.changed_data
        employer = form.save()
        if stir_changed and employer.status == Employer.Status.APPROVED:
            employer.status = Employer.Status.PENDING
            employer.status_comment = "STIR o'zgartirildi — qayta tasdiqlash talab qilinadi"
            employer.save(update_fields=["status", "status_comment"])
            messages.warning(request, "STIR o'zgartirilgani sababli tashkilot qayta tasdiqlanishi kerak.")
        audit(AuditLog.Action.DATA_CHANGE, request=request, obj=employer, details="Tashkilot profili yangilandi")
        messages.success(request, "Tashkilot ma'lumotlari saqlandi.")
        return redirect("employers:dashboard")
    return render(request, "employers/profile_form.html", {"form": form, "employer": employer})


# ---------------------------------------------------------------- Ommaviy ko'rinish
def public_list(request):
    qs = Employer.objects.filter(status=Employer.Status.APPROVED).annotate(
        open_count=Count("vacancies", filter=Q(vacancies__status=Vacancy.Status.PUBLISHED, vacancies__deadline__gte=timezone.localdate()))
    )
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(industry__icontains=q))
    region = request.GET.get("region", "")
    if region in Region.values:
        qs = qs.filter(region=region)
    page = Paginator(qs.order_by("name"), 12).get_page(request.GET.get("page"))
    return render(request, "employers/public_list.html", {"page": page, "q": q, "region": region, "regions": Region.choices})


def public_detail(request, pk):
    qs = Employer.objects.all() if (request.user.is_authenticated and request.user.role in STAFF_ROLES) else Employer.objects.filter(status=Employer.Status.APPROVED)
    employer = get_object_or_404(qs, pk=pk)
    vacancies = employer.vacancies.published()
    return render(request, "employers/public_detail.html", {"employer": employer, "vacancies": vacancies})


# ---------------------------------------------------------------- Karyera markazi: ish beruvchilar bazasi
@role_required(*STAFF_ROLES)
def manage_list(request):
    qs = Employer.objects.annotate(vacancy_count=Count("vacancies", distinct=True))
    status = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()
    coop = request.GET.get("coop", "")
    if status in Employer.Status.values:
        qs = qs.filter(status=status)
    if coop in Employer.Cooperation.values:
        qs = qs.filter(cooperation=coop)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(stir__icontains=q) | Q(contact_name__icontains=q))
    page = Paginator(qs.order_by("-created_at"), 20).get_page(request.GET.get("page"))
    return render(request, "employers/manage_list.html", {
        "page": page, "status": status, "q": q, "coop": coop,
        "statuses": Employer.Status.choices, "coops": Employer.Cooperation.choices,
    })


@role_required(*STAFF_ROLES)
def manage_detail(request, pk):
    employer = get_object_or_404(Employer.objects.select_related("user"), pk=pk)
    old_status = employer.status
    form = EmployerModerationForm(request.POST or None, instance=employer)
    if request.method == "POST" and form.is_valid():
        employer = form.save()
        details = f"Holat: {old_status} → {employer.status}; hamkorlik: {employer.cooperation}"
        audit(AuditLog.Action.EMPLOYER_STATUS, request=request, obj=employer, details=details)
        if employer.status != old_status:
            text = f"Tashkilotingiz holati: {employer.get_status_display()}."
            if employer.status_comment:
                text += f" Izoh: {employer.status_comment}"
            notify(employer.user, "Tashkilot holati o'zgardi", text, "/ish-beruvchi/")
        messages.success(request, "Ish beruvchi ma'lumotlari yangilandi.")
        return redirect("employers:manage_detail", pk=employer.pk)
    apps = Application.objects.filter(vacancy__employer=employer)
    stats = {
        "vacancies": employer.vacancies.count(),
        "applications": apps.count(),
        "interviews": apps.filter(status=Application.Status.INTERVIEW).count(),
        "accepted": apps.filter(status=Application.Status.ACCEPTED).count(),
    }
    vacancies = employer.vacancies.annotate(app_count=Count("applications")).order_by("-created_at")[:20]
    history = apps.select_related("applicant", "vacancy").order_by("-created_at")[:15]
    return render(request, "employers/manage_detail.html", {
        "employer": employer, "form": form, "stats": stats, "vacancies": vacancies, "history": history,
    })
