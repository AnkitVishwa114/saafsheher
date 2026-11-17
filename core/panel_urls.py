# =============================================================================
# FILE: core/panel_urls.py
# WHAT IS HERE: URLs for the admin panel (/admin-panel/...).
# =============================================================================
from django.urls import path

from . import panel

app_name = "panel"

urlpatterns = [
    path("", panel.dashboard, name="dashboard"),
    path("complaints/", panel.complaints, name="complaints"),
    path("complaints/export/", panel.export_csv, name="export"),
    path("complaints/<str:code>/", panel.complaint, name="complaint"),
    path("wards/", panel.wards, name="wards"),
    path("wards/<int:pk>/", panel.wards, name="ward_edit"),
    path("categories/", panel.categories, name="categories"),
    path("categories/<int:pk>/", panel.categories, name="category_edit"),
    path("citizens/", panel.users, name="users"),
    path("citizens/<int:pk>/toggle/", panel.user_toggle, name="user_toggle"),
]
