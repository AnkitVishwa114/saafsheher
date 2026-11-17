# =============================================================================
# FILE: complaints/services.py
# WHAT IS HERE: the COMPLAINT WORKFLOW. Every action saves a timeline entry and sends a notification.
#   file_complaint -> citizen files   change_status -> admin updates   reopen -> citizen reopens
#   rate -> citizen rates             toggle_upvote -> citizen upvotes / removes upvote
# VIVA TIP: "When the admin changes status, change_status() in complaints/services.py saves the history and notifies the citizen."
# =============================================================================
"""Complaint workflow. Every step records a timeline entry and notifies the other side."""

from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import User, notify

from .models import Complaint, ComplaintUpdate, Upvote


# FILE A COMPLAINT: save it as 'Received', add the first timeline entry, alert all admins.
@transaction.atomic
def file_complaint(form, user):
    c = form.save(commit=False)
    c.user = user
    c.status = Complaint.Status.RECEIVED
    c.save()
    ComplaintUpdate.objects.create(complaint=c, status=c.status, by=user, note="Complaint filed")
    for admin in User.objects.filter(role=User.Role.ADMIN, is_active=True):
        notify(admin, f"New complaint {c.code}", f"{c.category.name} · {c.ward}", c.get_admin_url(), icon="inbox")
    return c


# Notification text the citizen receives for each status.
MESSAGES = {
    "IN_PROGRESS": ("Work started", "The team is working on {code}."),
    "RESOLVED": ("Spot cleaned", "{code} is marked clean. See the after photo and rate the work."),
    "REJECTED": ("Complaint closed", "{code} was rejected: {note}"),
}


# ADMIN CHANGES STATUS: save new status / note / after photo / priority,
# set the cleaned time if resolved, add a timeline entry, notify the citizen.
@transaction.atomic
def change_status(c, status, by, note="", after_photo=None, priority=None):
    c.status = status
    if note:
        c.admin_note = note
    if after_photo:
        c.after_photo = after_photo
    if priority:
        c.priority = priority
    if status == Complaint.Status.RESOLVED:
        c.resolved_at = timezone.now()
    c.save()
    ComplaintUpdate.objects.create(complaint=c, status=status, by=by, note=note)
    title, body = MESSAGES.get(status, ("Complaint updated", "{code}"))
    notify(c.user, title, body.format(code=c.code, note=note), c.get_absolute_url(),
           icon={"RESOLVED": "check", "REJECTED": "x"}.get(status, "truck"))
    return c


# CITIZEN REOPENS: status -> Reopened, count it, add timeline entry, alert admins.
@transaction.atomic
def reopen(c, by, reason):
    c.status = Complaint.Status.REOPENED
    c.reopen_count += 1
    c.resolved_at = None
    c.save()
    ComplaintUpdate.objects.create(complaint=c, status=c.status, by=by, note=reason)
    for admin in User.objects.filter(role=User.Role.ADMIN, is_active=True):
        notify(admin, f"{c.code} reopened", reason, c.get_admin_url(), icon="alert")


# CITIZEN RATES the clean-up (stars + feedback).
def rate(c, rating, feedback):
    c.rating, c.feedback = rating, feedback
    c.save(update_fields=["rating", "feedback", "updated_at"])


# UPVOTE ON/OFF: if already upvoted, remove it; otherwise add it.
def toggle_upvote(c, user):
    """Returns True if the user now supports the complaint."""
    deleted, _ = Upvote.objects.filter(complaint=c, user=user).delete()
    if deleted:
        return False
    try:
        Upvote.objects.create(complaint=c, user=user)
    except IntegrityError:
        pass
    return True
