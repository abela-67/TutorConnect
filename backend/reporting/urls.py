from django.urls import path

from .views import ReportsView, StatsView

urlpatterns = [
    path("admin/stats/", StatsView.as_view(), name="admin-stats"),
    path("admin/reports/", ReportsView.as_view(), name="admin-reports"),
]
