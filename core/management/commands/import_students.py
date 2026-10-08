"""HEMIS yoki boshqa tizimdan olingan CSV fayl orqali talaba/bitiruvchilarni import qiladi.

CSV ustunlari (UTF-8, vergul bilan): external_id, last_name, first_name, patronymic,
faculty, direction, course, graduation_year, phone, email

Foydalanuvchiga login = external_id beriladi, parol o'rnatilmaydi (parolni «Parolni unutdingizmi?»
orqali e-mail bilan o'rnatadi). Mavjud external_id yangilanadi.
"""
import csv

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Direction, Faculty, Role, User
from core.validators import normalize_phone
from students.models import StudentProfile


class Command(BaseCommand):
    help = "CSV fayldan talaba va bitiruvchilarni import qilish"

    def add_arguments(self, parser):
        parser.add_argument("csv_file")
        parser.add_argument("--dry-run", action="store_true", help="Faqat tekshirish, saqlamaslik")

    def handle(self, *args, **opts):
        try:
            f = open(opts["csv_file"], newline="", encoding="utf-8-sig")
        except OSError as exc:
            raise CommandError(str(exc))
        created = updated = errors = 0
        with f, transaction.atomic():
            for line_no, row in enumerate(csv.DictReader(f), start=2):
                try:
                    c, u = self._import_row(row)
                    created += c
                    updated += u
                except Exception as exc:
                    errors += 1
                    self.stderr.write(f"{line_no}-qator: {exc}")
            if opts["dry_run"]:
                transaction.set_rollback(True)
        self.stdout.write(self.style.SUCCESS(f"Yaratildi: {created}, yangilandi: {updated}, xatolar: {errors}"
                                             + (" (dry-run: saqlanmadi)" if opts["dry_run"] else "")))

    def _import_row(self, row):
        ext = (row.get("external_id") or "").strip()
        if not ext:
            raise ValueError("external_id ko'rsatilmagan")
        faculty = Faculty.objects.get_or_create(name=(row.get("faculty") or "").strip() or "Ko'rsatilmagan")[0]
        direction_name = (row.get("direction") or "").strip()
        direction = Direction.objects.get_or_create(faculty=faculty, name=direction_name)[0] if direction_name else None
        year = (row.get("graduation_year") or "").strip()
        course = (row.get("course") or "").strip()
        role = Role.GRADUATE if year.isdigit() else Role.STUDENT
        profile = StudentProfile.objects.filter(external_id=ext).select_related("user").first()
        if profile:
            user, created = profile.user, 0
        else:
            user = User(username=ext)
            user.set_unusable_password()
            created = 1
        user.first_name = (row.get("first_name") or "").strip()[:150]
        user.last_name = (row.get("last_name") or "").strip()[:150]
        user.patronymic = (row.get("patronymic") or "").strip()[:100]
        user.email = (row.get("email") or "").strip()
        user.phone = normalize_phone(row.get("phone"))
        user.role = role
        user.full_clean(exclude=["password"])
        user.save()
        profile = profile or StudentProfile(user=user, external_id=ext)
        profile.faculty, profile.direction = faculty, direction
        profile.course = int(course) if course.isdigit() and role == Role.STUDENT else None
        profile.graduation_year = int(year) if year.isdigit() and role == Role.GRADUATE else None
        profile.full_clean(exclude=["user"])
        profile.save()
        return created, 0 if created else 1
