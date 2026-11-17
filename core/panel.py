# =============================================================================
# FILE: core/panel.py
# WHAT IS HERE: the MUNICIPAL ADMIN PANEL pages (/admin-panel/). Every page has @admin_required,
# so only ADMIN accounts can open them.
#   dashboard, complaints list + filters, export CSV, one complaint (change status),
#   wards, categories, citizens (block / unblock).
# VIVA TIP: "Admin panel code is in core/panel.py and its URLs are in core/panel_urls.py."
# =============================================================================
"""Municipal admin panel: dashboard, complaint handling, wards, categories, users, export."""

import csv
import json
from datetime import timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User, Ward
from complaints import services
from complaints.forms import CategoryForm, StatusForm, WardForm
from complaints.models import Category, Complaint
from core.decorators import admin_required
from core.views import ward_ranking


# Open complaints that are past their deadline.
def _overdue(qs):
    return [c for c in qs.filter(status__in=Complaint.OPEN_STATUSES).select_related("category") if c.is_overdue]


# ADMIN DASHBOARD: KPI numbers, 14-day chart, by-category and by-ward charts, latest and overdue lists.
@admin_required
def dashboard(request):
    qs = Complaint.objects.all()
    today = timezone.localdate()
    counts = {r["status"]: r["n"] for r in qs.values("status").annotate(n=Count("id"))}
    days = [today - timedelta(days=i) for i in range(13, -1, -1)]
    daily = {r["d"]: r["n"] for r in qs.filter(created_at__date__gte=days[0]).annotate(d=TruncDate("created_at")).values("d").annotate(n=Count("id"))}
    solved = {r["d"]: r["n"] for r in qs.filter(resolved_at__date__gte=days[0]).annotate(d=TruncDate("resolved_at")).values("d").annotate(n=Count("id"))}
    cats = Category.objects.annotate(n=Count("complaints")).filter(n__gt=0).order_by("-n")
    wards = Ward.objects.annotate(
        open=Count("complaints", filter=Q(complaints__status__in=Complaint.OPEN_STATUSES)),
        done=Count("complaints", filter=Q(complaints__status="RESOLVED")),
    ).filter(Q(open__gt=0) | Q(done__gt=0)).order_by("-open")[:8]
    resolved = qs.filter(status="RESOLVED")
    hrs = [(r - c).total_seconds() / 3600 for c, r in resolved.values_list("created_at", "resolved_at") if r]
    chart = {
        "days": [d.strftime("%d %b") for d in days],
        "filed": [daily.get(d, 0) for d in days], "solved": [solved.get(d, 0) for d in days],
        "cats": {"labels": [c.name for c in cats], "n": [c.n for c in cats], "colors": [c.color for c in cats]},
        "wards": {"labels": [f"W{w.number}" for w in wards], "open": [w.open for w in wards], "done": [w.done for w in wards]},
    }
    overdue = _overdue(qs)
    return render(request, "panel/dashboard.html", {
        "kpi": {
            "total": sum(counts.values()), "open": sum(counts.get(s, 0) for s in Complaint.OPEN_STATUSES),
            "resolved": counts.get("RESOLVED", 0), "rejected": counts.get("REJECTED", 0),
            "overdue": len(overdue), "today": daily.get(today, 0),
            "avg_hours": round(sum(hrs) / len(hrs), 1) if hrs else None,
            "rating": resolved.aggregate(a=Avg("rating"))["a"],
            "rate": round(counts.get("RESOLVED", 0) / sum(counts.values()) * 100) if counts else 0,
            "citizens": User.objects.filter(role="USER").count(),
        },
        "overdue": sorted(overdue, key=lambda c: c.due_at)[:6],
        "latest": qs.select_related("category", "ward", "user")[:7],
        "chart_json": json.dumps(chart),
        "top_wards": [w for w in ward_ranking() if w.total][:5],
    })


# Applies the filters on the complaints list: status, ward, category, priority, search, overdue, sort.
def _filtered(request):
    qs = Complaint.objects.select_related("category", "ward", "user").annotate(n_votes=Count("upvotes"))
    f = {k: request.GET.get(k, "") for k in ["status", "ward", "category", "priority", "q", "sort", "overdue"]}
    if f["status"]:
        qs = qs.filter(status=f["status"])
    if f["ward"]:
        qs = qs.filter(ward_id=f["ward"])
    if f["category"]:
        qs = qs.filter(category_id=f["category"])
    if f["priority"]:
        qs = qs.filter(priority=f["priority"])
    if f["q"]:
        q = f["q"].strip()
        qs = qs.filter(Q(code__icontains=q) | Q(title__icontains=q) | Q(address__icontains=q) | Q(user__first_name__icontains=q) | Q(user__email__icontains=q))
    qs = {"votes": qs.order_by("-n_votes", "-created_at"), "old": qs.order_by("created_at")}.get(f["sort"], qs.order_by("-created_at"))
    if f["overdue"]:
        qs = [c for c in qs if c.is_overdue]
    return qs, f


