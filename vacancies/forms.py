from django import forms
from django.utils import timezone

from accounts.models import Direction
from core.forms import BootstrapFormMixin, DateInput, DateTimeInput
from vacancies.models import Application, Vacancy


class DirectionChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.faculty.name} — {obj.name}"


class VacancyForm(BootstrapFormMixin, forms.ModelForm):
    directions = DirectionChoiceField(
        label="Mos ta'lim yo'nalishlari", required=False,
        queryset=Direction.objects.filter(is_active=True).select_related("faculty"),
        widget=forms.SelectMultiple(attrs={"size": 8}),
        help_text="Bo'sh qoldirilsa — barcha yo'nalishlar uchun. Bir nechtasini tanlash uchun Ctrl (⌘) tugmasini bosib turing.",
    )

    class Meta:
        model = Vacancy
        fields = ["title", "region", "employment_type", "salary_min", "salary_max", "schedule", "deadline",
                  "directions", "requirements", "duties"]
        widgets = {
            "deadline": DateInput(),
            "requirements": forms.Textarea(attrs={"rows": 5}),
            "duties": forms.Textarea(attrs={"rows": 5}),
        }
        help_texts = {"salary_min": "Bo'sh qoldirilsa — «Kelishiladi»", "schedule": "Masalan: Du–Ju, 09:00–18:00"}

    def clean_deadline(self):
        deadline = self.cleaned_data["deadline"]
        changed = not self.instance.pk or deadline != self.instance.deadline
        if changed and deadline < timezone.localdate():
            raise forms.ValidationError("Murojaat muddati o'tgan sana bo'lishi mumkin emas.")
        return deadline

    def clean(self):
        cleaned = super().clean()
        lo, hi = cleaned.get("salary_min"), cleaned.get("salary_max")
        if lo and hi and hi < lo:
            self.add_error("salary_max", "Ish haqining yuqori chegarasi quyi chegaradan kam bo'lishi mumkin emas.")
        return cleaned


class ApplyForm(BootstrapFormMixin, forms.Form):
    cover_letter = forms.CharField(label="Qo'shimcha xat (ixtiyoriy)", max_length=2000, required=False,
                                   widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Nima uchun aynan sizni tanlashlari kerak?"}))


class ApplicationStatusForm(BootstrapFormMixin, forms.Form):
    STATUS_CHOICES = [(s.value, s.label) for s in (Application.Status.REVIEWING, Application.Status.INTERVIEW,
                                                   Application.Status.ACCEPTED, Application.Status.REJECTED)]
    status = forms.ChoiceField(label="Yangi holat", choices=STATUS_CHOICES)
    interview_at = forms.DateTimeField(label="Suhbat vaqti", required=False, widget=DateTimeInput())
    interview_place = forms.CharField(label="Suhbat joyi yoki havolasi", max_length=250, required=False)
    employer_comment = forms.CharField(label="Nomzod uchun izoh", max_length=500, required=False,
                                       widget=forms.Textarea(attrs={"rows": 3}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") == Application.Status.INTERVIEW and not cleaned.get("interview_at"):
            self.add_error("interview_at", "Suhbat vaqtini ko'rsating.")
        return cleaned


class ModerationForm(BootstrapFormMixin, forms.Form):
    DECISIONS = [("publish", "E'lon qilish (tasdiqlash)"), ("reject", "Rad etish"), ("close", "Yopish")]
    decision = forms.ChoiceField(label="Qaror", choices=DECISIONS)
    comment = forms.CharField(label="Izoh", max_length=300, required=False)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("decision") == "reject" and not cleaned.get("comment"):
            self.add_error("comment", "Rad etish sababini yozing.")
        return cleaned
