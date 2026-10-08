from django.urls import path

from employers import views

app_name = "employers"

urlpatterns = [
    path("ish-beruvchi/", views.dashboard, name="dashboard"),
    path("ish-beruvchi/profil/", views.profile_edit, name="profile_edit"),
    path("ish-beruvchilar/", views.public_list, name="public_list"),
    path("ish-beruvchilar/<int:pk>/", views.public_detail, name="public_detail"),
    path("boshqaruv/ish-beruvchilar/", views.manage_list, name="manage_list"),
    path("boshqaruv/ish-beruvchilar/<int:pk>/", views.manage_detail, name="manage_detail"),
]
