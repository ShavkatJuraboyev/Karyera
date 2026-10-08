"""Umumiy xizmatlar: audit jurnali va bildirishnomalar (tizim ichida, e-mail, Telegram)."""
import json
import logging
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.mail import send_mail

from core.models import AuditLog, Notification

logger = logging.getLogger("karyera")


def get_client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")
    return ip or None


def audit(action, request=None, user=None, obj=None, details="", username=""):
    """Muhim amalni audit jurnaliga yozadi. Hech qachon asosiy jarayonni to'xtatmaydi."""
    try:
        if user is None and request is not None and getattr(request, "user", None) and request.user.is_authenticated:
            user = request.user
        AuditLog.objects.create(
            user=user if user is not None and getattr(user, "pk", None) else None,
            username=(user.get_username() if user is not None and getattr(user, "pk", None) else username)[:150],
            action=action,
            object_type=obj.__class__.__name__ if obj is not None else "",
            object_id=str(getattr(obj, "pk", "") or "") if obj is not None else "",
            object_repr=str(obj)[:250] if obj is not None else "",
            details=details[:4000],
            ip_address=get_client_ip(request),
        )
    except Exception:  # pragma: no cover - audit xatosi ilovani buzmasligi kerak
        logger.exception("Audit yozuvini saqlashda xatolik")


def _send_telegram(chat_id, text):
    token = settings.TELEGRAM_BOT_TOKEN
    if not token or not chat_id:
        return
    try:
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
        urllib.request.urlopen(req, timeout=3).read()
    except Exception:
        logger.warning("Telegram xabarini yuborib bo'lmadi (chat_id=%s)", chat_id)


def notify(user, title, message="", link="", external=True):
    """Foydalanuvchiga bildirishnoma yuboradi: tizim ichida + (ixtiyoriy) e-mail va Telegram."""
    if user is None or not getattr(user, "pk", None):
        return None
    notification = Notification.objects.create(user=user, title=title[:200], message=message, link=link[:300])
    if external:
        if settings.EMAIL_NOTIFICATIONS and user.email:
            try:
                send_mail(f"Karyera SIES: {title}", message or title, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
            except Exception:
                logger.warning("E-mail yuborib bo'lmadi (user=%s)", user.pk)
        if user.telegram_chat_id:
            _send_telegram(user.telegram_chat_id, f"{title}\n{message}")
    return notification


def notify_many(users, title, message="", link="", external=True):
    """Bir nechta foydalanuvchiga xabar. external=False bo'lsa faqat tizim ichida (ommaviy yuborishda)."""
    if not external:
        Notification.objects.bulk_create(
            [Notification(user=u, title=title[:200], message=message, link=link[:300]) for u in users]
        )
        return
    for user in users:
        notify(user, title, message, link)
