# =============================================================================
# FILE: core/views.py
# WHAT IS HERE: public pages and the citizen dashboard —
#   home, track, leaderboard (ward ranking), dashboard, citizen_dashboard, error pages.
# VIVA TIP: "The ward ranking formula is ward_ranking() in core/views.py."
# =============================================================================
from django.conf import settings
from django.db.models import Avg, Count, F, Q
from django.http import HttpResponse
from django.shortcuts import redirect, render

from accounts.models import User, Ward
from complaints.forms import TrackForm
from complaints.models import Category, Complaint
from core.decorators import citizen_required


# WARD RANKING: score = % of complaints cleaned. Ties: fewer open complaints ranks higher.
def ward_ranking():
    """Wards ranked by % of complaints resolved (ties broken by fewer open complaints)."""
    wards = Ward.objects.annotate(
        total=Count("complaints"),
        resolved=Count("complaints", filter=Q(complaints__status="RESOLVED")),
        open=Count("complaints", filter=Q(complaints__status__in=Complaint.OPEN_STATUSES)),
    )
    rows = []
    for w in wards:
        w.score = round(w.resolved / w.total * 100) if w.total else None
        rows.append(w)
    rows.sort(key=lambda w: (w.score is None, -(w.score or 0), w.open, w.number))
    return rows


# HOME PAGE: live numbers, categories, recently cleaned spots, top wards.
def home(request):
    qs = Complaint.objects.all()
    resolved = qs.filter(status="RESOLVED")
    avg_h = None
    rs = list(resolved.values_list("created_at", "resolved_at")[:500])
    if rs:
        avg_h = round(sum((r - c).total_seconds() for c, r in rs if r) / len(rs) / 3600)
    return render(request, "public/home.html", {
        "stats": {
            "total": qs.count(), "resolved": resolved.count(),
            "citizens": User.objects.filter(role="USER").count(), "avg_hours": avg_h,
        },
        "categories": Category.objects.filter(is_active=True),
        "showcase": resolved.exclude(after_photo="").select_related("ward", "category").order_by("-resolved_at").first(),
        "top_wards": [w for w in ward_ranking() if w.total][:5],
        "recent_cleaned": resolved.exclude(after_photo="").select_related("ward", "category").order_by("-resolved_at")[:3],
        "track_form": TrackForm(),
    })


# TRACK A COMPLAINT page: anyone can enter a number like SS-2026-0001, no login needed.
def track(request):
    form = TrackForm(request.GET if "code" in request.GET else None)
    complaint = None
    if form.is_valid():
        complaint = Complaint.objects.select_related("category", "ward").filter(code=form.cleaned_data["code"]).first()
        if complaint is None:
            form.add_error("code", "No complaint found with this number.")
    return render(request, "public/track.html", {
        "form": form, "c": complaint,
        "updates": complaint.updates.all() if complaint else [],
    })


# WARD RANKING page.
def leaderboard(request):
    return render(request, "public/leaderboard.html", {"wards": ward_ranking()})


# /dashboard/ decides where to go: not logged in -> login, admin -> admin panel, citizen -> citizen home.
def dashboard(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.is_admin_role:
        return redirect("panel:dashboard")
    return citizen_dashboard(request)


# CITIZEN HOME: my counts, recent complaints, open ones in my ward, my ward's rank.
@citizen_required
def citizen_dashboard(request):
    mine = request.user.complaints.select_related("category", "ward")
    counts = {r["status"]: r["n"] for r in mine.values("status").annotate(n=Count("id"))}
    ward_stats = None
    if request.user.ward_id:
        w = [x for x in ward_ranking() if x.id == request.user.ward_id]
        ward_stats = w[0] if w else None
        if ward_stats:
            ward_stats.rank = ward_ranking().index(ward_stats) + 1
    return render(request, "user/dashboard.html", {
        "recent": mine[:5],
        "counts": {
            "total": sum(counts.values()),
            "open": sum(counts.get(s, 0) for s in Complaint.OPEN_STATUSES),
            "resolved": counts.get("RESOLVED", 0),
            "upvotes": request.user.upvotes.count(),
        },
        "to_rate": mine.filter(status="RESOLVED", rating__isnull=True).first(),
        "ward_stats": ward_stats,
        "nearby": Complaint.objects.filter(ward_id=request.user.ward_id, status__in=Complaint.OPEN_STATUSES)
        .exclude(user=request.user).select_related("category").annotate(n_votes=Count("upvotes"))
        .order_by("-n_votes", "-created_at")[:4] if request.user.ward_id else [],
        "avg_rating": mine.aggregate(a=Avg("rating"))["a"],
        "live": Complaint.objects.select_related("category", "ward").order_by("-created_at")[:8],
    })


# Serves the PWA service worker so the site can be installed like an app.
def service_worker(request):
    js = (settings.BASE_DIR / "static" / "js" / "sw.js").read_text()
    return HttpResponse(js, content_type="application/javascript")


# Custom error pages: 404 (not found), 403 (not allowed), 500 (server error).
def error_404(request, exception):
    return render(request, "404.html", status=404)


def error_403(request, exception):
    return render(request, "403.html", status=403)


def error_500(request):
    return render(request, "500.html", status=500)
