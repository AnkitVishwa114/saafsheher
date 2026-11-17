# =============================================================================
# FILE: saafshehar/urls.py
# WHAT IS HERE: the main URL map of the website. Each line sends a URL prefix to an app.
# VIVA TIP: "/admin/ is the admin login, /admin-panel/ is the admin panel, /complaints/ is the citizen side."
# =============================================================================
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from accounts.views import admin_login

# /admin/        -> admin login page (accounts/views.py -> admin_login)
# /django-admin/ -> Django's built-in admin
# ''             -> public pages (core/urls.py)
# /accounts/     -> citizen login, sign-up, profile (accounts/urls.py)
# /complaints/   -> citizen complaint pages (complaints/urls.py)
# /admin-panel/  -> municipal admin panel (core/panel_urls.py)
urlpatterns = [
    path("admin/", admin_login, name="admin_login"),
    path("django-admin/", admin.site.urls),
    path("", include("core.urls")),
    path("accounts/", include("accounts.urls")),
    path("complaints/", include("complaints.urls")),
    path("admin-panel/", include("core.panel_urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "core.views.error_404"
handler403 = "core.views.error_403"
handler500 = "core.views.error_500"
