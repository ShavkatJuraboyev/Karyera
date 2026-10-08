# Karyera — axborot tizimi

Samarqand iqtisodiyot va servis instituti Karyera markazi uchun Django asosidagi veb-platforma
(texnik topshiriq: «Karyera SIES» axborot tizimini ishlab chiqish).

Texnologiyalar: Python 3.10+, Django 5, Django REST Framework, Bootstrap 5, Chart.js, openpyxl (Excel), reportlab (PDF).

## 1. Tezkor ishga tushirish (lokal)

```bash
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt     # psycopg2 faqat PostgreSQL uchun kerak

python manage.py migrate
python manage.py createsuperuser    # birinchi administrator (roli avtomatik "Administrator")
python manage.py seed_demo          # (ixtiyoriy) demo ma'lumotlar
python manage.py runserver
```

Brauzerda: http://127.0.0.1:8000/

Demo foydalanuvchilar (`seed_demo` dan keyin, parol hammasiga **Demo12345!**):
`admin`, `staff`, `dean`, `rector`, `employer1`..`employer5`, `student1`..`student40`.

> Internet kerak: Bootstrap, ikonkalar va Chart.js CDN orqali yuklanadi.

## 2. Testlar

```bash
python manage.py test        # 64 ta avtomatik test
```

## 3. Foydalanuvchi rollari (TZ 3-bo'lim)

