# =============================================================================
# FILE: complaints/models.py
# WHAT IS HERE: database tables for complaints —
#   Category (type of problem + deadline), Complaint (the main record),
#   ComplaintUpdate (timeline / history) and Upvote ('mujhe bhi dikkat hai').
# VIVA TIP: "The Complaint table is in complaints/models.py; status, deadline (SLA) and overdue logic are here."
# =============================================================================
from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

from accounts.models import Ward
from accounts.validators import pincode_validator


# TABLE: Category — e.g. Garbage pile, Blocked drain. sla_hours = deadline to clean it.
class Category(models.Model):
    """Type of sanitation problem. Each has a target resolution time (SLA)."""

    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=30, default="trash")
    description = models.CharField(max_length=140, blank=True)
    color = models.CharField(max_length=7, default="#10B981", help_text="Hex colour used on charts and badges")
    sla_hours = models.PositiveSmallIntegerField(
        default=48, validators=[MinValueValidator(2), MaxValueValidator(240)],
        help_text="Hours within which the complaint should be resolved",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


# TABLE: Complaint — one problem reported by a citizen, with photo, place, status and rating.
class Complaint(models.Model):
    # The 5 possible statuses of a complaint.
    class Status(models.TextChoices):
        RECEIVED = "RECEIVED", "Received"
        IN_PROGRESS = "IN_PROGRESS", "Work in progress"
        RESOLVED = "RESOLVED", "Cleaned"
        REJECTED = "REJECTED", "Rejected"
        REOPENED = "REOPENED", "Reopened"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    OPEN_STATUSES = [Status.RECEIVED, Status.IN_PROGRESS, Status.REOPENED]
    # Which statuses the admin may move a complaint to from each status.
    # Which status the admin can move a complaint to, from each status (the workflow rules).
    ADMIN_MOVES = {
        Status.RECEIVED: [Status.IN_PROGRESS, Status.RESOLVED, Status.REJECTED],
        Status.IN_PROGRESS: [Status.RESOLVED, Status.REJECTED],
        Status.REOPENED: [Status.IN_PROGRESS, Status.RESOLVED, Status.REJECTED],
    }

    code = models.CharField(max_length=16, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="complaints")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="complaints")
    ward = models.ForeignKey(Ward, on_delete=models.PROTECT, related_name="complaints")
    title = models.CharField(max_length=80)
    description = models.TextField(max_length=500)
    photo = models.ImageField(upload_to="complaints/before/%Y/%m/")
    after_photo = models.ImageField(upload_to="complaints/after/%Y/%m/", blank=True)
    address = models.CharField(max_length=200)
    landmark = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=6, validators=[pincode_validator])
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    priority = models.CharField(max_length=6, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RECEIVED)
    admin_note = models.CharField(max_length=255, blank=True)
    rating = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    feedback = models.CharField(max_length=300, blank=True)
    reopen_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "ward"]), models.Index(fields=["created_at"])]

    # AUTO COMPLAINT NUMBER: on first save we create a code like SS-2026-0001 (year + running number).
    def save(self, *args, **kwargs):
        if not self.code:
            year = timezone.localdate().year
            prefix = f"SS-{year}-"
            last = Complaint.objects.filter(code__startswith=prefix).order_by("-code").values_list("code", flat=True).first()
            seq = int(last.rsplit("-", 1)[1]) + 1 if last else 1
            self.code = f"{prefix}{seq:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} · {self.title}"

    def get_absolute_url(self):
        return reverse("complaints:detail", args=[self.code])

    def get_admin_url(self):
        return reverse("panel:complaint", args=[self.code])

    # ------------------------------------------------------------ helpers
    # Open = Received, Work in progress or Reopened (not yet cleaned or rejected).
    @property
    def is_open(self):
        return self.status in self.OPEN_STATUSES

    # DEADLINE = time filed + the category's SLA hours.
    @property
    def due_at(self):
        return self.created_at + timedelta(hours=self.category.sla_hours)

    # OVERDUE = still open AND the deadline has passed.
    @property
    def is_overdue(self):
        return self.is_open and timezone.now() > self.due_at

    # Hours left before the deadline (negative = late).
    @property
    def hours_left(self):
        return round((self.due_at - timezone.now()).total_seconds() / 3600)

    # Status choices the admin sees for this complaint right now.
    @property
    def next_moves(self):
        return self.ADMIN_MOVES.get(self.status, [])

    # Citizen can rate only once, and only after it is cleaned.
    @property
    def can_rate(self):
        return self.status == self.Status.RESOLVED and self.rating is None

    # REOPEN RULE: only once, and only within 7 days of cleaning (SS_REOPEN_DAYS in settings).
    @property
    def can_reopen(self):
        return (
            self.status == self.Status.RESOLVED and self.reopen_count == 0 and self.resolved_at
            and timezone.now() <= self.resolved_at + timedelta(days=settings.SS_REOPEN_DAYS)
        )

    # How many hours it took to clean (shown as 'Cleaned in X hours').
    @property
    def resolution_hours(self):
        if not self.resolved_at:
            return None
        return round((self.resolved_at - self.created_at).total_seconds() / 3600, 1)

    # Colour name for the status badge, and the step number for the progress tracker.
    @property
    def tone(self):
        return {"RECEIVED": "blue", "IN_PROGRESS": "amber", "RESOLVED": "green", "REJECTED": "red", "REOPENED": "violet"}[self.status]

    @property
    def stage(self):
        """Index on the 3-step tracker: Received → In progress → Cleaned."""
        return {"RECEIVED": 0, "REOPENED": 0, "IN_PROGRESS": 1, "RESOLVED": 2, "REJECTED": 2}[self.status]

    # Google Maps links built from the GPS location the citizen shared.
    @property
    def embed_map_url(self):
        if self.latitude is None or self.longitude is None:
            return ""
        lat, lng, d = float(self.latitude), float(self.longitude), 0.004
        return (f"https://www.openstreetmap.org/export/embed.html?bbox={lng - d},{lat - d},{lng + d},{lat + d}"
                f"&layer=mapnik&marker={lat},{lng}")

    @property
    def map_url(self):
        if self.latitude is None or self.longitude is None:
            return ""
        return f"https://www.openstreetmap.org/?mlat={self.latitude}&mlon={self.longitude}#map=17/{self.latitude}/{self.longitude}"


# TABLE: ComplaintUpdate — one row per status change. This is the TIMELINE on the complaint page.
class ComplaintUpdate(models.Model):
    """Timeline entry: every status change, with who did it and why."""

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="updates")
    status = models.CharField(max_length=12, choices=Complaint.Status.choices)
    note = models.CharField(max_length=255, blank=True)
    by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.complaint.code} → {self.status}"


# TABLE: Upvote — another citizen says 'I face this too'. One upvote per person per complaint.
class Upvote(models.Model):
    """'Mujhe bhi dikkat hai' – other citizens confirming the same problem."""

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="upvotes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="upvotes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["complaint", "user"], name="one_upvote_per_user")]
