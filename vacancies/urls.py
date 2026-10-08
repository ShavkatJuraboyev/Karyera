from django.urls import path

from vacancies import views

app_name = "vacancies"

urlpatterns = [
    path("vakansiyalar/", views.vacancy_list, name="list"),
    path("vakansiyalar/<int:pk>/", views.vacancy_detail, name="detail"),
    path("vakansiyalar/<int:pk>/ariza/", views.apply, name="apply"),
    path("kabinet/arizalar/", views.my_applications, name="my_applications"),
    path("kabinet/arizalar/<int:pk>/bekor/", views.withdraw, name="withdraw"),
    path("ish-beruvchi/vakansiyalar/", views.employer_vacancies, name="employer_list"),
    path("ish-beruvchi/vakansiyalar/yangi/", views.employer_vacancy_form, name="employer_create"),
    path("ish-beruvchi/vakansiyalar/<int:pk>/tahrirlash/", views.employer_vacancy_form, name="employer_edit"),
    path("ish-beruvchi/vakansiyalar/<int:pk>/yopish/", views.employer_vacancy_close, name="employer_close"),
    path("ish-beruvchi/vakansiyalar/<int:pk>/ochirish/", views.employer_vacancy_delete, name="employer_delete"),
    path("ish-beruvchi/vakansiyalar/<int:pk>/arizalar/", views.employer_vacancy_applications, name="employer_vacancy_applications"),
    path("ish-beruvchi/arizalar/", views.employer_applications_all, name="employer_applications"),
    path("ish-beruvchi/arizalar/<int:pk>/", views.employer_application_detail, name="employer_application"),
    path("boshqaruv/vakansiyalar/", views.manage_list, name="manage_list"),
    path("boshqaruv/vakansiyalar/<int:pk>/", views.manage_detail, name="manage_detail"),
]
