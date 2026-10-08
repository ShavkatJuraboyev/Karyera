"""Tizimni sinab ko'rish uchun demo ma'lumotlar yaratadi. Faqat DEBUG rejimida yoki --force bilan."""
import random
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import Direction, Faculty, Region, Role, User
from core.models import News
from employers.models import Employer
from events.models import Event, EventRegistration
from students.models import EmploymentStatus, Experience, LanguageSkill, Skill, StudentProfile
from vacancies.models import Application, Vacancy

PASSWORD = "Demo12345!"

STRUCTURE = {
    "Iqtisodiyot fakulteti": ["Iqtisodiyot (tarmoqlar va sohalar bo'yicha)", "Buxgalteriya hisobi va audit", "Bank ishi va audit"],
    "Servis va turizm fakulteti": ["Turizm va mehmondo'stlik", "Xizmat ko'rsatish sohasi menejmenti", "Gastronomiya"],
    "Axborot texnologiyalari fakulteti": ["Axborot tizimlari va texnologiyalari", "Dasturiy injiniring", "Raqamli iqtisodiyot"],
    "Menejment va marketing fakulteti": ["Menejment", "Marketing", "Logistika"],
}
FIRST = ["Aziz", "Dilshod", "Nodira", "Malika", "Sardor", "Jasur", "Madina", "Shahzod", "Zilola", "Bekzod", "Gulnora", "Otabek", "Sevara", "Rustam", "Laylo"]
LAST = ["Karimov", "Rahimova", "Tursunov", "Xolmatova", "Yusupov", "Ergashev", "Abdullayeva", "Saidov", "Nazarova", "Qodirov"]
EMPLOYERS = [("Samarqand Bank", "Moliya va bank", "100000001"), ("SamTech Solutions", "Axborot texnologiyalari", "100000002"),
             ("Registon Hotel Group", "Turizm va mehmondo'stlik", "100000003"), ("Zarafshon Logistics", "Logistika va transport", "100000004"),
             ("Silk Road Audit", "Audit va konsalting", "100000005")]


