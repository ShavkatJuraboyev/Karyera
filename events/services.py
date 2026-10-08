from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from core.models import AuditLog
from core.services import audit, notify
from events.models import Event, EventRegistration
from vacancies.services import BusinessError


def register_for_event(user, pk, request=None):
    """Tadbirga ro'yxatdan o'tkazadi. (registration, created) qaytaradi."""
    with transaction.atomic():
        event = get_object_or_404(Event.objects.select_for_update(), pk=pk, is_published=True)
        existing = EventRegistration.objects.filter(event=event, user=user).first()
        if existing:
            return existing, False
        if event.is_past:
            raise BusinessError("Tadbir allaqachon o'tib bo'lgan.")
        if event.is_full:
            raise BusinessError("Afsuski, joylar tugagan.")
        reg = EventRegistration.objects.create(event=event, user=user)
    audit(AuditLog.Action.OTHER, request=request, user=user, obj=event, details="Tadbirga ro'yxatdan o'tdi")
    notify(user, "Tadbirga ro'yxatdan o'tdingiz",
           f"{event.title} — {timezone.localtime(event.start_at):%d.%m.%Y %H:%M}, {event.location}", event.get_absolute_url())
    return reg, True


def cancel_registration(user, pk):
    event = get_object_or_404(Event, pk=pk)
    reg = EventRegistration.objects.filter(event=event, user=user).first()
    if not reg:
        raise BusinessError("Siz bu tadbirga ro'yxatdan o'tmagansiz.")
    if event.is_past:
        raise BusinessError("O'tib ketgan tadbir ro'yxatini bekor qilib bo'lmaydi.")
    reg.delete()
