from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from core.validators import image_extensions, validate_file_size


class News(models.Model):
    class Category(models.TextChoices):
        NEWS = "news", "Yangilik"
        EMPLOYER = "employer", "Ish beruvchi e'loni"
        EVENT = "event", "Tadbir"
        IMPORTANT = "important", "Muhim xabar"

    title = models.CharField("Sarlavha", max_length=250)
    category = models.CharField("Turkum", max_length=20, choices=Category.choices, default=Category.NEWS)
    body = models.TextField("Matn")
    image = models.ImageField("Rasm", upload_to="news/%Y/%m/", blank=True, validators=[image_extensions, validate_file_size])
    is_published = models.BooleanField("E'lon qilingan", default=True)
    is_pinned = models.BooleanField("Yuqorida qadab qo'yish", default=False)
    published_at = models.DateTimeField("E'lon qilingan vaqt", default=timezone.now)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="news")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Yangilik"
        verbose_name_plural = "Yangiliklar va e'lonlar"
        ordering = ["-is_pinned", "-published_at", "-id"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("core:news_detail", args=[self.pk])

    @property
    def badge(self):
        return {"news": "primary", "employer": "success", "event": "info", "important": "danger"}.get(self.category, "secondary")


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField("Sarlavha", max_length=200)
    message = models.TextField("Xabar", blank=True)
    link = models.CharField("Havola", max_length=300, blank=True)
    is_read = models.BooleanField("O'qilgan", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bildirishnoma"
        verbose_name_plural = "Bildirishnomalar"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["user", "is_read"])]

    def __str__(self):
        return f"{self.user_id}: {self.title}"


class AuditLog(models.Model):
    class Action(models.TextChoices):
        LOGIN = "login", "Tizimga kirish"
        LOGIN_FAILED = "login_failed", "Kirishda xatolik"
        LOGOUT = "logout", "Tizimdan chiqish"
        REGISTER = "register", "Ro'yxatdan o'tish"
        VACANCY_CREATE = "vacancy_create", "Vakansiya yaratildi"
        VACANCY_UPDATE = "vacancy_update", "Vakansiya o'zgartirildi"
        VACANCY_DELETE = "vacancy_delete", "Vakansiya o'chirildi"
        VACANCY_STATUS = "vacancy_status", "Vakansiya holati o'zgardi"
        APPLICATION = "application", "Ariza amali"
        EMPLOYER_STATUS = "employer_status", "Ish beruvchi holati o'zgardi"
        USER_CREATE = "user_create", "Foydalanuvchi yaratildi"
        USER_UPDATE = "user_update", "Foydalanuvchi o'zgartirildi"
        ROLE_CHANGE = "role_change", "Foydalanuvchi huquqi o'zgartirildi"
        PASSWORD = "password", "Parol o'zgartirildi"
        EXPORT = "export", "Ma'lumot eksporti"
        DATA_CHANGE = "data_change", "Ma'lumot o'zgartirildi"
        DATA_DELETE = "data_delete", "Ma'lumot o'chirildi"
        OTHER = "other", "Boshqa"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs")
    username = models.CharField("Login", max_length=150, blank=True)
    action = models.CharField("Amal", max_length=30, choices=Action.choices, db_index=True)
    object_type = models.CharField("Obyekt turi", max_length=60, blank=True)
    object_id = models.CharField("Obyekt ID", max_length=40, blank=True)
    object_repr = models.CharField("Obyekt", max_length=250, blank=True)
    details = models.TextField("Tafsilot", blank=True)
    ip_address = models.GenericIPAddressField("IP manzil", null=True, blank=True)
    created_at = models.DateTimeField("Vaqt", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Audit yozuvi"
        verbose_name_plural = "Audit jurnali"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.username} {self.action}"
