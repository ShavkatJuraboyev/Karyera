from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from accounts.models import Direction, Region
from employers.models import Employer


class VacancyQuerySet(models.QuerySet):
    def published(self):
        """Hozir ommaga ko'rinadigan vakansiyalar."""
        return self.filter(
            status=Vacancy.Status.PUBLISHED,
            deadline__gte=timezone.localdate(),
            employer__status=Employer.Status.APPROVED,
        )


class Vacancy(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Qoralama"
        PENDING = "pending", "Moderatsiyada"
        PUBLISHED = "published", "E'lon qilingan"
        REJECTED = "rejected", "Rad etilgan"
        CLOSED = "closed", "Yopilgan"

    class EmploymentType(models.TextChoices):
        FULL = "full", "To'liq stavka"
        PART = "part", "Yarim stavka"
        REMOTE = "remote", "Masofaviy"
        INTERNSHIP = "internship", "Amaliyot/stajirovka"
        CONTRACT = "contract", "Shartnoma asosida"

    employer = models.ForeignKey(Employer, on_delete=models.CASCADE, related_name="vacancies")
    title = models.CharField("Lavozim nomi", max_length=200)
    region = models.CharField("Hudud", max_length=60, choices=Region.choices)
    employment_type = models.CharField("Ish turi", max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL)
    salary_min = models.PositiveBigIntegerField("Ish haqi (dan), so'm", null=True, blank=True)
    salary_max = models.PositiveBigIntegerField("Ish haqi (gacha), so'm", null=True, blank=True)
    requirements = models.TextField("Talablar")
    duties = models.TextField("Vazifalar")
    schedule = models.CharField("Ish grafigi", max_length=200, blank=True)
    deadline = models.DateField("Murojaat muddati")
    directions = models.ManyToManyField(Direction, verbose_name="Mos ta'lim yo'nalishlari", blank=True, related_name="vacancies")
    status = models.CharField("Holati", max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    moderation_comment = models.CharField("Moderator izohi", max_length=300, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = VacancyQuerySet.as_manager()

    class Meta:
        verbose_name = "Vakansiya"
        verbose_name_plural = "Vakansiyalar"
        ordering = ["-published_at", "-created_at", "-id"]

    def __str__(self):
        return f"{self.title} — {self.employer.name}"

    def get_absolute_url(self):
        return reverse("vacancies:detail", args=[self.pk])

    @property
    def is_open(self):
        return (
            self.status == self.Status.PUBLISHED
            and self.deadline >= timezone.localdate()
            and self.employer.status == Employer.Status.APPROVED
        )

    @property
    def is_expired(self):
        return self.deadline < timezone.localdate()

    @property
    def days_left(self):
        return (self.deadline - timezone.localdate()).days

    @property
    def salary_display(self):
        def fmt(n):
            return f"{n:,}".replace(",", " ")
        if self.salary_min and self.salary_max:
            return f"{fmt(self.salary_min)} – {fmt(self.salary_max)} so'm"
        if self.salary_min:
            return f"{fmt(self.salary_min)} so'mdan"
        if self.salary_max:
            return f"{fmt(self.salary_max)} so'mgacha"
        return "Kelishiladi"

    @property
    def status_badge(self):
        return {"draft": "secondary", "pending": "warning", "published": "success", "rejected": "danger", "closed": "dark"}.get(self.status, "secondary")


class Application(models.Model):
    class Status(models.TextChoices):
        SENT = "sent", "Yuborildi"
        REVIEWING = "reviewing", "Ko'rib chiqilmoqda"
        INTERVIEW = "interview", "Suhbatga taklif qilindi"
        ACCEPTED = "accepted", "Qabul qilindi"
        REJECTED = "rejected", "Rad etildi"
        WITHDRAWN = "withdrawn", "Bekor qilindi"

    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications")
    cover_letter = models.TextField("Qo'shimcha xat", blank=True)
    status = models.CharField("Holati", max_length=20, choices=Status.choices, default=Status.SENT, db_index=True)
    interview_at = models.DateTimeField("Suhbat vaqti", null=True, blank=True)
    interview_place = models.CharField("Suhbat joyi / havola", max_length=250, blank=True)
    employer_comment = models.CharField("Ish beruvchi izohi", max_length=500, blank=True)
    created_at = models.DateTimeField("Topshirilgan", auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ariza"
        verbose_name_plural = "Arizalar"
        ordering = ["-created_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["vacancy", "applicant"], name="uniq_application_per_vacancy")]

    def __str__(self):
        return f"{self.applicant} → {self.vacancy.title}"

    @property
    def can_withdraw(self):
        return self.status in (self.Status.SENT, self.Status.REVIEWING, self.Status.INTERVIEW)

    @property
    def status_badge(self):
        return {
            "sent": "primary", "reviewing": "info", "interview": "warning",
            "accepted": "success", "rejected": "danger", "withdrawn": "secondary",
        }.get(self.status, "secondary")
