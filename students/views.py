from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Direction, Faculty, Role
from accounts.permissions import ANALYTICS_ROLES, CANDIDATE_ROLES, STAFF_ROLES, role_required
from core.exporters import pdf_response, xlsx_response
from core.models import AuditLog
from core.services import audit
from students.forms import MonitoringForm, SECTIONS, StudentProfileForm
from students.models import EmploymentStatus, StudentProfile
from students.pdf import build_cv_pdf
from students.services import can_view_profile, get_profile, scope_profiles


# ------------------------------------------------------------------ Talaba/bitiruvchi kabineti
@role_required(*CANDIDATE_ROLES)
def profile(request):
    profile = get_profile(request.user)
    return render(request, "students/profile.html", {
        "profile": profile,
        "sections": [
            ("skills", "Ko'nikmalar", profile.skills.all()),
            ("languages", "Tillar", profile.languages.all()),
            ("experiences", "Ish tajribasi", profile.experiences.all()),
            ("certificates", "Sertifikatlar", profile.certificates.all()),
            ("portfolio", "Portfolio", profile.portfolio.all()),
        ],
    })


@role_required(*CANDIDATE_ROLES)
def profile_edit(request):
    profile = get_profile(request.user)
    form = StudentProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        audit(AuditLog.Action.DATA_CHANGE, request=request, obj=profile, details="Profil yangilandi")
        messages.success(request, "Profil ma'lumotlari saqlandi.")
        return redirect("students:profile")
    return render(request, "students/profile_form.html", {"form": form, "profile": profile})


def _section_or_404(key):
    if key not in SECTIONS:
        from django.http import Http404
        raise Http404
    return SECTIONS[key]


