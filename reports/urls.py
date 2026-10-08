from django.urls import path

from reports import views

app_name = "reports"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("hisobotlar/", views.report_index, name="index"),
    path("hisobotlar/<slug:key>/", views.report_view, name="report"),
]
