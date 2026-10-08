from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.urls import path, reverse_lazy

from accounts import views
from accounts.forms import StyledPasswordResetForm, StyledSetPasswordForm

app_name = "accounts"

urlpatterns = [
    path("kirish/", views.CustomLoginView.as_view(), name="login"),
    path("chiqish/", LogoutView.as_view(), name="logout"),
    path("royxatdan-otish/", views.register_candidate, name="register"),
    path("royxatdan-otish/ish-beruvchi/", views.register_employer, name="register_employer"),
    path("profil/", views.account_settings, name="profile"),
    path("foydalanuvchilar/", views.user_list, name="user_list"),
    path("foydalanuvchilar/yangi/", views.user_create, name="user_create"),
    path("foydalanuvchilar/<int:pk>/", views.user_edit, name="user_edit"),
    path("parol-ozgartirish/", views.CustomPasswordChangeView.as_view(), name="password_change"),
    path("parol-tiklash/", auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset.html", form_class=StyledPasswordResetForm, email_template_name="accounts/password_reset_email.txt",
        subject_template_name="accounts/password_reset_subject.txt",
        success_url=reverse_lazy("accounts:password_reset_done")), name="password_reset"),
    path("parol-tiklash/yuborildi/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/password_reset_done.html"), name="password_reset_done"),
    path("parol-tiklash/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html", form_class=StyledSetPasswordForm,
        success_url=reverse_lazy("accounts:password_reset_complete")), name="password_reset_confirm"),
    path("parol-tiklash/tayyor/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/password_reset_complete.html"), name="password_reset_complete"),
]
