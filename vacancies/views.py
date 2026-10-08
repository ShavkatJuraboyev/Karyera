from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import Direction, Region, Role
from accounts.permissions import CANDIDATE_ROLES, STAFF_ROLES, role_required
from core.models import AuditLog
from core.services import audit
from employers.views import get_employer
from students.services import can_view_profile, get_profile
from vacancies.forms import ApplicationStatusForm, ApplyForm, ModerationForm, VacancyForm
from vacancies.models import Application, Vacancy
from vacancies.services import (BusinessError, apply_to_vacancy, moderate_vacancy, set_application_status,
                                submit_for_moderation, withdraw_application)


# ------------------------------------------------------------------ Ommaviy: qidirish va filtrlash
def vacancy_list(request):
    qs = Vacancy.objects.published().select_related("employer").prefetch_related("directions")
    g = request.GET
    q = g.get("q", "").strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(employer__name__icontains=q) | Q(requirements__icontains=q) | Q(duties__icontains=q))
    if g.get("direction", "").isdigit():
        d = int(g["direction"])
        # yo'nalish ko'rsatilmagan vakansiyalar barcha yo'nalishlar uchun mos
        qs = qs.filter(Q(directions__pk=d) | Q(directions__isnull=True)).distinct()
    if g.get("region") in Region.values:
        qs = qs.filter(region=g["region"])
    if g.get("type") in Vacancy.EmploymentType.values:
        qs = qs.filter(employment_type=g["type"])
    if g.get("employer", "").isdigit():
        qs = qs.filter(employer_id=int(g["employer"]))
    if g.get("salary", "").isdigit() and int(g["salary"]) > 0:
        s = int(g["salary"])
        qs = qs.filter(Q(salary_max__gte=s) | Q(salary_max__isnull=True, salary_min__gte=s))
    sort = g.get("sort", "new")
    if sort == "salary":
        qs = qs.order_by(F("salary_max").desc(nulls_last=True), "-published_at")
    elif sort == "deadline":
        qs = qs.order_by("deadline", "-published_at")
    else:
        qs = qs.order_by("-published_at", "-id")
    page = Paginator(qs, 10).get_page(g.get("page"))
    params = g.copy()
    params.pop("page", None)
    applied_ids = set()
    if request.user.is_authenticated and request.user.is_candidate:
        applied_ids = set(Application.objects.filter(applicant=request.user).exclude(status=Application.Status.WITHDRAWN)
                          .values_list("vacancy_id", flat=True))
    return render(request, "vacancies/list.html", {
        "page": page, "g": g, "querystring": params.urlencode(), "applied_ids": applied_ids,
        "directions": Direction.objects.filter(is_active=True).select_related("faculty"),
        "regions": Region.choices, "types": Vacancy.EmploymentType.choices,
    })


def vacancy_detail(request, pk):
    vacancy = get_object_or_404(Vacancy.objects.select_related("employer").prefetch_related("directions"), pk=pk)
    user = request.user
    is_owner = user.is_authenticated and vacancy.employer.user_id == user.pk
    is_staff = user.is_authenticated and user.role in STAFF_ROLES
    if not (vacancy.is_open or is_owner or is_staff):
        # yopilgan/muddati o'tgan e'lon ham ko'rinadi, faqat qoralama va moderatsiyadagilar yashirin
        if vacancy.status not in (Vacancy.Status.PUBLISHED, Vacancy.Status.CLOSED) or vacancy.employer.status != vacancy.employer.Status.APPROVED:
            raise Http404
    viewed = request.session.setdefault("viewed_vacancies", [])
    if vacancy.is_open and not is_owner and pk not in viewed:
        Vacancy.objects.filter(pk=pk).update(views_count=F("views_count") + 1)
        viewed.append(pk)
        request.session["viewed_vacancies"] = viewed[-100:]
    application = None
    if user.is_authenticated and user.is_candidate:
        application = Application.objects.filter(vacancy=vacancy, applicant=user).first()
    return render(request, "vacancies/detail.html", {
        "vacancy": vacancy, "application": application, "form": ApplyForm(),
        "is_owner": is_owner, "is_staff": is_staff,
        "can_apply": user.is_authenticated and user.is_candidate and vacancy.is_open and (application is None or application.status == Application.Status.WITHDRAWN),
    })


