from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

from accounts.forms import (AccountForm, StyledPasswordChangeForm, CandidateRegistrationForm, EmployerRegistrationForm, LoginForm,
                            UserAdminCreateForm, UserAdminEditForm)
from accounts.models import Role, User
from accounts.permissions import role_required
from core.models import AuditLog
from core.services import audit, notify_many


class CustomLoginView(LoginView):
    form_class = LoginForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class CustomPasswordChangeView(PasswordChangeView):
    form_class = StyledPasswordChangeForm
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        response = super().form_valid(form)
        audit(AuditLog.Action.PASSWORD, request=self.request, details="Parol o'zgartirildi")
        messages.success(self.request, "Parolingiz muvaffaqiyatli o'zgartirildi.")
        return response


def _login_new_user(request, user):
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")


@require_http_methods(["GET", "POST"])
def register_candidate(request):
    if request.user.is_authenticated:
        return redirect("core:redirect_by_role")
    form = CandidateRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        audit(AuditLog.Action.REGISTER, request=request, user=user, obj=user, details=f"Rol: {user.get_role_display()}")
        _login_new_user(request, user)
        messages.success(request, "Ro'yxatdan muvaffaqiyatli o'tdingiz! Profilingizni to'ldiring.")
        return redirect("students:profile")
    return render(request, "accounts/register_candidate.html", {"form": form})


@require_http_methods(["GET", "POST"])
def register_employer(request):
    if request.user.is_authenticated:
        return redirect("core:redirect_by_role")
    form = EmployerRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        audit(AuditLog.Action.REGISTER, request=request, user=user, obj=user.employer, details="Ish beruvchi ro'yxatdan o'tdi")
        staff = User.objects.filter(role__in=[Role.STAFF, Role.ADMIN], is_active=True)
        notify_many(staff, "Yangi ish beruvchi", f"{user.employer.name} ro'yxatdan o'tdi va tasdiqlashni kutmoqda.", "/boshqaruv/ish-beruvchilar/?status=pending")
        _login_new_user(request, user)
        messages.success(request, "Ro'yxatdan o'tdingiz. Karyera markazi tashkilotingizni tasdiqlagach vakansiya joylashtira olasiz.")
        return redirect("employers:dashboard")
    return render(request, "accounts/register_employer.html", {"form": form})


@login_required
def account_settings(request):
    form = AccountForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        audit(AuditLog.Action.DATA_CHANGE, request=request, obj=request.user, details="Shaxsiy ma'lumotlar yangilandi")
        messages.success(request, "Ma'lumotlar saqlandi.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})


# ------------------------------------------------------------- Administrator: foydalanuvchilarni boshqarish
@role_required(Role.ADMIN)
def user_list(request):
    qs = User.objects.select_related("faculty").all()
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")
    active = request.GET.get("active", "")
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
    if role in Role.values:
        qs = qs.filter(role=role)
    if active in ("1", "0"):
        qs = qs.filter(is_active=active == "1")
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(request, "accounts/user_list.html", {"page": page, "q": q, "role": role, "active": active, "roles": Role.choices})


@role_required(Role.ADMIN)
def user_create(request):
    form = UserAdminCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        audit(AuditLog.Action.USER_CREATE, request=request, obj=user, details=f"Rol: {user.get_role_display()}")
        messages.success(request, f"{user.username} foydalanuvchisi yaratildi.")
        return redirect("accounts:user_list")
    return render(request, "accounts/user_form.html", {"form": form, "title": "Yangi foydalanuvchi"})


@role_required(Role.ADMIN)
def user_edit(request, pk):
    target = get_object_or_404(User, pk=pk)
    old_role, old_active = target.role, target.is_active
    form = UserAdminEditForm(request.POST or None, instance=target, current_user=request.user)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        changes = []
        if user.role != old_role:
            changes.append(f"rol: {Role(old_role).label} → {user.get_role_display()}")
        if user.is_active != old_active:
            changes.append(f"faol: {old_active} → {user.is_active}")
        if form.cleaned_data.get("new_password"):
            changes.append("parol almashtirildi")
        action = AuditLog.Action.ROLE_CHANGE if any(c.startswith(("rol", "faol")) for c in changes) else AuditLog.Action.USER_UPDATE
        audit(action, request=request, obj=user, details="; ".join(changes) or "Ma'lumotlar yangilandi")
        messages.success(request, "Foydalanuvchi ma'lumotlari saqlandi.")
        return redirect("accounts:user_list")
    return render(request, "accounts/user_form.html", {"form": form, "title": f"Tahrirlash: {target.username}", "target": target})
