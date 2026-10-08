from django import forms

from accounts.models import Direction, Faculty
from core.forms import BootstrapFormMixin
from core.models import News


class FacultyForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Faculty
        fields = ["name", "code", "is_active"]


class DirectionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Direction
        fields = ["faculty", "name", "code", "is_active"]


class NewsForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = News
        fields = ["title", "category", "body", "image", "is_published", "is_pinned"]
        widgets = {"body": forms.Textarea(attrs={"rows": 8})}
