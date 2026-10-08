from django import forms

from core.forms import BootstrapFormMixin, DateTimeInput
from employers.models import Employer
from events.models import Event


class EventForm(BootstrapFormMixin, forms.ModelForm):
    employers = forms.ModelMultipleChoiceField(
        label="Ishtirok etuvchi ish beruvchilar", required=False,
        queryset=Employer.objects.filter(status=Employer.Status.APPROVED),
        widget=forms.SelectMultiple(attrs={"size": 6}),
    )

    class Meta:
        model = Event
        fields = ["title", "event_type", "description", "location", "start_at", "end_at", "capacity", "employers", "is_published"]
        widgets = {
            "start_at": DateTimeInput(), "end_at": DateTimeInput(),
            "description": forms.Textarea(attrs={"rows": 5}),
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_at"), cleaned.get("end_at")
        if start and end and end <= start:
            self.add_error("end_at", "Tugash vaqti boshlanish vaqtidan keyin bo'lishi kerak.")
        capacity = cleaned.get("capacity")
        if capacity is not None and self.instance.pk and capacity < self.instance.registered_count:
            self.add_error("capacity", f"Hozirgacha {self.instance.registered_count} kishi ro'yxatdan o'tgan, cheklov bundan kam bo'lishi mumkin emas.")
        return cleaned
