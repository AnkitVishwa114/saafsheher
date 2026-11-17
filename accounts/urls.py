# =============================================================================
# FILE: accounts/urls.py
# WHAT IS HERE: URLs for login, logout, sign-up, profile, notifications (/accounts/...).
# =============================================================================
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.signup, name="signup"),
    path("profile/", views.profile, name="profile"),
    path("notifications/", views.notifications, name="notifications"),
]