# ALL COMPLAINTS table (with filters and tabs).
@admin_required
def complaints(request):
    qs, f = _filtered(request)
    counts = {r["status"]: r["n"] for r in Complaint.objects.values("status").annotate(n=Count("id"))}
    return render(request, "panel/complaints.html", {
        "page": Paginator(qs, 15).get_page(request.GET.get("page")), "f": f, "counts": counts,
        "statuses": Complaint.Status.choices, "priorities": Complaint.Priority.choices,
        "wards": Ward.objects.all(), "categories": Category.objects.all(), "total": sum(counts.values()),
    })


# EXPORT: downloads the (filtered) complaints as a CSV file for Excel.
@admin_required
def export_csv(request):
    qs, _ = _filtered(request)
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="saafshehar-complaints-{timezone.localdate()}.csv"'
    w = csv.writer(resp)
    w.writerow(["Code", "Title", "Category", "Ward", "Status", "Priority", "Citizen", "Phone", "Address", "Pincode", "Filed", "Resolved", "Hours", "Upvotes", "Rating"])
    for c in qs:
        w.writerow([c.code, c.title, c.category.name, c.ward.name, c.get_status_display(), c.get_priority_display(),
                    c.user.display_name, c.user.phone, c.address, c.pincode, timezone.localtime(c.created_at).strftime("%Y-%m-%d %H:%M"),
                    timezone.localtime(c.resolved_at).strftime("%Y-%m-%d %H:%M") if c.resolved_at else "", c.resolution_hours or "",
                    getattr(c, "n_votes", ""), c.rating or ""])
    return resp


# ONE COMPLAINT (admin view): change status with StatusForm -> services.change_status().
@admin_required
def complaint(request, code):
    c = get_object_or_404(Complaint.objects.select_related("category", "ward", "user"), code=code.upper())
    form = StatusForm(request.POST or None, request.FILES or None, complaint=c)
    if request.method == "POST":
        if not c.next_moves:
            messages.error(request, "This complaint is closed. It can only be reopened by the citizen.")
        elif form.is_valid():
            d = form.cleaned_data
            services.change_status(c, d["status"], request.user, d["note"].strip(), d.get("after_photo"), d["priority"])
            messages.success(request, f"{c.code} marked as “{c.get_status_display()}”. The citizen has been notified.")
            return redirect(c.get_admin_url())
        else:
            messages.error(request, "Please fix the highlighted fields.")
    return render(request, "panel/complaint.html", {
        "c": c, "form": form, "updates": c.updates.select_related("by"), "votes": c.upvotes.count(),
        "others": Complaint.objects.filter(ward=c.ward, category=c.category, status__in=Complaint.OPEN_STATUSES).exclude(pk=c.pk)[:4],
    })


# WARDS page: ranking table + add / edit a ward.
@admin_required
def wards(request, pk=None):
    obj = get_object_or_404(Ward, pk=pk) if pk else None
    form = WardForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Ward {'updated' if obj else 'added'}.")
        return redirect("panel:wards")
    return render(request, "panel/wards.html", {"form": form, "obj": obj, "wards": ward_ranking()})


# CATEGORIES page: add / edit problem types and their deadlines.
@admin_required
def categories(request, pk=None):
    obj = get_object_or_404(Category, pk=pk) if pk else None
    form = CategoryForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Category {'updated' if obj else 'added'}.")
        return redirect("panel:categories")
    cats = Category.objects.annotate(n=Count("complaints"), open=Count("complaints", filter=Q(complaints__status__in=Complaint.OPEN_STATUSES)))
    return render(request, "panel/categories.html", {"form": form, "obj": obj, "cats": cats})


# CITIZENS page: list and search citizens with their complaint counts.
@admin_required
def users(request):
    qs = User.objects.filter(role="USER").select_related("ward").annotate(
        n=Count("complaints", distinct=True), done=Count("complaints", filter=Q(complaints__status="RESOLVED"), distinct=True),
    ).order_by("-date_joined")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q))
    return render(request, "panel/users.html", {"page": Paginator(qs, 20).get_page(request.GET.get("page")), "q": q})


# BLOCK / UNBLOCK a citizen (a blocked citizen cannot log in).
@admin_required
@require_POST
def user_toggle(request, pk):
    u = get_object_or_404(User, pk=pk, role="USER")
    u.is_active = not u.is_active
    u.save(update_fields=["is_active"])
    messages.success(request, f"{u.display_name} {'activated' if u.is_active else 'blocked'}.")
    return redirect(request.POST.get("next") or "panel:users")