@role_required(*CANDIDATE_ROLES)
def section_form(request, section, pk=None):
    cfg = _section_or_404(section)
    profile = get_profile(request.user)
    instance = get_object_or_404(cfg["model"], pk=pk, profile=profile) if pk else None
    form = cfg["form"](request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.profile = profile
        obj.save()
        audit(AuditLog.Action.DATA_CHANGE, request=request, obj=obj, details=f"{cfg['title']} {'yangilandi' if pk else 'qo`shildi'}")
        messages.success(request, f"{cfg['title']} saqlandi.")
        return redirect("students:profile")
    return render(request, "students/section_form.html", {
        "form": form, "cfg": cfg, "section": section, "editing": bool(pk),
    })


@role_required(*CANDIDATE_ROLES)
@require_POST
def section_delete(request, section, pk):
    cfg = _section_or_404(section)
    profile = get_profile(request.user)
    obj = get_object_or_404(cfg["model"], pk=pk, profile=profile)
    audit(AuditLog.Action.DATA_DELETE, request=request, obj=obj, details=f"{cfg['title']} o'chirildi")
    obj.delete()
    messages.success(request, f"{cfg['title']} o'chirildi.")
    return redirect("students:profile")


@role_required(*CANDIDATE_ROLES)
def cv_view(request):
    profile = get_profile(request.user)
    return render(request, "students/cv.html", {"profile": profile, "owner": True})


def _cv_pdf_response(profile):
    response = HttpResponse(build_cv_pdf(profile), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="CV_{profile.user.username}.pdf"'
    return response


@role_required(*CANDIDATE_ROLES)
def cv_pdf(request):
    return _cv_pdf_response(get_profile(request.user))


@login_required
def cv_view_other(request, pk):
    profile = get_object_or_404(StudentProfile.objects.select_related("user", "faculty", "direction"), pk=pk)
    if not can_view_profile(request.user, profile):
        raise PermissionDenied
    return render(request, "students/cv.html", {"profile": profile, "owner": False})


@login_required
def cv_pdf_other(request, pk):
    profile = get_object_or_404(StudentProfile.objects.select_related("user", "faculty", "direction"), pk=pk)
    if not can_view_profile(request.user, profile):
        raise PermissionDenied
    return _cv_pdf_response(profile)


# ------------------------------------------------------------------ Monitoring (markaz, dekanat, rahbariyat)
def _filtered_profiles(request):
    qs = scope_profiles(request.user, StudentProfile.objects.select_related("user", "faculty", "direction"))
    g = request.GET
    q = g.get("q", "").strip()
    if q:
        qs = qs.filter(Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) | Q(user__username__icontains=q)
                       | Q(user__phone__icontains=q) | Q(employer_name__icontains=q))
    if g.get("faculty", "").isdigit():
        qs = qs.filter(faculty_id=int(g["faculty"]))
    if g.get("direction", "").isdigit():
        qs = qs.filter(direction_id=int(g["direction"]))
    if g.get("course", "").isdigit():
        qs = qs.filter(course=int(g["course"]))
    if g.get("year", "").isdigit():
        qs = qs.filter(graduation_year=int(g["year"]))
    if g.get("status") in EmploymentStatus.values:
        qs = qs.filter(employment_status=g["status"])
    if g.get("role") in (Role.STUDENT, Role.GRADUATE):
        qs = qs.filter(user__role=g["role"])
    return qs.order_by("user__last_name", "user__first_name", "pk")


@role_required(*ANALYTICS_ROLES)
def monitor_list(request):
    qs = _filtered_profiles(request)
    export = request.GET.get("export")
    if export in ("xlsx", "pdf"):
        headers = ["F.I.Sh.", "Rol", "Fakultet", "Yo'nalish", "Kurs", "Bitiruv yili", "Telefon", "Bandlik holati", "Tashkilot", "Lavozim", "Ishga joylashgan sana"]
        rows = [[p.user.full_name, p.user.get_role_display(), p.faculty.name if p.faculty else "", p.direction.name if p.direction else "",
                 p.course or "", p.graduation_year or "", p.user.phone, p.get_employment_status_display(), p.employer_name, p.position,
                 f"{p.employed_date:%d.%m.%Y}" if p.employed_date else ""] for p in qs]
        audit(AuditLog.Action.EXPORT, request=request, details=f"Talaba/bitiruvchilar ro'yxati ({export}), {len(rows)} ta yozuv")
        fn = xlsx_response if export == "xlsx" else pdf_response
        return fn("Talaba va bitiruvchilar ro'yxati", headers, rows, filename_prefix="talabalar")
    faculties = Faculty.objects.filter(is_active=True)
    if request.user.role == Role.DEAN:
        faculties = faculties.filter(pk=request.user.faculty_id)
    directions = Direction.objects.filter(is_active=True)
    if request.user.role == Role.DEAN:
        directions = directions.filter(faculty_id=request.user.faculty_id)
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    params.pop("export", None)
    return render(request, "students/monitor_list.html", {
        "page": page, "faculties": faculties, "directions": directions, "statuses": EmploymentStatus.choices,
        "g": request.GET, "querystring": params.urlencode(), "total": qs.count(),
        "can_edit": request.user.role in STAFF_ROLES,
    })


@role_required(*ANALYTICS_ROLES)
def monitor_detail(request, pk):
    profile = get_object_or_404(scope_profiles(request.user, StudentProfile.objects.select_related("user", "faculty", "direction")), pk=pk)
    applications = profile.user.applications.select_related("vacancy", "vacancy__employer")[:20]
    registrations = profile.user.event_registrations.select_related("event")[:20]
    return render(request, "students/monitor_detail.html", {
        "profile": profile, "applications": applications, "registrations": registrations,
        "can_edit": request.user.role in STAFF_ROLES,
    })


@role_required(*STAFF_ROLES)
def monitor_edit(request, pk):
    profile = get_object_or_404(StudentProfile.objects.select_related("user"), pk=pk)
    form = MonitoringForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        audit(AuditLog.Action.DATA_CHANGE, request=request, obj=profile, details="Bandlik monitoringi ma'lumotlari yangilandi")
        messages.success(request, "Ma'lumotlar saqlandi.")
        return redirect("students:monitor_detail", pk=profile.pk)
    return render(request, "students/monitor_form.html", {"form": form, "profile": profile})


@login_required
def protected_file(request, kind, pk):
    """Shaxsiy fayllarni (rasm, sertifikat, portfolio) faqat vakolatli foydalanuvchilarga beradi."""
    from students.models import Certificate, PortfolioItem
    if kind == "photo":
        profile = get_object_or_404(StudentProfile.objects.select_related("user"), pk=pk)
        field = profile.photo
    elif kind == "certificate":
        obj = get_object_or_404(Certificate.objects.select_related("profile__user"), pk=pk)
        profile, field = obj.profile, obj.file
    elif kind == "portfolio":
        obj = get_object_or_404(PortfolioItem.objects.select_related("profile__user"), pk=pk)
        profile, field = obj.profile, obj.file
    else:
        raise Http404
    if not can_view_profile(request.user, profile):
        raise PermissionDenied
    if not field:
        raise Http404
    try:
        handle = field.open("rb")
    except FileNotFoundError:
        raise Http404
    return FileResponse(handle, as_attachment=False, filename=field.name.rsplit("/", 1)[-1])