class Command(BaseCommand):
    help = "Demo ma'lumotlarni yaratish"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        if not settings.DEBUG and not opts["force"]:
            raise CommandError("Production rejimida demo ma'lumot yaratilmaydi (--force bilan majburlash mumkin).")
        random.seed(7)
        faculties = {}
        directions = []
        for fname, dirs in STRUCTURE.items():
            f, _ = Faculty.objects.get_or_create(name=fname, defaults={"code": fname[:3].upper()})
            faculties[fname] = f
            for dname in dirs:
                d, _ = Direction.objects.get_or_create(faculty=f, name=dname)
                directions.append(d)

        def mk_user(username, role, first, last, faculty=None, email=None):
            u, created = User.objects.get_or_create(username=username, defaults={
                "role": role, "first_name": first, "last_name": last, "faculty": faculty,
                "email": email or f"{username}@example.uz", "phone": "+998901234567"})
            if created:
                u.set_password(PASSWORD)
                u.save()
            return u

        mk_user("admin", Role.ADMIN, "Administrator", "Tizim")
        mk_user("staff", Role.STAFF, "Karyera", "Xodimi")
        mk_user("dean", Role.DEAN, "Dekan", "Mas'uli", faculty=faculties["Iqtisodiyot fakulteti"])
        mk_user("rector", Role.MANAGEMENT, "Rahbar", "Institut")

        employers = []
        for i, (name, industry, stir) in enumerate(EMPLOYERS):
            u = mk_user(f"employer{i + 1}", Role.EMPLOYER, "Mas'ul", f"Shaxs{i + 1}")
            e, _ = Employer.objects.get_or_create(user=u, defaults={
                "name": name, "stir": stir, "industry": industry, "region": Region.SAMARKAND.value, "address": "Samarqand sh., Registon ko'chasi 1",
                "phone": "+998662345678", "email": u.email, "contact_name": u.full_name, "contact_phone": "+998901234567",
                "status": Employer.Status.APPROVED if i < 4 else Employer.Status.PENDING,
                "cooperation": Employer.Cooperation.PARTNER if i < 2 else Employer.Cooperation.NONE,
                "description": f"{name} — {industry} sohasidagi yetakchi tashkilot."})
            employers.append(e)

        titles = ["Buxgalter", "Dasturchi (Python/Django)", "Marketing mutaxassisi", "Mehmonxona administratori", "Logist", "Kredit mutaxassisi", "Auditor yordamchisi", "Turizm menejeri"]
        vacancies = []
        for i, title in enumerate(titles):
            emp = employers[i % 4]
            v, _ = Vacancy.objects.get_or_create(employer=emp, title=title, defaults={
                "region": Region.SAMARKAND.value, "employment_type": random.choice(list(Vacancy.EmploymentType.values)),
                "salary_min": random.choice([3_000_000, 4_000_000, 5_000_000]), "salary_max": random.choice([7_000_000, 9_000_000, None]),
                "requirements": "Oliy ma'lumot yoki 3-kurs talabasi.\nJamoada ishlay olish.\nKompyuter savodxonligi.",
                "duties": "Rahbariyat topshiriqlarini bajarish.\nHisobotlarni tayyorlash.\nMijozlar bilan ishlash.",
                "schedule": "Du–Ju, 09:00–18:00", "deadline": timezone.localdate() + timedelta(days=random.randint(10, 60)),
                "status": Vacancy.Status.PUBLISHED if i < 6 else Vacancy.Status.PENDING,
                "published_at": timezone.now() - timedelta(days=random.randint(0, 20)) if i < 6 else None})
            if not v.directions.exists():
                v.directions.set(random.sample(directions, 2))
            vacancies.append(v)

        statuses = [EmploymentStatus.LOOKING, EmploymentStatus.EMPLOYED, EmploymentStatus.EMPLOYED, EmploymentStatus.SELF_EMPLOYED,
                    EmploymentStatus.STUDYING, EmploymentStatus.UNKNOWN]
        candidates = []
        for i in range(40):
            role = Role.GRADUATE if i % 2 == 0 else Role.STUDENT
            u = mk_user(f"student{i + 1}", role, random.choice(FIRST), random.choice(LAST))
            d = directions[i % len(directions)]
            status = random.choice(statuses) if role == Role.GRADUATE else random.choice([EmploymentStatus.LOOKING, EmploymentStatus.UNKNOWN])
            p, created = StudentProfile.objects.get_or_create(user=u, defaults={
                "faculty": d.faculty, "direction": d, "course": random.randint(1, 4) if role == Role.STUDENT else None,
                "graduation_year": random.choice([2023, 2024, 2025, 2026]) if role == Role.GRADUATE else None,
                "region": Region.SAMARKAND.value, "employment_status": status, "desired_position": "Mutaxassis",
                "about": "O'qishga va yangi bilimlarga intiluvchan mutaxassis."})
            if created:
                if status in (EmploymentStatus.EMPLOYED, EmploymentStatus.SELF_EMPLOYED):
                    p.employer_name = random.choice(EMPLOYERS)[0] if status == EmploymentStatus.EMPLOYED else "Yakka tartibdagi tadbirkor"
                    p.position = "Mutaxassis"
                    p.employed_date = timezone.localdate() - timedelta(days=random.randint(5, 330))
                    p.save()
                Skill.objects.create(profile=p, name=random.choice(["Excel", "Python", "Ingliz tili", "Muloqot", "1C Buxgalteriya"]), level=2)
                LanguageSkill.objects.create(profile=p, language="Ingliz tili", level="B1")
                Experience.objects.create(profile=p, company="Amaliyot", position="Stajyor", start_date=timezone.localdate() - timedelta(days=400))
            candidates.append(u)

        for u in random.sample(candidates, 14):
            v = random.choice(vacancies[:6])
            Application.objects.get_or_create(vacancy=v, applicant=u, defaults={
                "status": random.choice(list(Application.Status.values)), "cover_letter": "Vakansiyaga qiziqish bildiraman."})

        now = timezone.now()
        for title, etype, delta in [("Bahorgi mehnat yarmarkasi", Event.Type.JOB_FAIR, 15), ("CV yozish bo'yicha trening", Event.Type.TRAINING, 7),
                                    ("Samarqand Bank bilan uchrashuv", Event.Type.MEETING, 25), ("O'tgan yilgi karyera seminari", Event.Type.SEMINAR, -30)]:
            ev, created = Event.objects.get_or_create(title=title, defaults={
                "event_type": etype, "description": "Talabalar va bitiruvchilar uchun karyera tadbiri.", "location": "Institut majlislar zali",
                "start_at": now + timedelta(days=delta), "end_at": now + timedelta(days=delta, hours=3), "capacity": 100})
            if created:
                for u in random.sample(candidates, 10):
                    EventRegistration.objects.get_or_create(event=ev, user=u, defaults={"attended": delta < 0})

        for title, cat in [("Karyera SIES platformasi ishga tushdi", News.Category.IMPORTANT), ("Yangi hamkor tashkilotlar", News.Category.NEWS)]:
            News.objects.get_or_create(title=title, defaults={"category": cat, "body": "Karyera markazi yangiliklari va muhim e'lonlar shu yerda joylashtiriladi."})

        self.stdout.write(self.style.SUCCESS("Demo ma'lumotlar yaratildi."))
        self.stdout.write(f"Kirish: admin / staff / dean / rector / employer1 / student1 ... — parol: {PASSWORD}")
