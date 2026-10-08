from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

from accounts.models import Direction, Faculty, Region
from core.validators import document_extensions, image_extensions, validate_file_size


class EmploymentStatus(models.TextChoices):
    UNKNOWN = "unknown", "Aniqlanmagan"
    LOOKING = "looking", "Ish izlayapti"
    EMPLOYED = "employed", "Ishga joylashgan"
    SELF_EMPLOYED = "self_employed", "O'zini o'zi band qilgan"
    STUDYING = "studying", "O'qishni davom ettirmoqda"
    NOT_LOOKING = "not_looking", "Ish izlamayapti"


class StudentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    external_id = models.CharField("Tashqi tizim ID (HEMIS)", max_length=50, null=True, blank=True, unique=True)
    birth_date = models.DateField("Tug'ilgan sana", null=True, blank=True)
    region = models.CharField("Yashash hududi", max_length=60, choices=Region.choices, blank=True)
    address = models.CharField("Manzil", max_length=300, blank=True)
    faculty = models.ForeignKey(Faculty, verbose_name="Fakultet", null=True, blank=True, on_delete=models.SET_NULL, related_name="students")
    direction = models.ForeignKey(Direction, verbose_name="Ta'lim yo'nalishi", null=True, blank=True, on_delete=models.SET_NULL, related_name="students")
    course = models.PositiveSmallIntegerField("Kurs", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(6)])
    graduation_year = models.PositiveSmallIntegerField("Bitiruv yili", null=True, blank=True, validators=[MinValueValidator(1990), MaxValueValidator(2100)])
    desired_position = models.CharField("Maqsad qilingan lavozim", max_length=200, blank=True)
    about = models.TextField("O'zi haqida", blank=True)
    photo = models.ImageField("Rasm", upload_to="students/photos/", blank=True, validators=[image_extensions, validate_file_size])

    employment_status = models.CharField("Bandlik holati", max_length=20, choices=EmploymentStatus.choices, default=EmploymentStatus.UNKNOWN, db_index=True)
    employer_name = models.CharField("Ishga joylashgan tashkilot", max_length=250, blank=True)
    position = models.CharField("Lavozimi", max_length=200, blank=True)
    employed_date = models.DateField("Ishga joylashgan sana", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Talaba/bitiruvchi profili"
        verbose_name_plural = "Talaba va bitiruvchilar profillari"
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self):
        return str(self.user)

    def get_absolute_url(self):
        return reverse("students:monitor_detail", args=[self.pk])

    @property
    def is_graduate(self):
        return self.user.role == "graduate"

    @property
    def status_badge(self):
        return {
            "looking": "primary", "employed": "success", "self_employed": "info",
            "studying": "warning", "not_looking": "secondary", "unknown": "light text-dark",
        }.get(self.employment_status, "secondary")

    @property
    def completeness(self):
        """Profil to'ldirilganlik foizi."""
        checks = [
            bool(self.user.first_name and self.user.last_name),
            bool(self.user.phone),
            bool(self.user.email),
            bool(self.birth_date),
            bool(self.region),
            bool(self.faculty_id and self.direction_id),
            bool(self.course or self.graduation_year),
            bool(self.about),
            bool(self.desired_position),
            self.skills.exists(),
            self.languages.exists(),
            self.experiences.exists() or self.certificates.exists() or self.portfolio.exists(),
        ]
        return int(round(100 * sum(checks) / len(checks)))


class Skill(models.Model):
    class Level(models.IntegerChoices):
        BEGINNER = 1, "Boshlang'ich"
        INTERMEDIATE = 2, "O'rta"
        ADVANCED = 3, "Yuqori"
        EXPERT = 4, "Mutaxassis"

    profile = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField("Ko'nikma", max_length=120)
    level = models.PositiveSmallIntegerField("Daraja", choices=Level.choices, default=Level.INTERMEDIATE)

    class Meta:
        verbose_name = "Ko'nikma"
        verbose_name_plural = "Ko'nikmalar"
        ordering = ["-level", "name"]

    def __str__(self):
        return self.name


class LanguageSkill(models.Model):
    class Level(models.TextChoices):
        A1 = "A1", "A1 — Boshlang'ich"
        A2 = "A2", "A2 — Elementar"
        B1 = "B1", "B1 — O'rta"
        B2 = "B2", "B2 — O'rtadan yuqori"
        C1 = "C1", "C1 — Ilg'or"
        C2 = "C2", "C2 — Mukammal"
        NATIVE = "native", "Ona tili"

    profile = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="languages")
    language = models.CharField("Til", max_length=80)
    level = models.CharField("Daraja", max_length=10, choices=Level.choices, default=Level.B1)

    class Meta:
        verbose_name = "Til bilimi"
        verbose_name_plural = "Til bilimlari"
        ordering = ["language"]

    def __str__(self):
        return f"{self.language} ({self.level})"


class Certificate(models.Model):
    profile = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="certificates")
    title = models.CharField("Sertifikat nomi", max_length=200)
    issuer = models.CharField("Bergan tashkilot", max_length=200, blank=True)
    issue_date = models.DateField("Berilgan sana", null=True, blank=True)
    file = models.FileField("Fayl (PDF/rasm)", upload_to="students/certificates/%Y/", blank=True, validators=[document_extensions, validate_file_size])

    class Meta:
        verbose_name = "Sertifikat"
        verbose_name_plural = "Sertifikatlar"
        ordering = ["-issue_date", "title"]

    def __str__(self):
        return self.title


class Experience(models.Model):
    profile = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="experiences")
    company = models.CharField("Tashkilot", max_length=200)
    position = models.CharField("Lavozim", max_length=200)
    start_date = models.DateField("Boshlangan sana")
    end_date = models.DateField("Tugagan sana", null=True, blank=True, help_text="Hozir ham ishlayotgan bo'lsangiz bo'sh qoldiring")
    description = models.TextField("Vazifalar va yutuqlar", blank=True)

    class Meta:
        verbose_name = "Ish tajribasi"
        verbose_name_plural = "Ish tajribasi"
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.position} — {self.company}"


class PortfolioItem(models.Model):
    profile = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="portfolio")
    title = models.CharField("Loyiha nomi", max_length=200)
    description = models.TextField("Tavsif", blank=True)
    url = models.URLField("Havola", blank=True)
    file = models.FileField("Fayl", upload_to="students/portfolio/%Y/", blank=True, validators=[document_extensions, validate_file_size])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Portfolio elementi"
        verbose_name_plural = "Portfolio"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
