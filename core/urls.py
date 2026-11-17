# =============================================================================
# FILE: core/urls.py
# WHAT IS HERE: URLs for public pages: home, track, ward ranking, dashboard.
# =============================================================================
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("track/", views.track, name="track"),
    path("leaderboard/", views.leaderboard, name="leaderboard"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("sw.js", views.service_worker, name="sw"),
]
