# =============================================================================
# FILE: complaints/views.py
# WHAT IS HERE: citizen-side complaint pages —
#   new (Report a problem), mine (My complaints), detail (one complaint), rate, reopen, upvote, feed (Around me).
# VIVA TIP: "Citizen complaint pages are in complaints/views.py; the URLs are in complaints/urls.py."
# =============================================================================
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Exists, OuterRef, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Ward
from core.decorators import citizen_required

from . import services
from .forms import ComplaintForm, RateForm, ReopenForm
from .models import Category, Complaint, Upvote


# Adds the upvote count (and 'did I upvote?') to a list of complaints.
def with_votes(qs, user):
    qs = qs.select_related("category", "ward", "user").annotate(n_votes=Count("upvotes", distinct=True))
    if user.is_authenticated:
        qs = qs.annotate(voted=Exists(Upvote.objects.filter(complaint=OuterRef("pk"), user=user)))
    return qs


# REPORT A PROBLEM page (/complaints/new/). Only citizens. Valid form -> file_complaint() in services.py.
@citizen_required
def new(request):
    form = ComplaintForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        c = services.file_complaint(form, request.user)
        messages.success(request, f"Complaint {c.code} filed! We'll notify you at every step.")
        return redirect(f"{c.get_absolute_url()}?new=1")
    return render(request, "user/new.html", {"form": form, "categories": Category.objects.filter(is_active=True)})


# MY COMPLAINTS page: the citizen's own complaints with status tabs.
@citizen_required
def mine(request):
    qs = with_votes(request.user.complaints.all(), request.user).order_by("-created_at")
    status = request.GET.get("status", "")
    counts = {r["status"]: r["n"] for r in request.user.complaints.values("status").annotate(n=Count("id"))}
    if status:
        qs = qs.filter(status=status)
    return render(request, "user/mine.html", {
        "page": Paginator(qs, 10).get_page(request.GET.get("page")),
        "status": status, "counts": counts, "statuses": Complaint.Status.choices,
    })


# COMPLAINT DETAIL page: photo, tracker, timeline, and rate / reopen / upvote boxes.
# Admins are sent to the admin version of the page instead.
@login_required
def detail(request, code):
    c = get_object_or_404(with_votes(Complaint.objects.all(), request.user), code=code.upper())
    is_owner = c.user_id == request.user.id
    if request.user.is_admin_role:
        return redirect(c.get_admin_url())
    return render(request, "user/detail.html", {
        "c": c, "is_owner": is_owner, "updates": c.updates.select_related("by"),
        "rate_form": RateForm(), "reopen_form": ReopenForm(), "just_filed": request.GET.get("new") == "1",
    })


# RATE: owner only, once, after cleaning.
@citizen_required
@require_POST
def rate(request, code):
    c = get_object_or_404(Complaint, code=code, user=request.user)
    form = RateForm(request.POST)
    if not c.can_rate:
        messages.error(request, "You can rate only once, after the spot is cleaned.")
    elif form.is_valid():
        services.rate(c, form.cleaned_data["rating"], form.cleaned_data["feedback"])
        messages.success(request, "Thanks for rating! Your feedback helps the team. ⭐")
    else:
        messages.error(request, "Pick a rating from 1 to 5 stars.")
    return redirect(c)


# REOPEN: owner only, once, within 7 days of cleaning.
@citizen_required
@require_POST
def reopen(request, code):
    c = get_object_or_404(Complaint, code=code, user=request.user)
    form = ReopenForm(request.POST)
    if not c.can_reopen:
        messages.error(request, "This complaint can no longer be reopened.")
    elif form.is_valid():
        services.reopen(c, request.user, form.cleaned_data["reason"])
        messages.warning(request, f"{c.code} reopened. The team has been alerted.")
    else:
        messages.error(request, form.errors["reason"][0])
    return redirect(c)


# UPVOTE button. Works without page reload (returns JSON) and also as a normal form.
@citizen_required
@require_POST
def upvote(request, code):
    c = get_object_or_404(Complaint, code=code)
    if c.user_id == request.user.id:
        msg, ok = "You can't upvote your own complaint.", False
        on = False
    elif not c.is_open:
        msg, ok, on = "This complaint is already closed.", False, False
    else:
        on = services.toggle_upvote(c, request.user)
        msg, ok = ("Added your voice 👍" if on else "Upvote removed"), True
    count = c.upvotes.count()
    if request.headers.get("x-requested-with") == "fetch":
        return JsonResponse({"ok": ok, "on": on, "count": count, "message": msg}, status=200 if ok else 400)
    (messages.success if ok else messages.error)(request, msg)
    return redirect(request.POST.get("next") or c.get_absolute_url())


# AROUND ME page: open complaints in the city, filter by ward/category, sort by upvotes or newest.
@login_required
def feed(request):
    if request.user.is_admin_role:
        return redirect("panel:complaints")
    qs = with_votes(Complaint.objects.filter(status__in=Complaint.OPEN_STATUSES), request.user)
    ward = request.GET.get("ward") or (str(request.user.ward_id) if request.user.ward_id and "ward" not in request.GET else "")
    cat = request.GET.get("category", "")
    sort = request.GET.get("sort", "votes")
    if ward:
        qs = qs.filter(ward_id=ward)
    if cat:
        qs = qs.filter(category__slug=cat)
    qs = qs.order_by("-n_votes", "-created_at") if sort == "votes" else qs.order_by("-created_at")
    return render(request, "user/feed.html", {
        "page": Paginator(qs, 12).get_page(request.GET.get("page")), "wards": Ward.objects.all(),
        "categories": Category.objects.filter(is_active=True), "ward": ward, "cat": cat, "sort": sort,
    })