| Rol | Imkoniyatlar |
|---|---|
| Talaba / Bitiruvchi | profil, CV (PDF), vakansiya qidirish, ariza topshirish/bekor qilish, tadbirga yozilish, bandlik holatini yangilash |
| Ish beruvchi | tashkilot profili, vakansiya yaratish (moderatsiyaga yuborish), arizalarni ko'rish, holatni o'zgartirish, suhbatga taklif |
| Karyera markazi xodimi | vakansiyalar moderatsiyasi, ish beruvchilarni tasdiqlash, tadbirlar, yangiliklar, fakultet/yo'nalishlar, monitoring, hisobotlar |
| Fakultet/dekanat mas'uli | **faqat o'z fakulteti** bo'yicha monitoring, dashboard va hisobotlar |
| Rahbariyat | umumiy dashboard, monitoring va hisobotlar (faqat o'qish) |
| Administrator | yuqoridagilar + foydalanuvchilar/rollar, audit jurnali, Django admin |

Karyera xodimi, dekan, rahbar va administrator hisoblarini **Administrator** yaratadi:
«Boshqaruv → Foydalanuvchilar va rollar». Dekan uchun fakultet ko'rsatilishi shart.

## 4. Asosiy sahifalar

- `/` bosh sahifa, `/vakansiyalar/`, `/ish-beruvchilar/`, `/tadbirlar/`, `/yangiliklar/`
- `/hisob/kirish/`, `/hisob/royxatdan-otish/`, `/hisob/royxatdan-otish/ish-beruvchi/`
- Talaba: `/kabinet/profil/`, `/kabinet/cv/`, `/kabinet/arizalar/`, `/kabinet/tadbirlarim/`
- Ish beruvchi: `/ish-beruvchi/`, `/ish-beruvchi/vakansiyalar/`, `/ish-beruvchi/arizalar/`
- Markaz: `/boshqaruv/vakansiyalar/`, `/boshqaruv/ish-beruvchilar/`, `/boshqaruv/tadbirlar/`, `/boshqaruv/yangiliklar/`, `/boshqaruv/fakultetlar/`, `/boshqaruv/yonalishlar/`
- Tahlil: `/dashboard/`, `/monitoring/`, `/hisobotlar/` (Excel/PDF eksport)
- Administrator: `/hisob/foydalanuvchilar/`, `/boshqaruv/audit/`, `/admin/`
- Monitoring: `/health/` (server holati, DB tekshiruvi bilan)

## 5. Jarayonlar

**Vakansiya:** Ish beruvchi yaratadi → *Moderatsiyada* → Markaz xodimi *e'lon qiladi* yoki sabab bilan *rad etadi* →
e'lon qilinganda mos yo'nalishdagi talabalarga bildirishnoma boradi. E'lon qilingan vakansiya o'zgartirilsa, qayta moderatsiyadan o'tadi.
Murojaat muddati o'tgan vakansiyalar ro'yxatda ko'rinmaydi va ariza qabul qilmaydi.
Tasdiqlanmagan (yoki bloklangan) ish beruvchining vakansiyalari ommaga ko'rinmaydi.

**Ariza holatlari:** Yuborildi → Ko'rib chiqilmoqda → Suhbatga taklif qilindi (vaqt va joy bilan) → Qabul qilindi / Rad etildi;
talaba arizani *Bekor qilishi* va qayta topshirishi mumkin. Har bir o'zgarishda talabaga bildirishnoma (tizim ichida + e-mail + ixtiyoriy Telegram) yuboriladi.

**Ish beruvchi:** ro'yxatdan o'tgach *Tasdiqlanishi kutilmoqda* holatida bo'ladi; Markaz xodimi tasdiqlaydi/rad etadi/bloklaydi va hamkorlik holatini belgilaydi.

## 6. Hisobotlar (TZ 9-bo'lim)

Bandlik holati · Fakultetlar kesimida · Yo'nalishlar kesimida · Bitiruv yillari kesimida · Ish beruvchilar va vakansiyalar ·
Arizalar statistikasi · Tadbirlar · Oy/chorak/yil dinamikasi. Hammasi filtrlanadi va **Excel (.xlsx)** hamda **PDF** ga eksport qilinadi
(eksport audit jurnaliga yoziladi). Excel'da formula inyeksiyasidan himoya qilingan.

## 7. REST API (`/api/v1/`)

| Endpoint | Tavsif |
|---|---|
| `POST /api/v1/auth/token/` | `{username, password}` → token |
| `GET /api/v1/vacancies/` (+`?search=&region=&type=&direction=&salary=&employer=`) | e'lon qilingan vakansiyalar (ochiq) |
| `GET /api/v1/events/`, `/news/`, `/faculties/`, `/directions/` | ochiq ma'lumotnomalar |
| `POST /api/v1/events/{id}/register/` · `/cancel/` | tadbirga yozilish |
| `GET/PATCH /api/v1/me/` | foydalanuvchi va profil |
| `GET/POST /api/v1/applications/` · `POST .../{id}/withdraw/` · `POST .../{id}/set-status/` | arizalar (talaba — o'zinikilari, ish beruvchi — o'z vakansiyalariniki) |
| `GET /api/v1/stats/` | dashboard ko'rsatkichlari (faqat tahlil rollari) |

Avtorizatsiya: `Authorization: Token <token>`. So'rovlar chastotasi cheklangan (throttling).

## 8. Xavfsizlik (TZ 12-bo'lim)

- Parollar PBKDF2 bilan saqlanadi, parol murakkabligi tekshiriladi, parolni e-mail orqali tiklash mavjud.
- Rollarga asoslangan kirish: har bir view'da rol tekshiriladi; ish beruvchi faqat o'z ma'lumotlarini, dekan faqat o'z fakultetini ko'radi.
- Brute-force himoyasi: 5 ta xato urinishdan so'ng 15 daqiqa blok (veb va API uchun).
- Administrator sessiyasi 30 daqiqa (boshqalar — 8 soat).
- CSRF himoyasi, logout faqat POST, `X-Frame-Options: DENY`, XSS'dan avtomatik escape.
- Shaxsiy fayllar (sertifikat, portfolio, rasm) faqat vakolatli foydalanuvchilarga beriladi; yuklash hajmi (5 MB) va kengaytma tekshiriladi.
- **Audit jurnali** (`/boshqaruv/audit/`): kirish/chiqish, xato kirishlar, vakansiya yaratish/o'zgartirish/o'chirish/holati,
  rol va huquq o'zgarishi, eksportlar, ariza amallari, ma'lumot o'zgartirish/o'chirish. Django adminda faqat o'qish mumkin.
- Production'da `DJANGO_DEBUG=0` bo'lsa HTTPS yo'naltirish, xavfsiz cookie va HSTS avtomatik yoqiladi.

## 9. Production'ga joylash

1. `.env.example` dagi o'zgaruvchilarni server muhitiga o'rnating (`DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DB_*`, `EMAIL_*`).
2. PostgreSQL tavsiya etiladi (`DB_NAME` berilsa avtomatik ulanadi).
3. `python manage.py migrate && python manage.py collectstatic --noinput`
4. `gunicorn config.wsgi:application --workers 3 --bind 127.0.0.1:8000` (nginx orqali HTTPS bilan).
5. nginx'da `/media/` ni to'g'ridan-to'g'ri `MEDIA_ROOT` dan bering (maxfiy fayllar Django orqali beriladi — `/fayl/...`).
   **Muhim:** `media/students/` papkasini nginx orqali ochmang.
6. Zaxira (cron): `0 2 * * * /path/venv/bin/python /path/manage.py backup_db --media`
   (SQLite — ichki backup API, PostgreSQL — `pg_dump`; oxirgi 14 nusxa saqlanadi, `BACKUP_KEEP` bilan o'zgartiring).
7. Jurnallar `logs/karyera.log` va `logs/errors.log` (aylanuvchi fayllar); `/health/` ni monitoring tizimiga ulang.

## 10. Integratsiyalar (TZ 10-bo'lim)

- **REST API** — uchinchi tomon tizimlari uchun tayyor (yuqorida).
- **HEMIS / mavjud tizim:** `python manage.py import_students fayl.csv [--dry-run]` — CSV orqali talaba/bitiruvchilarni
  yaratadi yoki yangilaydi (`external_id` bo'yicha). Parol o'rnatilmaydi; foydalanuvchi «Parolni unutdingizmi?» orqali o'zi o'rnatadi.
- **E-mail:** `EMAIL_*` o'zgaruvchilari bilan SMTP ulanadi. **Telegram:** `TELEGRAM_BOT_TOKEN` o'rnatilsa va foydalanuvchi
  «Shaxsiy ma'lumotlar»da chat ID kiritsa, bildirishnomalar Telegramga ham yuboriladi.
- Aniq xizmat nuqtalari ma'lum bo'lmagani uchun `career.edu.uz` va SMS-shlyuz bilan jonli ulanish yozilmagan;
  `core/services.py` dagi `notify()` va API shu ulanishlar uchun kengaytirish nuqtasi.

## 11. Loyiha tuzilmasi

```
config/      sozlamalar, asosiy url'lar
accounts/    foydalanuvchi, rollar, fakultet/yo'nalish, kirish/ro'yxatdan o'tish, rollarni boshqarish
core/        yangiliklar, bildirishnomalar, audit, umumiy CRUD, eksport (Excel/PDF), buyruqlar
students/    profil, CV (PDF), ko'nikma/til/sertifikat/tajriba/portfolio, monitoring
employers/   ish beruvchi kabineti va bazasi
vacancies/   vakansiyalar, moderatsiya, arizalar (biznes qoidalari: services.py)
events/      tadbirlar, ro'yxatdan o'tish, qatnashuv
reports/     dashboard, hisobotlar
api/         REST API
templates/ static/
```
