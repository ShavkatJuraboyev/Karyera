from datetime import date

from django import forms
from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.forms import (AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm,
                                       UserCreationForm)
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import Direction, Faculty, Region, Role, User
from core.forms import BootstrapFormMixin
from core.validators import normalize_phone, phone_validator, stir_validator


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    """Kirish formasi. Ketma-ket xato urinishlarda vaqtincha bloklaydi."""

    def _lock_key(self):
        from core.services import get_client_ip
        username = (self.data.get("username") or "").strip().lower()
        return f"login-fail:{get_client_ip(self.request)}:{username}"

    def clean(self):
        key = self._lock_key()
        attempts = cache.get(key, 0)
        if attempts >= settings.LOGIN_MAX_ATTEMPTS:
            minutes = max(settings.LOGIN_LOCKOUT_SECONDS // 60, 1)
            raise ValidationError(f"Juda ko'p noto'g'ri urinish. Iltimos, {minutes} daqiqadan so'ng qayta urinib ko'ring.", code="locked")
        try:
            cleaned = super().clean()
        except ValidationError:
            cache.set(key, attempts + 1, settings.LOGIN_LOCKOUT_SECONDS)
            raise
        cache.delete(key)
        return cleaned


class PhoneEmailCleanMixin:
    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        qs = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if email and qs.exists():
            raise ValidationError("Bu e-mail manzil allaqachon ro'yxatdan o'tgan.")
        return email

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data.get("phone"))
        if phone:
            phone_validator(phone)
        return phone


