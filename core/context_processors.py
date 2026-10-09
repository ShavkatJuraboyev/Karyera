from accounts.models import Role


def global_context(request):
    ctx = {"SITE_NAME": "Karyera SIES", "Role": Role}
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        from core.models import Notification
        ctx["unread_notifications"] = Notification.objects.filter(user=user, is_read=False).count()
        ctx["recent_notifications"] = list(Notification.objects.filter(user=user).order_by("-created_at", "-id")[:5])
    return ctx
