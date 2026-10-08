from django import forms

from accounts.models import Faculty
from core.forms import BootstrapFormMixin, DateInput


class ReportFilterForm(BootstrapFormMixin, forms.Form):
    faculty = forms.ModelChoiceField(label="Fakultet", queryset=Faculty.objects.filter(is_active=True), required=False, empty_label="Barchasi")
    year = forms.IntegerField(label="Bitiruv yili", required=False, min_value=1990, max_value=2100)
    date_from = forms.DateField(label="Sanadan", required=False, widget=DateInput())
    date_to = forms.DateField(label="Sanagacha", required=False, widget=DateInput())
    period = forms.ChoiceField(label="Davr", required=False, choices=[("month", "Oylar bo'yicha"), ("quarter", "Choraklar bo'yicha"), ("year", "Yillar bo'yicha")])

    def clean(self):
        cleaned = super().clean()
        a, b = cleaned.get("date_from"), cleaned.get("date_to")
        if a and b and b < a:
            self.add_error("date_to", "Tugash sanasi boshlanish sanasidan oldin bo'lishi mumkin emas.")
        return cleaned