# ------------------------------------------------------------------ Talaba/bitiruvchi: ariza
@role_required(*CANDIDATE_ROLES)
@require_POST
def apply(request, pk):
    vacancy = get_object_or_404(Vacancy.objects.select_related("employer"), pk=pk)
    form = ApplyForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Qo'shimcha xat juda uzun (2000 belgigacha).")
        return redirect(vacancy)
    get_profile(request.user)
    try:
        apply_to_vacancy(request.user, vacancy, form.cleaned_data["cover_letter"], request=request)
    except BusinessError as e:
        messages.error(request, str(e))
    else:
        messages.success(request, "Arizangiz yuborildi. Holatini «Arizalarim» bo'limida kuzatib borishingiz mumkin.")
    return redirect(vacancy)


@role_required(*CANDIDATE_ROLES)
def my_applications(request):
    qs = Application.objects.filter(applicant=request.user).select_related("vacancy", "vacancy__employer")
    status = request.GET.get("status", "")
    if status in Application.Status.values:
        qs = qs.filter(status=status)
    page = Paginator(qs, 15).get_page(request.GET.get("page"))
    return render(request, "vacancies/my_applications.html", {"page": page, "status": status, "statuses": Application.Status.choices})


@role_required(*CANDIDATE_ROLES)
@require_POST
def withdraw(request, pk):
    application = get_object_or_404(Application, pk=pk, applicant=request.user)
    try:
        withdraw_application(application, request.user, request=request)
        messages.success(request, "Ariza bekor qilindi.")
    except BusinessError as e:
        messages.error(request, str(e))
    return redirect("vacancies:my_applications")


# ------------------------------------------------------------------ Ish beruvchi: vakansiyalar
@role_required(Role.EMPLOYER)
def employer_vacancies(request):
    employer = get_employer(request.user)
    qs = employer.vacancies.annotate(app_count=Count("applications"))
    status = request.GET.get("status", "")
    if status in Vacancy.Status.values:
        qs = qs.filter(status=status)
    page = Paginator(qs.order_by("-created_at"), 15).get_page(request.GET.get("page"))
    return render(request, "vacancies/employer_list.html", {
        "page": page, "employer": employer, "status": status, "statuses": Vacancy.Status.choices,
    })


@role_required(Role.EMPLOYER)
def employer_vacancy_form(request, pk=None):
    employer = get_employer(request.user)
    vacancy = get_object_or_404(Vacancy, pk=pk, employer=employer) if pk else None
    if not employer.is_approved:
        messages.warning(request, "Tashkilotingiz hali tasdiqlanmagan. Tasdiqlangandan so'ng vakansiya joylashtira olasiz.")
        return redirect("employers:dashboard")
    can_draft = vacancy is None or vacancy.status in (Vacancy.Status.DRAFT, Vacancy.Status.REJECTED)
    form = VacancyForm(request.POST or None, instance=vacancy)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.employer = employer
        is_new = obj.pk is None
        submit = request.POST.get("action") == "submit" or not can_draft
        if is_new:
            obj.status = Vacancy.Status.DRAFT
        obj.save()
        form.save_m2m()
        audit(AuditLog.Action.VACANCY_CREATE if is_new else AuditLog.Action.VACANCY_UPDATE, request=request, obj=obj,
              details="Vakansiya yaratildi" if is_new else "Vakansiya o'zgartirildi")
        if submit:
            try:
                submit_for_moderation(obj, request=request)
                messages.success(request, "Vakansiya moderatsiyaga yuborildi. Tasdiqlangach e'lon qilinadi.")
            except BusinessError as e:
                messages.error(request, str(e))
        else:
            messages.success(request, "Vakansiya qoralama sifatida saqlandi.")
        return redirect("vacancies:employer_list")
    return render(request, "vacancies/employer_form.html", {"form": form, "vacancy": vacancy, "can_draft": can_draft})


@role_required(Role.EMPLOYER)
@require_POST
def employer_vacancy_close(request, pk):
    vacancy = get_object_or_404(Vacancy, pk=pk, employer=get_employer(request.user))
    if vacancy.status not in (Vacancy.Status.PUBLISHED, Vacancy.Status.PENDING):
        messages.error(request, "Bu vakansiyani yopib bo'lmaydi.")
    else:
        vacancy.status = Vacancy.Status.CLOSED
        vacancy.save(update_fields=["status", "updated_at"])
        audit(AuditLog.Action.VACANCY_STATUS, request=request, obj=vacancy, details="Ish beruvchi vakansiyani yopdi")
        messages.success(request, "Vakansiya yopildi.")
    return redirect("vacancies:employer_list")


