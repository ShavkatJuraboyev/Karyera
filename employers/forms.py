from django import forms
from django.core.exceptions import ValidationError

from core.forms import BootstrapFormMixin
from core.validators import normalize_phone, phone_validator
from employers.models import Employer


class EmployerForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Employer
        fields = ["name", "stir", "industry", "region", "address", "phone", "email", "website",
                  "contact_name", "contact_position", "contact_phone", "description", "logo"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def _clean_phone(self, name):
        phone = normalize_phone(self.cleaned_data.get(name))
        phone_validator(phone)
        return phone

    def clean_phone(self):
        return self._clean_phone("phone")

    def clean_contact_phone(self):
        return self._clean_phone("contact_phone")


class EmployerModerationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Employer
        fields = ["status", "status_comment", "cooperation"]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") in (Employer.Status.REJECTED, Employer.Status.BLOCKED) and not cleaned.get("status_comment"):
            self.add_error("status_comment", "Rad etish yoki bloklash sababini ko'rsating.")
        return cleaned
