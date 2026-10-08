"""Ma'lumotlar bazasining zaxira nusxasini yaratadi (cron orqali avtomatik ishga tushirish mumkin).

Misol (har kuni 02:00):  0 2 * * * /path/venv/bin/python /path/manage.py backup_db
"""
import os
import shutil
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Ma'lumotlar bazasi (va ixtiyoriy media fayllar) zaxira nusxasini yaratadi."

    def add_arguments(self, parser):
        parser.add_argument("--media", action="store_true", help="Media fayllarni ham arxivlash")

    def handle(self, *args, **opts):
        backup_dir = Path(settings.BACKUP_DIR)
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db = settings.DATABASES["default"]
        engine = db["ENGINE"]

        if engine.endswith("sqlite3"):
            target = backup_dir / f"db_{stamp}.sqlite3"
            name = str(db["NAME"])
            src = sqlite3.connect(name, uri=name.startswith("file:"), timeout=30)
            dst = sqlite3.connect(str(target), timeout=30)
            with dst:
                src.backup(dst)
            src.close()
            dst.close()
        elif engine.endswith("postgresql"):
            target = backup_dir / f"db_{stamp}.sql"
            env = dict(os.environ, PGPASSWORD=db.get("PASSWORD", ""))
            cmd = ["pg_dump", "-h", db.get("HOST", "127.0.0.1"), "-p", str(db.get("PORT", "5432")),
                   "-U", db.get("USER", ""), "-f", str(target), db["NAME"]]
            try:
                subprocess.run(cmd, check=True, env=env)
            except (OSError, subprocess.CalledProcessError) as exc:
                raise CommandError(f"pg_dump bajarilmadi: {exc}")
        else:
            raise CommandError("Qo'llab-quvvatlanmaydigan ma'lumotlar bazasi.")
        self.stdout.write(self.style.SUCCESS(f"Baza zaxirasi: {target}"))

        if opts["media"] and Path(settings.MEDIA_ROOT).exists():
            archive = shutil.make_archive(str(backup_dir / f"media_{stamp}"), "gztar", settings.MEDIA_ROOT)
            self.stdout.write(self.style.SUCCESS(f"Media zaxirasi: {archive}"))

        # Eski nusxalarni tozalash
        keep = settings.BACKUP_KEEP
        for pattern in ("db_*", "media_*"):
            files = sorted(backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
            for old in files[keep:]:
                old.unlink()
