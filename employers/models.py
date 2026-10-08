from django.conf import settings
from django.db import models
from django.urls import reverse

from accounts.models import Region
from core.validators import image_extensions, phone_validator, stir_validator, validate_file_size


class Employer(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Tasdiqlanishi kutilmoqda"
        APPROVED = "approved", "Tasdiqlangan"
        REJECTED = "rejected", "Rad etilgan"
        BLOCKED = "blocked", "Bloklangan"

    class Cooperation(models.TextChoices):
        NONE = "none", "Hamkorlik yo'q"
        NEGOTIATION = "negotiation", "Muzokaralar olib borilmoqda"
        PARTNER = "partner", "Hamkor (shartnoma mavjud)"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employer")
    name = models.CharField("Tashkilot nomi", max_length=250)
    stir = models.CharField("STIR", max_length=9, unique=True, validators=[stir_validator])
    industry = models.CharField("Faoliyat sohasi", max_length=200)
    region = models.CharField("Hudud", max_length=60, choices=Region.choices)
    address = models.CharField("Manzil", max_length=300)
    phone = models.CharField("Telefon", max_length=16, validators=[phone_validator])
    email = models.EmailField("E-mail")
    website = models.URLField("Veb-sayt", blank=True)
    contact_name = models.CharField("Mas'ul shaxs F.I.Sh.", max_length=200)
    contact_position = models.CharField("Mas'ul shaxs lavozimi", max_length=150, blank=True)
    contact_phone = models.CharField("Mas'ul shaxs telefoni", max_length=16, validators=[phone_validator])
    description = models.TextField("Tashkilot haqida", blank=True)
    logo = models.ImageField("Logotip", upload_to="employers/logos/", blank=True, validators=[image_extensions, validate_file_size])
    status = models.CharField("Holati", max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    status_comment = models.CharField("Holat izohi", max_length=300, blank=True)
    cooperation = models.CharField("Institut bilan hamkorlik", max_length=20, choices=Cooperation.choices, default=Cooperation.NONE)
    created_at = models.DateTimeField("Ro'yxatdan o'tgan", auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ish beruvchi"
        verbose_name_plural = "Ish beruvchilar"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("employers:public_detail", args=[self.pk])

    @property
    def is_approved(self):
        return self.status == self.Status.APPROVED

    @property
    def status_badge(self):
        return {"pending": "warning", "approved": "success", "rejected": "danger", "blocked": "dark"}.get(self.status, "secondary")
