from django.urls import path

from .views import DashboardView

dashboard_patterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]
