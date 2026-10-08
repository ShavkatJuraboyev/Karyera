"""Statistika va tahlil hisob-kitoblari (dashboard va hisobotlar uchun)."""
from datetime import date, datetime

from django.db.models import Count, Q
from django.db.models.functions import TruncMonth, TruncQuarter, TruncYear
from django.utils import timezone

from accounts.models import Role
from employers.models import Employer
from events.models import Event, EventRegistration
from students.models import EmploymentStatus, StudentProfile
from students.services import scope_profiles
from vacancies.models import Application, Vacancy

HIRED = [EmploymentStatus.EMPLOYED, EmploymentStatus.SELF_EMPLOYED]
UZ_MONTHS = ["Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek"]


def graduates_qs(user):
    return scope_profiles(user, StudentProfile.objects.filter(user__role=Role.GRADUATE))


def students_qs(user):
    return scope_profiles(user, StudentProfile.objects.filter(user__role=Role.STUDENT))


def applications_qs(user):
    qs = Application.objects.all()
    if user.role == Role.DEAN:
        return qs.filter(applicant__profile__faculty_id=user.faculty_id) if user.faculty_id else qs.none()
    return qs


def to_date(value):
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.date()
    return value


def rate(part, total):
    return round(100 * part / total, 1) if total else 0


def month_starts(n=12):
    today = timezone.localdate()
    y, m = today.year, today.month
    result = []
    for _ in range(n):
        result.append(date(y, m, 1))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(result))


def dashboard_data(user):
    grads = graduates_qs(user)
    students = students_qs(user)
    apps = applications_qs(user)
    now = timezone.now()
    grads_total = grads.count()
    hired = grads.filter(employment_status__in=HIRED).count()
    looking = grads.filter(employment_status=EmploymentStatus.LOOKING).count()

    data = {
        "students_total": students.count(),
        "graduates_total": grads_total,
        "looking": looking,
        "hired": hired,
        "employment_rate": rate(hired, grads_total),
        "vacancies_active": Vacancy.objects.published().count(),
        "vacancies_pending": Vacancy.objects.filter(status=Vacancy.Status.PENDING).count(),
        "employers_total": Employer.objects.filter(status=Employer.Status.APPROVED).count(),
        "employers_pending": Employer.objects.filter(status=Employer.Status.PENDING).count(),
        "applications_total": apps.count(),
        "applications_new": apps.filter(status=Application.Status.SENT).count(),
        "interviews": apps.filter(status=Application.Status.INTERVIEW).count(),
        "accepted": apps.filter(status=Application.Status.ACCEPTED).count(),
        "events_upcoming": Event.objects.filter(is_published=True, start_at__gte=now).count(),
        "events_total": Event.objects.filter(is_published=True).count(),
        "registrations_total": EventRegistration.objects.count(),
        "attended_total": EventRegistration.objects.filter(attended=True).count(),
    }

    # Bitiruvchilar holati bo'yicha doira diagramma
    counts = dict(grads.values_list("employment_status").annotate(c=Count("id")))
    status_chart = {"labels": [label for _, label in EmploymentStatus.choices],
                    "data": [counts.get(value, 0) for value, _ in EmploymentStatus.choices]}

    # Fakultetlar kesimida bandlik ko'rsatkichi
    rows = (grads.values("faculty__name").annotate(total=Count("id"), hired=Count("id", filter=Q(employment_status__in=HIRED)))
            .order_by("faculty__name"))
    faculty_chart = {"labels": [r["faculty__name"] or "Ko'rsatilmagan" for r in rows],
                     "data": [rate(r["hired"], r["total"]) for r in rows]}

    # Oxirgi 12 oy dinamikasi
    months = month_starts(12)
    start = months[0]
    employed_by = {to_date(r["m"]): r["c"] for r in grads.filter(employment_status__in=HIRED, employed_date__gte=start)
                   .annotate(m=TruncMonth("employed_date")).values("m").annotate(c=Count("id"))}
    apps_by = {to_date(r["m"]): r["c"] for r in apps.filter(created_at__date__gte=start)
               .annotate(m=TruncMonth("created_at")).values("m").annotate(c=Count("id"))}
    monthly = {
        "labels": [f"{UZ_MONTHS[d.month - 1]} {d.year}" for d in months],
        "employed": [employed_by.get(d, 0) for d in months],
        "applications": [apps_by.get(d, 0) for d in months],
    }
    if user.role != Role.DEAN:
        vac_by = {to_date(r["m"]): r["c"] for r in Vacancy.objects.filter(published_at__date__gte=start)
                  .annotate(m=TruncMonth("published_at")).values("m").annotate(c=Count("id"))}
        monthly["vacancies"] = [vac_by.get(d, 0) for d in months]

    # Ariza holatlari
    app_counts = dict(apps.values_list("status").annotate(c=Count("id")))
    app_chart = {"labels": [label for _, label in Application.Status.choices],
                 "data": [app_counts.get(value, 0) for value, _ in Application.Status.choices]}
    data.update(status_chart=status_chart, faculty_chart=faculty_chart, monthly=monthly, app_chart=app_chart)
    return data


def period_label(d, period):
    if period == "year":
        return str(d.year)
    if period == "quarter":
        return f"{d.year}-chorak {(d.month - 1) // 3 + 1}"
    return f"{d.year}-{d.month:02d}"
