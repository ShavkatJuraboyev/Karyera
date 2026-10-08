from django.urls import path

from students import views

app_name = "students"

urlpatterns = [
    path("kabinet/profil/", views.profile, name="profile"),
    path("kabinet/profil/tahrirlash/", views.profile_edit, name="profile_edit"),
    path("kabinet/profil/<str:section>/qoshish/", views.section_form, name="section_add"),
    path("kabinet/profil/<str:section>/<int:pk>/tahrirlash/", views.section_form, name="section_edit"),
    path("kabinet/profil/<str:section>/<int:pk>/ochirish/", views.section_delete, name="section_delete"),
    path("kabinet/cv/", views.cv_view, name="cv"),
    path("kabinet/cv/pdf/", views.cv_pdf, name="cv_pdf"),
    path("nomzod/<int:pk>/cv/", views.cv_view_other, name="cv_other"),
    path("nomzod/<int:pk>/cv/pdf/", views.cv_pdf_other, name="cv_pdf_other"),
    path("fayl/<str:kind>/<int:pk>/", views.protected_file, name="file"),
    path("monitoring/", views.monitor_list, name="monitor_list"),
    path("monitoring/<int:pk>/", views.monitor_detail, name="monitor_detail"),
    path("monitoring/<int:pk>/tahrirlash/", views.monitor_edit, name="monitor_edit"),
]
