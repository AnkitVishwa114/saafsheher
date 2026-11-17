# =============================================================================
# FILE: accounts/backends.py
# WHAT IS HERE: EMAIL LOGIN. Django normally logs in with a username; this lets users log in with email.
# VIVA TIP: "Login checks the email (any case) and password here; it is switched on in settings.py."
# =============================================================================
from django.contrib.auth.backends import ModelBackend

from .models import User


class EmailBackend(ModelBackend):
    """Sign in with email (any letter case) + password."""

    # Find the user by email, check the password, and return the user if both are right.
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = (username or kwargs.get("email") or "").strip().lower()
        if not email or not password:
            return None
        user = User.objects.filter(email=email).first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        # Run the hasher anyway so a wrong email takes as long as a wrong password.
        User().set_password(password)
        return None
