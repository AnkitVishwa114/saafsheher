# =============================================================================
# FILE: accounts/models.py
# WHAT IS HERE: database tables for people — Ward, User (citizen or admin) and Notification.
# VIVA TIP: "The User table has a 'role' field: USER = citizen, ADMIN = municipal admin."
# =============================================================================
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

from .validators import phone_validator


# TABLE: Ward — a municipal area (number, name, zone). Complaints and users belong to a ward.
class Ward(models.Model):
    """A municipal ward. Complaints are routed and ranked by ward."""

    name = models.CharField(max_length=60, unique=True)
    number = models.PositiveSmallIntegerField(unique=True)
    zone = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"Ward {self.number} · {self.name}"


# Makes sure every superuser created from the terminal becomes an ADMIN.
class SSUserManager(UserManager):
    def create_superuser(self, username=None, email=None, password=None, **extra):
        extra.setdefault("role", "ADMIN")
        return super().create_superuser(username or email, email, password, **extra)


# TABLE: User — every citizen and admin. Extra fields: role, unique email, phone, ward.
class User(AbstractUser):
    """A citizen or a municipal admin. Citizens sign in with their email address."""

    class Role(models.TextChoices):
        USER = "USER", "Citizen"
        ADMIN = "ADMIN", "Municipal admin"

    role = models.CharField(max_length=6, choices=Role.choices, default=Role.USER)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=10, validators=[phone_validator], blank=True)
    ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True, blank=True, related_name="residents")

    objects = SSUserManager()

    class Meta:
        ordering = ["first_name", "username"]
        constraints = [
            models.UniqueConstraint(fields=["phone"], condition=~models.Q(phone=""), name="unique_phone_when_set"),
        ]

    # Before saving: email is stored in lowercase, superusers always get the ADMIN role.
    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().lower()
        if self.is_superuser:
            self.role = self.Role.ADMIN
            self.is_staff = True
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name

    # Small helpers used on the pages: full name, initials (for the avatar circle), avatar colour.
    @property
    def display_name(self):
        return self.get_full_name() or self.email or self.username

    @property
    def initials(self):
        parts = self.display_name.split()
        return ("".join(p[0] for p in parts[:2]) or "U").upper()

    @property
    def hue(self):
        return sum(map(ord, self.email or self.username)) * 41 % 360

    is_admin_role = property(lambda self: self.role == self.Role.ADMIN)


# TABLE: Notification — the alerts a user sees in the bell icon (e.g. 'Spot cleaned').
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=140)
    body = models.CharField(max_length=255, blank=True)
    link = models.CharField(max_length=200, blank=True)
    icon = models.CharField(max_length=20, default="bell")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}: {self.title}"


# Helper to create a notification in one line: notify(user, title, body, link).
def notify(user, title, body="", link="", icon="bell"):
    return Notification.objects.create(user=user, title=title, body=body, link=link, icon=icon)
