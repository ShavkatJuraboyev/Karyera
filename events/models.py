from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from employers.models import Employer


class Event(models.Model):
    class Type(models.TextChoices):
        JOB_FAIR = "job_fair", "Mehnat yarmarkasi"
        SEMINAR = "seminar", "Seminar"
        TRAINING = "training", "Trening"
        MEETING = "meeting", "Ish beruvchi bilan uchrashuv"
        OTHER = "other", "Boshqa"

    title = models.CharField("Tadbir nomi", max_length=250)
    event_type = models.CharField("Turi", max_length=20, choices=Type.choices, default=Type.OTHER)
    description = models.TextField("Tavsif")
    location = models.CharField("O'tkaziladigan joy", max_length=250)
    start_at = models.DateTimeField("Boshlanish vaqti")
    end_at = models.DateTimeField("Tugash vaqti", null=True, blank=True)
    capacity = models.PositiveIntegerField("Ishtirokchilar soni (cheklov)", null=True, blank=True, help_text="Bo'sh qoldirilsa — cheklovsiz")
    employers = models.ManyToManyField(Employer, verbose_name="Ishtirok etuvchi ish beruvchilar", blank=True, related_name="events")
    is_published = models.BooleanField("E'lon qilingan", default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_events")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Karyera tadbiri"
        verbose_name_plural = "Karyera tadbirlari"
        ordering = ["-start_at", "-id"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("events:detail", args=[self.pk])

    @property
    def is_past(self):
        end = self.end_at or self.start_at
        return end < timezone.now()

    @property
    def registered_count(self):
        return self.registrations.count()

    @property
    def is_full(self):
        return self.capacity is not None and self.registered_count >= self.capacity

    @property
    def spots_left(self):
        if self.capacity is None:
            return None
        return max(self.capacity - self.registered_count, 0)

    @property
    def registration_open(self):
        return self.is_published and not self.is_past and not self.is_full

    @property
    def badge(self):
        return {"job_fair": "success", "seminar": "primary", "training": "info", "meeting": "warning"}.get(self.event_type, "secondary")


class EventRegistration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="registrations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="event_registrations")
    attended = models.BooleanField("Qatnashdi", default=False)
    created_at = models.DateTimeField("Ro'yxatdan o'tgan", auto_now_add=True)

    class Meta:
        verbose_name = "Tadbir ishtirokchisi"
        verbose_name_plural = "Tadbir ishtirokchilari"
        ordering = ["created_at"]
        constraints = [models.UniqueConstraint(fields=["event", "user"], name="uniq_event_registration")]

    def __str__(self):
        return f"{self.user} → {self.event}"
