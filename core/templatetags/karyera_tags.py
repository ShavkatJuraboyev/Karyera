import datetime

from django import template
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.html import format_html

register = template.Library()


@register.filter
def attr(obj, name):
    """Obyektning atributini (yoki chaqiriladigan metodini) qaytaradi va chiroyli ko'rinishga keltiradi."""
    value = obj
    for part in str(name).split("."):
        value = getattr(value, part, "")
        if callable(value):
            value = value()
    if isinstance(value, bool):
        return "Ha" if value else "Yo'q"
    if isinstance(value, datetime.datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime("%d.%m.%Y %H:%M")
    if isinstance(value, datetime.date):
        return value.strftime("%d.%m.%Y")
    if value is None:
        return "—"
    return value


@register.filter
def get_item(mapping, key):
    try:
        return mapping.get(key, "")
    except AttributeError:
        return ""


@register.simple_tag
def badge(css, text):
    return format_html('<span class="badge text-bg-{}">{}</span>', css, text)


@register.simple_tag(takes_context=True)
def qs_replace(context, **kwargs):
    """Joriy so'rov parametrlarini saqlagan holda ayrimlarini almashtiradi (sahifalash uchun)."""
    request = context["request"]
    params = request.GET.copy()
    for k, v in kwargs.items():
        params[k] = v
    return params.urlencode()


@register.filter
def pct(value, total):
    try:
        return round(100 * float(value) / float(total), 1) if total else 0
    except (TypeError, ValueError):
        return 0


@register.simple_tag(takes_context=True)
def nav_active(context, *prefixes, exact=False):
    """Joriy sahifa berilgan manzillardan biri bilan boshlansa 'active' qaytaradi (menyu uchun)."""
    path = context["request"].path
    for p in prefixes:
        if (path == p) if (exact or p == "/") else path.startswith(p):
            return "active"
    return ""


@register.filter
def initials(user):
    """Foydalanuvchi bosh harflari (avatar uchun)."""
    first = (getattr(user, "first_name", "") or "")[:1]
    last = (getattr(user, "last_name", "") or "")[:1]
    value = (first + last) or (getattr(user, "username", "") or "?")[:1]
    return value.upper()


@register.simple_tag(takes_context=True)
def qs_remove(context, *keys):
    """Joriy so'rov parametrlaridan berilgan kalitlarni (va sahifalashni) olib tashlaydi (filtr chiplari uchun)."""
    params = context["request"].GET.copy()
    for k in keys:
        params.pop(k, None)
    params.pop("page", None)
    return params.urlencode()
