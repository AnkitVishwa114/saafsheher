# =============================================================================
# FILE: core/context_processors.py
# WHAT IS HERE: values available on EVERY page — unread alert count, sidebar counts,
# and which base layout to use (admin panel layout or citizen layout).
# =============================================================================
# Runs for every page. Admin -> open/new/overdue counts for the sidebar. Citizen -> my filed/open/cleaned.
def _asset_version():
    # Version number for CSS/JS links (?v=...). It changes whenever app.css or app.js changes,
    # so browsers always download the new file instead of using an old cached copy.
    from django.conf import settings
    try:
        return int(max((settings.BASE_DIR / "static" / f).stat().st_mtime for f in ("css/app.css", "js/app.js")))
    except OSError:
        return 1


def site(request):
    ctx = {"SITE_NAME": "SaafShehar", "SITE_TAGLINE": "Photo kheencho, shehar saaf karo", "ASSET_V": _asset_version()}
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        from complaints.models import Complaint

        ctx["unread_count"] = user.notifications.filter(is_read=False).count()
        if user.is_admin_role:
            open_qs = Complaint.objects.filter(status__in=Complaint.OPEN_STATUSES).select_related("category")
            total = Complaint.objects.count()
            done = Complaint.objects.filter(status="RESOLVED").count()
            ctx.update({
                "side_open": open_qs.count(),
                "side_new": open_qs.filter(status__in=["RECEIVED", "REOPENED"]).count(),
                "side_overdue": sum(1 for c in open_qs if c.is_overdue),
                "side_rate": round(done / total * 100) if total else 0,
                "base_template": "panel/base.html",
            })
        else:
            mine = user.complaints.all()
            ctx.update({
                "my_total": mine.count(),
                "my_open": mine.filter(status__in=Complaint.OPEN_STATUSES).count(),
                "my_done": mine.filter(status="RESOLVED").count(),
                "base_template": "user/base.html",
            })
    return ctx
