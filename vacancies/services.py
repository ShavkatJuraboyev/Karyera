"""Vakansiya va arizalar bo'yicha biznes qoidalari (veb va API tomonidan umumiy foydalaniladi)."""
from django.db import transaction
from django.utils import timezone

from accounts.models import Role, User
from core.models import AuditLog
from core.services import audit, notify, notify_many
from employers.models import Employer
from vacancies.models import Application, Vacancy


class BusinessError(Exception):
    """Foydalanuvchiga ko'rsatiladigan biznes-qoida xatosi."""


EMPLOYER_STATUSES = (Application.Status.REVIEWING, Application.Status.INTERVIEW,
                     Application.Status.ACCEPTED, Application.Status.REJECTED)


@transaction.atomic
def apply_to_vacancy(user, vacancy, cover_letter="", request=None):
    if not user.is_candidate:
        raise BusinessError("Faqat talaba va bitiruvchilar ariza topshirishi mumkin.")
    if not vacancy.is_open:
        raise BusinessError("Bu vakansiya hozir arizalar qabul qilmaydi.")
    application, created = Application.objects.get_or_create(
        vacancy=vacancy, applicant=user, defaults={"cover_letter": cover_letter},
    )
    if not created:
        if application.status != Application.Status.WITHDRAWN:
            raise BusinessError("Siz bu vakansiyaga allaqachon ariza topshirgansiz.")
        application.status = Application.Status.SENT
        application.cover_letter = cover_letter
        application.interview_at = None
        application.interview_place = ""
        application.employer_comment = ""
        application.save()
    audit(AuditLog.Action.APPLICATION, request=request, user=user, obj=application, details="Ariza topshirildi")
    notify(vacancy.employer.user, "Yangi ariza", f"{user.full_name} «{vacancy.title}» vakansiyasiga ariza topshirdi.",
           f"/ish-beruvchi/arizalar/{application.pk}/")
    return application


def withdraw_application(application, user, request=None):
    if application.applicant_id != user.pk:
        raise BusinessError("Bu ariza sizga tegishli emas.")
    if not application.can_withdraw:
        raise BusinessError("Bu arizani bekor qilib bo'lmaydi.")
    application.status = Application.Status.WITHDRAWN
    application.save(update_fields=["status", "updated_at"])
    audit(AuditLog.Action.APPLICATION, request=request, user=user, obj=application, details="Ariza bekor qilindi")
    return application


def set_application_status(application, status, by, interview_at=None, interview_place="", comment="", request=None):
    if application.vacancy.employer.user_id != by.pk:
        raise BusinessError("Bu ariza sizning vakansiyangizga tegishli emas.")
    if status not in EMPLOYER_STATUSES:
        raise BusinessError("Noto'g'ri holat tanlandi.")
    if application.status == Application.Status.WITHDRAWN:
        raise BusinessError("Nomzod arizani bekor qilgan, holatni o'zgartirib bo'lmaydi.")
    old = application.status
    application.status = status
    application.employer_comment = comment
    if status == Application.Status.INTERVIEW:
        application.interview_at = interview_at
        application.interview_place = interview_place
    application.save()
    audit(AuditLog.Action.APPLICATION, request=request, user=by, obj=application, details=f"Holat: {old} → {status}")
    text = f"«{application.vacancy.title}» ({application.vacancy.employer.name}) bo'yicha arizangiz holati: {application.get_status_display()}."
    if status == Application.Status.INTERVIEW and interview_at:
        from django.utils import timezone as tz
        text += f" Suhbat: {tz.localtime(interview_at):%d.%m.%Y %H:%M}" + (f", {interview_place}" if interview_place else "") + "."
    if comment:
        text += f" Izoh: {comment}"
    notify(application.applicant, "Ariza holati o'zgardi", text, "/kabinet/arizalar/")
    return application


def submit_for_moderation(vacancy, request=None):
    if not vacancy.employer.is_approved:
        raise BusinessError("Tashkilotingiz hali tasdiqlanmagan. Vakansiyani moderatsiyaga yuborish uchun tasdiqlanishini kuting.")
    vacancy.status = Vacancy.Status.PENDING
    vacancy.moderation_comment = ""
    vacancy.save(update_fields=["status", "moderation_comment", "updated_at"])
    staff = User.objects.filter(role__in=[Role.STAFF, Role.ADMIN], is_active=True)
    notify_many(staff, "Vakansiya moderatsiyaga yuborildi", f"{vacancy.employer.name}: «{vacancy.title}»",
                f"/boshqaruv/vakansiyalar/{vacancy.pk}/", external=False)
    audit(AuditLog.Action.VACANCY_STATUS, request=request, obj=vacancy, details="Moderatsiyaga yuborildi")


def _notify_matching_candidates(vacancy):
    from students.models import EmploymentStatus, StudentProfile
    profiles = StudentProfile.objects.filter(user__is_active=True, user__role__in=[Role.STUDENT, Role.GRADUATE]) \
        .exclude(employment_status__in=[EmploymentStatus.EMPLOYED, EmploymentStatus.NOT_LOOKING])
    direction_ids = list(vacancy.directions.values_list("pk", flat=True))
    if direction_ids:
        profiles = profiles.filter(direction_id__in=direction_ids)
    users = [p.user for p in profiles.select_related("user")[:500]]
    notify_many(users, "Yangi vakansiya", f"{vacancy.employer.name}: «{vacancy.title}»", vacancy.get_absolute_url(), external=False)


def moderate_vacancy(vacancy, decision, comment, by, request=None):
    status = vacancy.status
    if decision == "publish":
        if status not in (Vacancy.Status.PENDING, Vacancy.Status.REJECTED, Vacancy.Status.CLOSED):
            raise BusinessError("Bu holatdagi vakansiyani e'lon qilib bo'lmaydi.")
        if not vacancy.employer.is_approved:
            raise BusinessError("Avval ish beruvchi tashkilotni tasdiqlang.")
        if vacancy.is_expired:
            raise BusinessError("Murojaat muddati o'tgan. Ish beruvchi muddatni yangilashi kerak.")
        vacancy.status = Vacancy.Status.PUBLISHED
        vacancy.published_at = timezone.now()
        vacancy.moderation_comment = comment
        title = "Vakansiyangiz e'lon qilindi"
    elif decision == "reject":
        if status not in (Vacancy.Status.PENDING, Vacancy.Status.PUBLISHED):
            raise BusinessError("Bu holatdagi vakansiyani rad etib bo'lmaydi.")
        vacancy.status = Vacancy.Status.REJECTED
        vacancy.moderation_comment = comment
        title = "Vakansiyangiz rad etildi"
    elif decision == "close":
        if status not in (Vacancy.Status.PENDING, Vacancy.Status.PUBLISHED):
            raise BusinessError("Bu holatdagi vakansiyani yopib bo'lmaydi.")
        vacancy.status = Vacancy.Status.CLOSED
        vacancy.moderation_comment = comment
        title = "Vakansiyangiz yopildi"
    else:
        raise BusinessError("Noto'g'ri qaror.")
    vacancy.save()
    audit(AuditLog.Action.VACANCY_STATUS, request=request, user=by, obj=vacancy, details=f"Moderatsiya: {decision}. {comment}")
    notify(vacancy.employer.user, title, f"«{vacancy.title}»" + (f" — {comment}" if comment else ""), "/ish-beruvchi/vakansiyalar/")
    if decision == "publish":
        _notify_matching_candidates(vacancy)
    return vacancy
