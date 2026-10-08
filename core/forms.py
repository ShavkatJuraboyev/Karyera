from django import forms


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format="%Y-%m-%d")


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format="%Y-%m-%dT%H:%M")


class BootstrapFormMixin:
    """Barcha forma maydonlariga Bootstrap 5 klasslarini qo'shadi."""

    PHONE_FIELDS = ("phone", "contact_phone", "org_phone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Telefon raqami bo'shliq/tire bilan kiritilishi mumkin: uzunlik normallashtirilgandan so'ng tekshiriladi
        for name in self.PHONE_FIELDS:
            field = self.fields.get(name)
            if field is not None:
                field.max_length = None
                field.validators = [v for v in field.validators if v.__class__.__name__ != "MaxLengthValidator"]
                field.widget.attrs.pop("maxlength", None)
        labels = {"username": "Login", "password": "Parol", "password1": "Parol", "password2": "Parolni tasdiqlang",
                  "first_name": "Ism", "last_name": "Familiya", "email": "E-mail",
                  "old_password": "Joriy parol", "new_password1": "Yangi parol", "new_password2": "Yangi parolni tasdiqlang"}
        for name, label in labels.items():
            if name in self.fields:
                self.fields[name].label = label
        username = self.fields.get("username")
        if username is not None and username.help_text:
            username.help_text = "Harflar, raqamlar va @ . + - _ belgilari. 150 tagacha belgi."
        for field in self.fields.values():
            widget = field.widget
            css = widget.attrs.get("class", "")
            if isinstance(widget, forms.CheckboxInput):
                css += " form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css += " form-select"
            elif isinstance(widget, forms.RadioSelect):
                pass
            else:
                css += " form-control"
            widget.attrs["class"] = css.strip()
