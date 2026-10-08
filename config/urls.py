from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

admin.site.site_header = "Karyera SIES — Administrator paneli"
admin.site.site_title = "Karyera SIES"
admin.site.index_title = "Boshqaruv"

handler403 = "core.views.handler403"
handler404 = "core.views.handler404"
handler500 = "core.views.handler500"

urlpatterns = [
    # Ommaviy media (yangilik rasmlari, tashkilot logotiplari). Shaxsiy fayllar (sertifikat, portfolio, rasm)
    # faqat ruxsat tekshiruvi orqali beriladi — students:file.
    re_path(r"^media/(?P<path>(?:news|employers)/.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    path("admin/", admin.site.urls),
    path("hisob/", include("accounts.urls")),
    path("api/v1/", include("api.urls")),
    path("", include("core.urls")),
    path("", include("students.urls")),
    path("", include("employers.urls")),
    path("", include("vacancies.urls")),
    path("", include("events.urls")),
    path("", include("reports.urls")),
]
