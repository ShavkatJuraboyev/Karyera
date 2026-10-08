"""Hisobotlar ro'yxati. Har bir hisobot (sarlavhalar, qatorlar) qaytaradi."""
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth, TruncQuarter, TruncYear
from django.utils import timezone

from accounts.models import Role
from employers.models import Employer
from events.models import Event, EventRegistration
from reports.analytics import (HIRED, applications_qs, graduates_qs, period_label, rate, to_date)
from students.models import EmploymentStatus
from vacancies.models import Application, Vacancy

STAFF_VIEW = (Role.STAFF, Role.ADMIN, Role.MANAGEMENT)
ALL_VIEW = (Role.STAFF, Role.ADMIN, Role.MANAGEMENT, Role.DEAN)


def _grads(user, p):
    qs = graduates_qs(user)
    if p.get("faculty"):
        qs = qs.filter(faculty=p["faculty"])
    if p.get("year"):
        qs = qs.filter(graduation_year=p["year"])
    return qs


def employment_status(user, p):
    qs = _grads(user, p)
    counts = dict(qs.values_list("employment_status").annotate(c=Count("id")))
    total = sum(counts.values())
    rows = [[label, counts.get(v, 0), f"{rate(counts.get(v, 0), total)}%"] for v, label in EmploymentStatus.choices]
    rows.append(["JAMI", total, "100%" if total else "0%"])
    return ["Bandlik holati", "Bitiruvchilar soni", "Ulushi"], rows


def by_faculty(user, p):
    qs = _grads(user, p)
    data = qs.values("faculty__name").annotate(
        total=Count("id"),
        employed=Count("id", filter=Q(employment_status=EmploymentStatus.EMPLOYED)),
        selfemp=Count("id", filter=Q(employment_status=EmploymentStatus.SELF_EMPLOYED)),
        looking=Count("id", filter=Q(employment_status=EmploymentStatus.LOOKING)),
        studying=Count("id", filter=Q(employment_status=EmploymentStatus.STUDYING)),
    ).order_by("faculty__name")
    rows, t = [], [0, 0, 0, 0, 0]
    for r in data:
        vals = [r["total"], r["employed"], r["selfemp"], r["looking"], r["studying"]]
        t = [a + b for a, b in zip(t, vals)]
        rows.append([r["faculty__name"] or "Ko'rsatilmagan"] + vals + [f"{rate(r['employed'] + r['selfemp'], r['total'])}%"])
    rows.append(["JAMI"] + t + [f"{rate(t[1] + t[2], t[0])}%"])
    return ["Fakultet", "Bitiruvchilar", "Ishga joylashgan", "O'zini o'zi band qilgan", "Ish izlayapti", "O'qishni davom ettirmoqda", "Bandlik ko'rsatkichi"], rows


def by_direction(user, p):
    qs = _grads(user, p)
    data = qs.values("faculty__name", "direction__name").annotate(
        total=Count("id"), hired=Count("id", filter=Q(employment_status__in=HIRED)),
        looking=Count("id", filter=Q(employment_status=EmploymentStatus.LOOKING)),
    ).order_by("faculty__name", "direction__name")
    rows = [[r["faculty__name"] or "—", r["direction__name"] or "Ko'rsatilmagan", r["total"], r["hired"], r["looking"],
             f"{rate(r['hired'], r['total'])}%"] for r in data]
    return ["Fakultet", "Ta'lim yo'nalishi", "Bitiruvchilar", "Ishga joylashgan", "Ish izlayapti", "Bandlik ko'rsatkichi"], rows


def by_year(user, p):
    qs = _grads(user, {"faculty": p.get("faculty")})
    data = qs.values("graduation_year").annotate(total=Count("id"), hired=Count("id", filter=Q(employment_status__in=HIRED)),
                                                 looking=Count("id", filter=Q(employment_status=EmploymentStatus.LOOKING))).order_by("-graduation_year")
    rows = [[r["graduation_year"] or "Ko'rsatilmagan", r["total"], r["hired"], r["looking"], f"{rate(r['hired'], r['total'])}%"] for r in data]
    return ["Bitiruv yili", "Bitiruvchilar", "Ishga joylashgan", "Ish izlayapti", "Bandlik ko'rsatkichi"], rows


def employers_vacancies(user, p):
    today = timezone.localdate()
    data = Employer.objects.annotate(
        vac=Count("vacancies", distinct=True),
        active=Count("vacancies", filter=Q(vacancies__status=Vacancy.Status.PUBLISHED, vacancies__deadline__gte=today), distinct=True),
        apps=Count("vacancies__applications", distinct=True),
        accepted=Count("vacancies__applications", filter=Q(vacancies__applications__status=Application.Status.ACCEPTED), distinct=True),
    ).order_by("name")
    rows = [[e.name, e.stir, e.region, e.get_status_display(), e.get_cooperation_display(), e.vac, e.active, e.apps, e.accepted] for e in data]
    return ["Tashkilot", "STIR", "Hudud", "Holati", "Hamkorlik", "Vakansiyalar", "Faol vakansiyalar", "Arizalar", "Qabul qilinganlar"], rows


