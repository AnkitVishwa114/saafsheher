# =============================================================================
# FILE: accounts/views.py
# WHAT IS HERE: page logic (views) for login, admin login, logout, sign-up, profile and notifications.
# VIVA TIP: "/accounts/login/ is citizen login and /admin/ is admin login — both are in accounts/views.py."
# =============================================================================
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import LoginForm, ProfileForm, SignupForm


# After login we may go back to the page the user wanted. This only allows our own site's links.
def _safe_next(request):
    nxt = request.POST.get("next") or request.GET.get("next") or ""
    return nxt if url_has_allowed_host_and_scheme(nxt, {request.get_host()}) else ""


# CITIZEN LOGIN PAGE (/accounts/login/). Uses LoginForm with role USER, so admins are refused here.
def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    form = LoginForm(request, request.POST or None, role="USER")
    if request.method == "POST" and form.is_valid():
        login(request, form.user, backend="accounts.backends.EmailBackend")
        if not form.cleaned_data.get("remember"):
            request.session.set_expiry(0)
        messages.success(request, f"Welcome back, {form.user.first_name or 'friend'}!")
        return redirect(_safe_next(request) or "core:dashboard")
    return render(request, "accounts/login.html", {"form": form, "next": _safe_next(request)})


# ADMIN LOGIN PAGE (/admin/). Uses LoginForm with role ADMIN, so citizens are refused here.
# After login the admin goes to the admin panel.
def admin_login(request):
    """Separate sign-in for municipal admins at /admin/. Citizen accounts are refused here."""
    if request.user.is_authenticated:
        return redirect("panel:dashboard" if request.user.is_admin_role else "core:dashboard")
    form = LoginForm(request, request.POST or None, role="ADMIN")
    if request.method == "POST" and form.is_valid():
        login(request, form.user, backend="accounts.backends.EmailBackend")
        if not form.cleaned_data.get("remember"):
            request.session.set_expiry(0)
        messages.success(request, f"Welcome back, {form.user.first_name or 'Admin'}.")
        nxt = _safe_next(request)
        return redirect(nxt if nxt.startswith("/admin-panel/") else "panel:dashboard")
    return render(request, "accounts/admin_login.html", {"form": form, "next": _safe_next(request)})


# SIGN OUT. Admins go back to /admin/, citizens go to the home page.
@require_POST
def logout_view(request):
    was_admin = request.user.is_authenticated and request.user.is_admin_role
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("admin_login" if was_admin else "core:home")


# SIGN-UP PAGE (/accounts/signup/). Creates a citizen, logs them in, then opens 'Report a problem'.
def signup(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="accounts.backends.EmailBackend")
        messages.success(request, f"Account created. Welcome to SaafShehar, {user.first_name}!")
        return redirect("complaints:new")
    return render(request, "accounts/signup.html", {"form": form})


# PROFILE PAGE: two forms on one page — update details, and change password.
@login_required
def profile(request):
    pform = ProfileForm(instance=request.user)
    pwform = PasswordChangeForm(request.user)
    for f in pwform.fields.values():
        f.widget.attrs["autocomplete"] = "new-password"
    pwform.fields["new_password1"].widget.attrs["data-strength"] = "1"
    pwform.fields["new_password2"].widget.attrs["data-match"] = "id_new_password1"
    if request.method == "POST":
        if "save_profile" in request.POST:
            pform = ProfileForm(request.POST, instance=request.user)
            if pform.is_valid():
                pform.save()
                messages.success(request, "Profile updated.")
                return redirect("accounts:profile")
        elif "change_password" in request.POST:
            pwform = PasswordChangeForm(request.user, request.POST)
            if pwform.is_valid():
                user = pwform.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully. 🔒")
                return redirect("accounts:profile")
    stats = {}
    if not request.user.is_admin_role:
        qs = request.user.complaints.all()
        stats = {"total": qs.count(), "resolved": qs.filter(status="RESOLVED").count(), "upvotes": request.user.upvotes.count()}
    return render(request, "accounts/profile.html", {"pform": pform, "pwform": pwform, "stats": stats})


# NOTIFICATIONS PAGE: shows the user's alerts and marks them as read.
@login_required
def notifications(request):
    items = list(request.user.notifications.all()[:60])
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return render(request, "accounts/notifications.html", {"items": items})
