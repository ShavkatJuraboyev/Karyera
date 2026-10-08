from datetime import date

from django import forms

from accounts.models import Direction, Faculty, Role
from core.forms import BootstrapFormMixin, DateInput
from students.models import (Certificate, EmploymentStatus, Experience, LanguageSkill, PortfolioItem, Skill,
                             StudentProfile)

EMPLOYED_STATES = (EmploymentStatus.EMPLOYED, EmploymentStatus.SELF_EMPLOYED)


class EmploymentCleanMixin:
    """Bandlik holati bilan bog'liq maydonlarning izchilligini ta'minlaydi."""

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("employment_status")
        if status == EmploymentStatus.EMPLOYED and not cleaned.get("employer_name"):
            self.add_error("employer_name", "Ishga joylashgan tashkilot nomini kiriting.")
        if status == EmploymentStatus.EMPLOYED and not cleaned.get("position"):
            self.add_error("position", "Lavozimni kiriting.")
        faculty, direction = cleaned.get("faculty"), cleaned.get("direction")
        if faculty and direction and direction.faculty_id != faculty.pk:
            self.add_error("direction", "Tanlangan yo'nalish bu fakultetga tegishli emas.")
        return cleaned

    def apply_employment_rules(self, profile):
        if profile.employment_status in EMPLOYED_STATES:
            if not profile.employed_date:
                profile.employed_date = date.today()
        else:
            profile.employer_name = ""
            profile.position = ""
            profile.employed_date = None


class StudentProfileForm(EmploymentCleanMixin, BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ["faculty", "direction", "course", "graduation_year", "birth_date", "region", "address",
                  "desired_position", "about", "photo", "employment_status", "employer_name", "position", "employed_date"]
        widgets = {"birth_date": DateInput(), "employed_date": DateInput(), "about": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["faculty"].queryset = Faculty.objects.filter(is_active=True)
        self.fields["direction"].queryset = Direction.objects.filter(is_active=True)
        self.fields["faculty"].required = True
        self.fields["direction"].required = True
        self.fields["faculty"].widget.attrs["data-dependent-target"] = "id_direction"
        self.fields["direction"].widget.attrs["data-faculty-url"] = "/malumotnoma/yonalishlar/"
        role = self.instance.user.role if self.instance.pk else Role.STUDENT
        if role == Role.GRADUATE:
            del self.fields["course"]
        else:
            del self.fields["graduation_year"]
        self.fields["employment_status"].choices = EmploymentStatus.choices

    def clean(self):
        cleaned = super().clean()
        role = self.instance.user.role
        if role == Role.STUDENT and "course" in self.fields and not cleaned.get("course"):
            self.add_error("course", "Kursni ko'rsating.")
        if role == Role.GRADUATE and "graduation_year" in self.fields and not cleaned.get("graduation_year"):
            self.add_error("graduation_year", "Bitiruv yilini ko'rsating.")
        return cleaned

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.apply_employment_rules(profile)
        if commit:
            profile.save()
        return profile


class MonitoringForm(EmploymentCleanMixin, BootstrapFormMixin, forms.ModelForm):
    """Karyera markazi xodimi uchun: bandlik monitoringi va o'quv ma'lumotlari."""

    class Meta:
        model = StudentProfile
        fields = ["faculty", "direction", "course", "graduation_year", "employment_status", "employer_name", "position", "employed_date"]
        widgets = {"employed_date": DateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["faculty"].widget.attrs["data-dependent-target"] = "id_direction"
        self.fields["direction"].widget.attrs["data-faculty-url"] = "/malumotnoma/yonalishlar/"

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.apply_employment_rules(profile)
        if commit:
            profile.save()
        return profile


class SkillForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Skill
        fields = ["name", "level"]


class LanguageForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = LanguageSkill
        fields = ["language", "level"]


class CertificateForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Certificate
        fields = ["title", "issuer", "issue_date", "file"]
        widgets = {"issue_date": DateInput()}


class ExperienceForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Experience
        fields = ["company", "position", "start_date", "end_date", "description"]
        widgets = {"start_date": DateInput(), "end_date": DateInput(), "description": forms.Textarea(attrs={"rows": 3})}

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "Tugash sanasi boshlanish sanasidan oldin bo'lishi mumkin emas.")
        return cleaned


class PortfolioForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = PortfolioItem
        fields = ["title", "description", "url", "file"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


SECTIONS = {
    "skills": {"model": Skill, "form": SkillForm, "title": "Ko'nikma", "multipart": False},
    "languages": {"model": LanguageSkill, "form": LanguageForm, "title": "Til bilimi", "multipart": False},
    "certificates": {"model": Certificate, "form": CertificateForm, "title": "Sertifikat", "multipart": True},
    "experiences": {"model": Experience, "form": ExperienceForm, "title": "Ish tajribasi", "multipart": False},
    "portfolio": {"model": PortfolioItem, "form": PortfolioForm, "title": "Portfolio", "multipart": True},
}