def applications(user, p):
    cond = Q()
    if p.get("date_from"):
        cond &= Q(applications__created_at__date__gte=p["date_from"])
    if p.get("date_to"):
        cond &= Q(applications__created_at__date__lte=p["date_to"])
    if user.role == Role.DEAN:
        cond &= Q(applications__applicant__profile__faculty_id=user.faculty_id)
    S = Application.Status
    data = Vacancy.objects.select_related("employer").annotate(
        total=Count("applications", filter=cond),
        sent=Count("applications", filter=cond & Q(applications__status=S.SENT)),
        reviewing=Count("applications", filter=cond & Q(applications__status=S.REVIEWING)),
        interview=Count("applications", filter=cond & Q(applications__status=S.INTERVIEW)),
        accepted=Count("applications", filter=cond & Q(applications__status=S.ACCEPTED)),
        rejected=Count("applications", filter=cond & Q(applications__status=S.REJECTED)),
    ).filter(total__gt=0).order_by("-total", "title")
    rows = [[v.title, v.employer.name, v.total, v.sent, v.reviewing, v.interview, v.accepted, v.rejected] for v in data]
    if rows:
        sums = [sum(r[i] for r in rows) for i in range(2, 8)]
        rows.append(["JAMI", ""] + sums)
    return ["Vakansiya", "Tashkilot", "Jami arizalar", "Yuborildi", "Ko'rib chiqilmoqda", "Suhbatga taklif", "Qabul qilindi", "Rad etildi"], rows


def events_report(user, p):
    qs = Event.objects.filter(is_published=True)
    if p.get("date_from"):
        qs = qs.filter(start_at__date__gte=p["date_from"])
    if p.get("date_to"):
        qs = qs.filter(start_at__date__lte=p["date_to"])
    data = qs.annotate(reg=Count("registrations", distinct=True),
                       att=Count("registrations", filter=Q(registrations__attended=True), distinct=True)).order_by("-start_at")
    rows = [[e.title, e.get_event_type_display(), timezone.localtime(e.start_at).strftime("%d.%m.%Y %H:%M"), e.location, e.reg, e.att,
             f"{rate(e.att, e.reg)}%"] for e in data]
    return ["Tadbir", "Turi", "Sana", "Joyi", "Ro'yxatdan o'tganlar", "Qatnashganlar", "Qatnashuv ulushi"], rows


def dynamics(user, p):
    period = p.get("period") or "month"
    trunc = {"month": TruncMonth, "quarter": TruncQuarter, "year": TruncYear}.get(period, TruncMonth)
    df, dt = p.get("date_from"), p.get("date_to")
    buckets = {}

    def add(qs, idx, field, is_dt):
        if df:
            qs = qs.filter(**{f"{field}__date__gte" if is_dt else f"{field}__gte": df})
        if dt:
            qs = qs.filter(**{f"{field}__date__lte" if is_dt else f"{field}__lte": dt})
        qs = qs.filter(**{f"{field}__isnull": False})
        for r in qs.annotate(b=trunc(field)).values("b").annotate(c=Count("id")):
            key = to_date(r["b"])
            buckets.setdefault(key, [0, 0, 0, 0])[idx] += r["c"]

    add(graduates_qs(user).filter(employment_status__in=HIRED), 0, "employed_date", False)
    add(applications_qs(user), 1, "created_at", True)
    headers = ["Davr", "Ishga joylashgan bitiruvchilar", "Topshirilgan arizalar"]
    if user.role != Role.DEAN:
        add(Vacancy.objects.filter(status__in=[Vacancy.Status.PUBLISHED, Vacancy.Status.CLOSED]), 2, "published_at", True)
        add(EventRegistration.objects.all(), 3, "created_at", True)
        headers += ["E'lon qilingan vakansiyalar", "Tadbirlarga ro'yxatdan o'tganlar"]
    rows = []
    for key in sorted(buckets):
        vals = buckets[key] if user.role != Role.DEAN else buckets[key][:2]
        rows.append([period_label(key, period)] + vals)
    return headers, rows


REPORTS = {
    "employment-status": {"title": "Bitiruvchilarning ishga joylashish holati", "func": employment_status, "filters": ["faculty", "year"], "roles": ALL_VIEW,
                          "desc": "Bitiruvchilar bandlik holatlari bo'yicha taqsimoti."},
    "by-faculty": {"title": "Fakultetlar kesimida bandlik ko'rsatkichi", "func": by_faculty, "filters": ["faculty", "year"], "roles": ALL_VIEW,
                   "desc": "Har bir fakultet bitiruvchilarining bandlik darajasi."},
    "by-direction": {"title": "Ta'lim yo'nalishlari kesimida bandlik", "func": by_direction, "filters": ["faculty", "year"], "roles": ALL_VIEW,
                     "desc": "Yo'nalishlar bo'yicha ishga joylashish ko'rsatkichi."},
    "by-year": {"title": "Bitiruv yillari kesimida ishga joylashish", "func": by_year, "filters": ["faculty"], "roles": ALL_VIEW,
                "desc": "Turli yillardagi bitiruvchilar bandligi statistikasi."},
    "employers": {"title": "Ish beruvchilar va vakansiyalar", "func": employers_vacancies, "filters": [], "roles": STAFF_VIEW,
                  "desc": "Tashkilotlar, ularning vakansiyalari va natijalari."},
    "applications": {"title": "Vakansiyalarga topshirilgan arizalar", "func": applications, "filters": ["date_from", "date_to"], "roles": ALL_VIEW,
                     "desc": "Vakansiyalar bo'yicha arizalar va ularning holatlari."},
    "events": {"title": "Mehnat yarmarkalari va tadbirlar", "func": events_report, "filters": ["date_from", "date_to"], "roles": STAFF_VIEW,
               "desc": "Tadbirlar, ishtirokchilar va qatnashuv statistikasi."},
    "dynamics": {"title": "Bandlik dinamikasi (oy, chorak, yil)", "func": dynamics, "filters": ["period", "date_from", "date_to"], "roles": ALL_VIEW,
                 "desc": "Tanlangan davr kesimida ishga joylashish va faollik dinamikasi."},
}
