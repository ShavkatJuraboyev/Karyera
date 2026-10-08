from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api import views

router = DefaultRouter()
router.register("vacancies", views.VacancyViewSet, basename="vacancy")
router.register("events", views.EventViewSet, basename="event")
router.register("news", views.NewsViewSet, basename="news")
router.register("applications", views.ApplicationViewSet, basename="application")
router.register("faculties", views.FacultyViewSet, basename="faculty")
router.register("directions", views.DirectionViewSet, basename="direction")

urlpatterns = [
    path("auth/token/", views.LoginTokenView.as_view(), name="token"),
    path("me/", views.MeView.as_view(), name="me"),
    path("stats/", views.StatsView.as_view(), name="stats"),
    path("", include(router.urls)),
]