class CandidateRegistrationForm(PhoneEmailCleanMixin, BootstrapFormMixin, UserCreationForm):
    role = forms.ChoiceField(
        label="Siz kimsiz?",
        choices=[(Role.STUDENT.value, Role.STUDENT.label), (Role.GRADUATE.value, Role.GRADUATE.label)],
    )
    faculty = forms.ModelChoiceField(label="Fakultet", queryset=Faculty.objects.filter(is_active=True))
    direction = forms.ModelChoiceField(label="Ta'lim yo'nalishi", queryset=Direction.objects.filter(is_active=True))
    course = forms.IntegerField(label="Kurs", min_value=1, max_value=6, required=False)
    graduation_year = forms.IntegerField(label="Bitiruv yili", min_value=1990, max_value=2100, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "last_name", "first_name", "patronymic", "email", "phone")

    field_order = ["role", "last_name", "first_name", "patronymic", "faculty", "direction", "course",
                   "graduation_year", "email", "phone", "username", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("last_name", "first_name", "email", "phone"):
            self.fields[name].required = True
        self.fields["phone"].widget.attrs["placeholder"] = "+998901234567"
        self.fields["faculty"].widget.attrs["data-dependent-target"] = "id_direction"
        self.fields["direction"].widget.attrs["data-faculty-url"] = "/malumotnoma/yonalishlar/"
        self.fields["graduation_year"].initial = date.today().year

    def clean(self):
        cleaned = super().clean()
        faculty, direction, role = cleaned.get("faculty"), cleaned.get("direction"), cleaned.get("role")
        if faculty and direction and direction.faculty_id != faculty.pk:
            self.add_error("direction", "Tanlangan yo'nalish bu fakultetga tegishli emas.")
        if role == Role.STUDENT and not cleaned.get("course"):
            self.add_error("course", "Talaba uchun kursni ko'rsating.")
        if role == Role.GRADUATE and not cleaned.get("graduation_year"):
            self.add_error("graduation_year", "Bitiruvchi uchun bitiruv yilini ko'rsating.")
        return cleaned

    @transaction.atomic
    def save(self, commit=True):
        from students.models import StudentProfile
        user = super().save(commit=False)
        user.role = self.cleaned_data["role"]
        user.save()
        StudentProfile.objects.create(
            user=user,
            faculty=self.cleaned_data["faculty"],
            direction=self.cleaned_data["direction"],
            course=self.cleaned_data.get("course") if user.role == Role.STUDENT else None,
            graduation_year=self.cleaned_data.get("graduation_year") if user.role == Role.GRADUATE else None,
        )
        return user


class EmployerRegistrationForm(PhoneEmailCleanMixin, BootstrapFormMixin, UserCreationForm):
    name = forms.CharField(label="Tashkilot nomi", max_length=250)
    stir = forms.CharField(label="STIR", max_length=9, validators=[stir_validator])
    industry = forms.CharField(label="Faoliyat sohasi", max_length=200)
    region = forms.ChoiceField(label="Hudud", choices=Region.choices)
    address = forms.CharField(label="Manzil", max_length=300)
    org_phone = forms.CharField(label="Tashkilot telefoni", max_length=20)
    website = forms.URLField(label="Veb-sayt", required=False)
    contact_position = forms.CharField(label="Mas'ul shaxs lavozimi", max_length=150, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "last_name", "first_name", "patronymic", "email", "phone")

    field_order = ["name", "stir", "industry", "region", "address", "org_phone", "website",
                   "last_name", "first_name", "patronymic", "contact_position", "email", "phone",
                   "username", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("last_name", "first_name", "email", "phone"):
            self.fields[name].required = True
        self.fields["phone"].label = "Mas'ul shaxs telefoni"
        self.fields["last_name"].label = "Mas'ul shaxs familiyasi"
        self.fields["first_name"].label = "Mas'ul shaxs ismi"
        self.fields["email"].label = "E-mail (kirish va xabarnomalar uchun)"
        self.fields["phone"].widget.attrs["placeholder"] = "+998901234567"
        self.fields["org_phone"].widget.attrs["placeholder"] = "+998662345678"

    def clean_stir(self):
        from employers.models import Employer
        stir = self.cleaned_data["stir"].strip()
        if Employer.objects.filter(stir=stir).exists():
            raise ValidationError("Bu STIR bilan tashkilot allaqachon ro'yxatdan o'tgan.")
        return stir

    def clean_org_phone(self):
        phone = normalize_phone(self.cleaned_data["org_phone"])
        phone_validator(phone)
        return phone

    @transaction.atomic
    def save(self, commit=True):
        from employers.models import Employer
        user = super().save(commit=False)
        user.role = Role.EMPLOYER
        user.save()
        Employer.objects.create(
            user=user,
            name=self.cleaned_data["name"],
            stir=self.cleaned_data["stir"],
            industry=self.cleaned_data["industry"],
            region=self.cleaned_data["region"],
            address=self.cleaned_data["address"],
            phone=self.cleaned_data["org_phone"],
            email=user.email,
            website=self.cleaned_data.get("website", ""),
            contact_name=user.full_name,
            contact_position=self.cleaned_data.get("contact_position", ""),
            contact_phone=user.phone,
        )
        return user


class AccountForm(PhoneEmailCleanMixin, BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("last_name", "first_name", "patronymic", "email", "phone", "telegram_chat_id")
        help_texts = {"telegram_chat_id": "Telegram orqali xabarnoma olish uchun (ixtiyoriy)."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("last_name", "first_name", "email"):
            self.fields[name].required = True


class UserAdminCreateForm(PhoneEmailCleanMixin, BootstrapFormMixin, UserCreationForm):
    role = forms.ChoiceField(label="Rol", choices=[(r.value, r.label) for r in Role if r != Role.EMPLOYER])
    faculty = forms.ModelChoiceField(label="Fakultet (dekanat mas'uli uchun)", queryset=Faculty.objects.filter(is_active=True), required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "last_name", "first_name", "patronymic", "email", "phone")

    field_order = ["username", "last_name", "first_name", "patronymic", "email", "phone", "role", "faculty", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["last_name"].required = True
        self.fields["first_name"].required = True

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("role") == Role.DEAN and not cleaned.get("faculty"):
            self.add_error("faculty", "Dekanat mas'uli uchun fakultetni tanlang.")
        return cleaned

    @transaction.atomic
    def save(self, commit=True):
        from students.models import StudentProfile
        user = super().save(commit=False)
        user.role = self.cleaned_data["role"]
        user.faculty = self.cleaned_data.get("faculty") if user.role == Role.DEAN else None
        user.save()
        if user.is_candidate:
            StudentProfile.objects.get_or_create(user=user)
        return user


class UserAdminEditForm(PhoneEmailCleanMixin, BootstrapFormMixin, forms.ModelForm):
    new_password = forms.CharField(label="Yangi parol (o'zgartirish uchun)", required=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    class Meta:
        model = User
        fields = ("last_name", "first_name", "patronymic", "email", "phone", "role", "faculty", "is_active")

    def __init__(self, *args, current_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = current_user
        has_employer = hasattr(self.instance, "employer") if self.instance.pk else False
        self.fields["role"].choices = [(r.value, r.label) for r in Role if r != Role.EMPLOYER or has_employer]
        self.fields["email"].required = True
        self.self_edit = bool(current_user and self.instance.pk == current_user.pk)
        if self.self_edit:
            for name in ("role", "is_active", "faculty"):
                self.fields[name].disabled = True

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("role") == Role.DEAN and not cleaned.get("faculty"):
            self.add_error("faculty", "Dekanat mas'uli uchun fakultetni tanlang.")
        pwd = cleaned.get("new_password")
        if pwd:
            try:
                password_validation.validate_password(pwd, self.instance)
            except ValidationError as e:
                self.add_error("new_password", e)
        return cleaned

    @transaction.atomic
    def save(self, commit=True):
        from students.models import StudentProfile
        user = super().save(commit=False)
        if user.role != Role.DEAN:
            user.faculty = None
        if self.cleaned_data.get("new_password"):
            user.set_password(self.cleaned_data["new_password"])
        user.save()
        if user.is_candidate:
            StudentProfile.objects.get_or_create(user=user)
        return user


class StyledPasswordChangeForm(BootstrapFormMixin, PasswordChangeForm):
    pass


class StyledPasswordResetForm(BootstrapFormMixin, PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = "E-mail"
        self.fields["email"].widget.attrs["placeholder"] = "siz@example.uz"


class StyledSetPasswordForm(BootstrapFormMixin, SetPasswordForm):
    pass
