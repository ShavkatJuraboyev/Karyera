"""Karyera markazi xodimlari uchun umumiy CRUD (ro'yxat, yaratish, tahrirlash, o'chirish) generatori."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.views.decorators.http import require_http_methods

from accounts.permissions import STAFF_ROLES, role_required
from core.models import AuditLog
from core.services import audit


def crud_patterns(*, slug, name, namespace, model, form_class, title, columns, search_fields=(),
                  multipart=False, queryset=None, can_delete=None, pre_save=None, extra_links=None, per_page=20):
    """CRUD uchun (view funksiyalari, url ro'yxati) qaytaradi.

    columns: [(sarlavha, atribut_nomi), ...]
    can_delete: obj -> (bool, xabar)
    pre_save: (request, obj, created) -> None
    extra_links: [(sarlavha, url_name, pk_arg)] — qatordagi qo'shimcha havolalar
    """
    base = lambda: queryset() if callable(queryset) else model.objects.all()
    list_name, create_name, edit_name, delete_name = (f"{name}_{x}" for x in ("list", "create", "edit", "delete"))

    @role_required(*STAFF_ROLES)
    def list_view(request):
        qs = base()
        q = request.GET.get("q", "").strip()
        if q and search_fields:
            cond = Q()
            for f in search_fields:
                cond |= Q(**{f"{f}__icontains": q})
            qs = qs.filter(cond)
        page = Paginator(qs, per_page).get_page(request.GET.get("page"))
        return render(request, "core/manage_list.html", {
            "page": page, "title": title, "columns": columns, "q": q, "has_search": bool(search_fields),
            "create_url": reverse(f"{namespace}:{create_name}"), "edit_name": f"{namespace}:{edit_name}",
            "delete_name": f"{namespace}:{delete_name}", "extra_links": [(l, f"{namespace}:{u}", a) for l, u, a in (extra_links or [])],
        })

    @role_required(*STAFF_ROLES)
    @require_http_methods(["GET", "POST"])
    def form_view(request, pk=None):
        instance = get_object_or_404(base(), pk=pk) if pk else None
        form = form_class(request.POST or None, request.FILES or None, instance=instance)
        if request.method == "POST" and form.is_valid():
            obj = form.save(commit=False)
            created = obj.pk is None
            if pre_save:
                pre_save(request, obj, created)
            obj.save()
            form.save_m2m()
            audit(AuditLog.Action.DATA_CHANGE, request=request, obj=obj, details=f"{title}: {'yaratildi' if created else 'o`zgartirildi'}")
            messages.success(request, "Ma'lumot saqlandi.")
            return redirect(f"{namespace}:{list_name}")
        return render(request, "core/manage_form.html", {
            "form": form, "title": title, "editing": bool(pk), "multipart": multipart,
            "back_url": reverse(f"{namespace}:{list_name}"),
        })

    @role_required(*STAFF_ROLES)
    @require_http_methods(["GET", "POST"])
    def delete_view(request, pk):
        obj = get_object_or_404(base(), pk=pk)
        allowed, msg = (True, "") if can_delete is None else can_delete(obj)
        if request.method == "POST":
            if not allowed:
                messages.error(request, msg)
            else:
                audit(AuditLog.Action.DATA_DELETE, request=request, obj=obj, details=f"{title}: o'chirildi")
                obj.delete()
                messages.success(request, "Ma'lumot o'chirildi.")
            return redirect(f"{namespace}:{list_name}")
        return render(request, "core/manage_confirm_delete.html", {
            "obj": obj, "title": title, "allowed": allowed, "message": msg,
            "back_url": reverse(f"{namespace}:{list_name}"),
        })

    patterns = [
        path(f"boshqaruv/{slug}/", list_view, name=list_name),
        path(f"boshqaruv/{slug}/yangi/", form_view, name=create_name),
        path(f"boshqaruv/{slug}/<int:pk>/tahrirlash/", form_view, name=edit_name),
        path(f"boshqaruv/{slug}/<int:pk>/ochirish/", delete_view, name=delete_name),
    ]
    return patterns
