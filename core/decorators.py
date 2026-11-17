# =============================================================================
# FILE: core/decorators.py
# WHAT IS HERE: ROLE-BASED ACCESS. @citizen_required and @admin_required protect pages.
# VIVA TIP: "Admin pages use @admin_required from core/decorators.py — a citizen gets a 403 'not allowed' page."
# =============================================================================
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.urls import reverse


# Not logged in -> send to the right login page. Wrong role -> 403 page. Right role -> open the page.
def role_required(role):
    """Signed-in users with this role only. Signed-out visitors go to the matching sign-in page
    (admins to /admin/, citizens to the normal login); a wrong role gets the 403 page."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                login_url = reverse("admin_login") if role == "ADMIN" else reverse("accounts:login")
                return redirect_to_login(request.get_full_path(), login_url)
            if request.user.role != role:
                raise PermissionDenied("This page is not available for your account.")
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


# Ready-made decorators used on the views.
citizen_required = role_required("USER")
admin_required = role_required("ADMIN")
