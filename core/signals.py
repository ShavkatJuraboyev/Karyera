from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from core.models import AuditLog
from core.services import audit


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    audit(AuditLog.Action.LOGIN, request=request, user=user, details="Tizimga muvaffaqiyatli kirdi")


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if user is not None:
        audit(AuditLog.Action.LOGOUT, request=request, user=user)


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    audit(AuditLog.Action.LOGIN_FAILED, request=request, username=str(credentials.get("username", ""))[:150],
          details="Noto'g'ri login yoki parol")
