# =============================================================================
# FILE: accounts/validators.py
# WHAT IS HERE: field VALIDATION rules — phone number, PIN code, name and strong password.
# VIVA TIP: "Phone must start with 6-9 and be 10 digits; password needs upper, lower, number and symbol."
# =============================================================================
import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

# PHONE: 10-digit Indian mobile number starting with 6, 7, 8 or 9.
phone_validator = RegexValidator(r"^[6-9]\d{9}$", "Enter a valid 10-digit Indian mobile number (starts with 6–9).")
# PIN CODE: exactly 6 digits and cannot start with 0.
pincode_validator = RegexValidator(r"^[1-9]\d{5}$", "Enter a valid 6-digit PIN code.")
# NAME: only letters, spaces, dot, apostrophe or hyphen (2–50 characters).
name_validator = RegexValidator(r"^[A-Za-z][A-Za-z .'-]{1,49}$", "Use letters and spaces only (2–50 characters).")


# PASSWORD VALIDATION: added to settings.py -> AUTH_PASSWORD_VALIDATORS.
# Rejects passwords missing an uppercase letter, lowercase letter, number or symbol,
# passwords with spaces, and passwords repeating one character 4 times (aaaa).
class StrongPasswordValidator:
    """Password must mix uppercase, lowercase, a number and a symbol, and have no spaces."""

    RULES = [
        (r"[A-Z]", "one uppercase letter"),
        (r"[a-z]", "one lowercase letter"),
        (r"\d", "one number"),
        (r"[^A-Za-z0-9]", "one special character (e.g. @ # $ !)"),
    ]

    def validate(self, password, user=None):
        missing = [msg for pattern, msg in self.RULES if not re.search(pattern, password)]
        if missing:
            raise ValidationError("Password needs at least " + ", ".join(missing) + ".", code="password_weak")
        if " " in password:
            raise ValidationError("Password cannot contain spaces.", code="password_space")
        if re.search(r"(.)\1\1\1", password):
            raise ValidationError("Password cannot repeat the same character 4 times in a row.", code="password_repeat")

    def get_help_text(self):
        return "Use 8+ characters with uppercase, lowercase, a number and a special character."
