from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import Role
from accounts.permissions import STAFF_ROLES, role_required
from core.models import AuditLog
from core.services import audit, notify
from events.models import Event, EventRegistration
from events.services import cancel_registration, register_for_event
from vacancies.services import BusinessError

REGISTRANT_ROLES = (Role.STUDENT, Role.GRADUATE, Role.EMPLOYER)


def event_list(request):
    qs = Event.objects.filter(is_published=True).annotate(reg_count=Count("registrations"))
    now = timezone.now()
    tab = request.GET.get("tab", "upcoming")
    etype = request.GET.get("type", "")
    if etype in Event.Type.values:
        qs = qs.filter(event_type=etype)
    if tab == "past":
        qs = qs.filter(Q(end_at__lt=now) | Q(end_at__isnull=True, start_at__lt=now)).order_by("-start_at")
    else:
        tab = "upcoming"
        qs = qs.exclude(Q(end_at__lt=now) | Q(end_at__isnull=True, start_at__lt=now)).order_by("start_at")
    page = Paginator(qs, 9).get_page(request.GET.get("page"))
    registered = set()
    if request.user.is_authenticated:
        registered = set(EventRegistration.objects.filter(user=request.user).values_list("event_id", flat=True))
    return render(request, "events/list.html", {"page": page, "tab": tab, "type": etype, "types": Event.Type.choices, "registered": registered})


def event_detail(request, pk):
    event = get_object_or_404(Event.objects.prefetch_related("employers"), pk=pk)
    is_staff = request.user.is_authenticated and request.user.role in STAFF_ROLES
    if not event.is_published and not is_staff:
        raise Http404
    registration = None
    if request.user.is_authenticated:
        registration = EventRegistration.objects.filter(event=event, user=request.user).first()
    can_register = (request.user.is_authenticated and request.user.role in REGISTRANT_ROLES
                    and registration is None and event.registration_open)
    return render(request, "events/detail.html", {
        "event": event, "registration": registration, "can_register": can_register, "is_staff": is_staff,
        "employers": event.employers.filter(status="approved"),
    })


@role_required(*REGISTRANT_ROLES)
@require_POST
def register(request, pk):
    try:
        _, created = register_for_event(request.user, pk, request=request)
        if created:
            messages.success(request, "Tadbirga muvaffaqiyatli ro'yxatdan o'tdingiz.")
        else:
            messages.info(request, "Siz allaqachon ro'yxatdan o'tgansiz.")
    except BusinessError as e:
        messages.error(request, str(e))
    return redirect("events:detail", pk=pk)


@role_required(*REGISTRANT_ROLES)
@require_POST
def cancel(request, pk):
    try:
        cancel_registration(request.user, pk)
        messages.success(request, "Ro'yxatdan o'tish bekor qilindi.")
    except BusinessError as e:
        messages.error(request, str(e))
    return redirect("events:detail", pk=pk)


@role_required(*REGISTRANT_ROLES)
def my_events(request):
    regs = EventRegistration.objects.filter(user=request.user).select_related("event").order_by("-event__start_at")
    page = Paginator(regs, 15).get_page(request.GET.get("page"))
    return render(request, "events/my_events.html", {"page": page})


@role_required(*STAFF_ROLES)
def participants(request, pk):
    event = get_object_or_404(Event, pk=pk)
    regs = event.registrations.select_related("user").order_by("user__last_name", "user__first_name")
    if request.method == "POST":
        attended_ids = {int(x) for x in request.POST.getlist("attended") if x.isdigit()}
        with transaction.atomic():
            for reg in regs:
                value = reg.pk in attended_ids
                if reg.attended != value:
                    reg.attended = value
                    reg.save(update_fields=["attended"])
        audit(AuditLog.Action.DATA_CHANGE, request=request, obj=event, details=f"Qatnashuv belgilandi ({len(attended_ids)} ta)")
        messages.success(request, "Qatnashuv ma'lumotlari saqlandi.")
        return redirect("events:participants", pk=pk)
    return render(request, "events/participants.html", {"event": event, "regs": regs})
