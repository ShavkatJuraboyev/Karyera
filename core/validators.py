import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, RegexValidator

phone_validator = RegexValidator(
    regex=r"^\+?\d{9,15}$",
    message="Telefon raqamini to'g'ri kiriting (masalan: +998901234567).",
)
stir_validator = RegexValidator(regex=r"^\d{9}$", message="STIR 9 ta raqamdan iborat bo'lishi kerak.")

document_extensions = FileExtensionValidator(["pdf", "doc", "docx", "jpg", "jpeg", "png"])
image_extensions = FileExtensionValidator(["jpg", "jpeg", "png", "webp"])


def validate_file_size(f):
    limit = getattr(settings, "MAX_UPLOAD_SIZE", 5 * 1024 * 1024)
    if f.size > limit:
        raise ValidationError(f"Fayl hajmi {limit // (1024 * 1024)} MB dan oshmasligi kerak.")


def normalize_phone(value):
    """Bo'sh joy, tire va qavslarni olib tashlaydi."""
    if not value:
        return ""
    return re.sub(r"[\s\-()]", "", value)
