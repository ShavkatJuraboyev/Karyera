from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models
from django.urls import reverse

from core.validators import phone_validator


class Role(models.TextChoices):
    STUDENT = "student", "Talaba"
    GRADUATE = "graduate", "Bitiruvchi"
    EMPLOYER = "employer", "Ish beruvchi"
    STAFF = "staff", "Karyera markazi xodimi"
    DEAN = "dean", "Fakultet/dekanat mas'uli"
    MANAGEMENT = "management", "Rahbariyat"
    ADMIN = "admin", "Administrator"


class Region(models.TextChoices):
    TASHKENT_CITY = "Toshkent shahri", "Toshkent shahri"
    TASHKENT = "Toshkent viloyati", "Toshkent viloyati"
    SAMARKAND = "Samarqand viloyati", "Samarqand viloyati"
    BUKHARA = "Buxoro viloyati", "Buxoro viloyati"
    NAVOIY = "Navoiy viloyati", "Navoiy viloyati"
    KASHKADARYA = "Qashqadaryo viloyati", "Qashqadaryo viloyati"
    SURKHANDARYA = "Surxondaryo viloyati", "Surxondaryo viloyati"
    JIZZAKH = "Jizzax viloyati", "Jizzax viloyati"
    SYRDARYA = "Sirdaryo viloyati", "Sirdaryo viloyati"
    FERGANA = "Farg'ona viloyati", "Farg'ona viloyati"
    ANDIJAN = "Andijon viloyati", "Andijon viloyati"
    NAMANGAN = "Namangan viloyati", "Namangan viloyati"
    KHOREZM = "Xorazm viloyati", "Xorazm viloyati"
    KARAKALPAKSTAN = "Qoraqalpog'iston Respublikasi", "Qoraqalpog'iston Respublikasi"
    ABROAD = "Xorijiy davlat", "Xorijiy davlat"


class Faculty(models.Model):
    name = models.CharField("Fakultet nomi", max_length=200, unique=True)
    code = models.CharField("Qisqa kodi", max_length=20, blank=True)
    is_active = models.BooleanField("Faol", default=True)

    class Meta:
        verbose_name = "Fakultet"
        verbose_name_plural = "Fakultetlar"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Direction(models.Model):
    faculty = models.ForeignKey(Faculty, verbose_name="Fakultet", on_delete=models.CASCADE, related_name="directions")
    name = models.CharField("Ta'lim yo'nalishi", max_length=250)
    code = models.CharField("Shifri", max_length=30, blank=True)
    is_active = models.BooleanField("Faol", default=True)

    class Meta:
        verbose_name = "Ta'lim yo'nalishi"
        verbose_name_plural = "Ta'lim yo'nalishlari"
        ordering = ["faculty__name", "name"]
        constraints = [models.UniqueConstraint(fields=["faculty", "name"], name="uniq_direction_per_faculty")]

    def __str__(self):
        return self.name


class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    patronymic = models.CharField("Otasining ismi", max_length=100, blank=True)
    phone = models.CharField("Telefon", max_length=16, blank=True, validators=[phone_validator])
    role = models.CharField("Rol", max_length=20, choices=Role.choices, default=Role.STUDENT, db_index=True)
    faculty = models.ForeignKey(
        Faculty, verbose_name="Fakultet (dekanat mas'uli uchun)", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="staff_users",
    )
    telegram_chat_id = models.CharField("Telegram chat ID", max_length=50, blank=True)

    objects = UserManager()

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        ordering = ["last_name", "first_name", "username"]

    def save(self, *args, **kwargs):
        # Administrator roli Django admin paneliga to'liq kirish huquqini beradi, boshqa rollar bermaydi.
        is_admin = self.role == Role.ADMIN
        self.is_staff = is_admin
        self.is_superuser = is_admin
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name or self.username

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name, self.patronymic]
        return " ".join(p for p in parts if p).strip()

    @property
    def short_name(self):
        return self.first_name or self.username

    @property
    def is_candidate(self):
        return self.role in (Role.STUDENT, Role.GRADUATE)

    @property
    def is_employer(self):
        return self.role == Role.EMPLOYER

    @property
    def is_career_staff(self):
        """Karyera markazi xodimi yoki administrator."""
        return self.role in (Role.STAFF, Role.ADMIN)

    @property
    def can_view_analytics(self):
        return self.role in (Role.STAFF, Role.ADMIN, Role.MANAGEMENT, Role.DEAN)

    def get_absolute_url(self):
        return reverse("accounts:profile")