@role_required(Role.EMPLOYER)
@require_POST
def employer_vacancy_delete(request, pk):
    vacancy = get_object_or_404(Vacancy, pk=pk, employer=get_employer(request.user))
    if vacancy.status not in (Vacancy.Status.DRAFT, Vacancy.Status.REJECTED) or vacancy.applications.exists():
        messages.error(request, "Faqat arizasi yo'q qoralama yoki rad etilgan vakansiyani o'chirish mumkin. Qolganlarini yoping.")
    else:
        audit(AuditLog.Action.VACANCY_DELETE, request=request, obj=vacancy, details="Vakansiya o'chirildi")
        vacancy.delete()
        messages.success(request, "Vakansiya o'chirildi.")
    return redirect("vacancies:employer_list")


@role_required(Role.EMPLOYER)
def employer_vacancy_applications(request, pk):
    vacancy = get_object_or_404(Vacancy, pk=pk, employer=get_employer(request.user))
    qs = vacancy.applications.select_related("applicant", "applicant__profile", "applicant__profile__direction")
    status = request.GET.get("status", "")
    if status in Application.Status.values:
        qs = qs.filter(status=status)
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "vacancies/employer_applications.html", {
        "vacancy": vacancy, "page": page, "status": status, "statuses": Application.Status.choices,
    })


@role_required(Role.EMPLOYER)
def employer_applications_all(request):
    employer = get_employer(request.user)
    qs = Application.objects.filter(vacancy__employer=employer).select_related("applicant", "vacancy")
    status = request.GET.get("status", "")
    if status in Application.Status.values:
        qs = qs.filter(status=status)
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "vacancies/employer_all_applications.html", {"page": page, "status": status, "statuses": Application.Status.choices})


@role_required(Role.EMPLOYER)
def employer_application_detail(request, pk):
    application = get_object_or_404(
        Application.objects.select_related("vacancy", "applicant", "applicant__profile", "applicant__profile__faculty", "applicant__profile__direction"),
        pk=pk, vacancy__employer=get_employer(request.user))
    initial = {"status": application.status if application.status in dict(ApplicationStatusForm.STATUS_CHOICES) else Application.Status.REVIEWING,
               "interview_place": application.interview_place, "employer_comment": application.employer_comment,
               "interview_at": timezone.localtime(application.interview_at).replace(tzinfo=None) if application.interview_at else None}
    form = ApplicationStatusForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            set_application_status(application, form.cleaned_data["status"], request.user,
                                   interview_at=form.cleaned_data.get("interview_at"), interview_place=form.cleaned_data.get("interview_place", ""),
                                   comment=form.cleaned_data.get("employer_comment", ""), request=request)
            messages.success(request, "Ariza holati yangilandi va nomzodga xabar yuborildi.")
            return redirect("vacancies:employer_application", pk=application.pk)
        except BusinessError as e:
            messages.error(request, str(e))
    profile = getattr(application.applicant, "profile", None)
    return render(request, "vacancies/employer_application_detail.html", {
        "application": application, "profile": profile, "form": form,
        "can_update": application.status != Application.Status.WITHDRAWN,
        "can_see_cv": bool(profile) and can_view_profile(request.user, profile),
    })


# ------------------------------------------------------------------ Karyera markazi: moderatsiya
@role_required(*STAFF_ROLES)
def manage_list(request):
    qs = Vacancy.objects.select_related("employer").annotate(app_count=Count("applications"))
    status = request.GET.get("status", "pending")
    q = request.GET.get("q", "").strip()
    if status in Vacancy.Status.values:
        qs = qs.filter(status=status)
    else:
        status = ""
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(employer__name__icontains=q))
    page = Paginator(qs.order_by("-updated_at"), 20).get_page(request.GET.get("page"))
    return render(request, "vacancies/manage_list.html", {"page": page, "status": status, "q": q, "statuses": Vacancy.Status.choices})


@role_required(*STAFF_ROLES)
def manage_detail(request, pk):
    vacancy = get_object_or_404(Vacancy.objects.select_related("employer").prefetch_related("directions"), pk=pk)
    form = ModerationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            moderate_vacancy(vacancy, form.cleaned_data["decision"], form.cleaned_data["comment"], request.user, request=request)
            messages.success(request, "Qaror saqlandi va ish beruvchiga xabar yuborildi.")
            return redirect("vacancies:manage_list")
        except BusinessError as e:
            messages.error(request, str(e))
    return render(request, "vacancies/manage_detail.html", {"vacancy": vacancy, "form": form, "app_count": vacancy.applications.count()})
