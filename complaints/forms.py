# =============================================================================
# FILE: complaints/forms.py
# WHAT IS HERE: forms + VALIDATION for complaints and the admin panel.
#   validate_photo -> photo type, size, real image, minimum size
#   ComplaintForm  -> title, description, address, PIN, GPS, daily limit, duplicate check
#   StatusForm     -> admin status change (after-photo needed for 'Cleaned', reason for 'Rejected')
#   RateForm / ReopenForm / TrackForm / WardForm / CategoryForm
# VIVA TIP: "Complaint validation (photo, duplicate, 5-per-day limit) is in complaints/forms.py."
# =============================================================================
import re
from datetime import timedelta
from decimal import Decimal

from django import forms
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

from accounts.models import Ward
from accounts.validators import pincode_validator

from .models import Category, Complaint

ALLOWED_EXT = ["jpg", "jpeg", "png", "webp"]


# PHOTO VALIDATION (used for both before and after photos):
#  1) only JPG / PNG / WEBP   2) not bigger than 5 MB
#  3) must open as a real image (not a renamed file)   4) at least 200 px wide and tall
def validate_photo(f, label="Photo"):
    """Real image check: extension, size, actually decodable, not too small."""
    FileExtensionValidator(ALLOWED_EXT, f"{label} must be a JPG, PNG or WEBP image.")(f)
    if f.size > settings.SS_MAX_PHOTO_MB * 1024 * 1024:
        raise forms.ValidationError(f"{label} must be smaller than {settings.SS_MAX_PHOTO_MB} MB (yours is {f.size / 1048576:.1f} MB).")
    try:
        pos = f.tell() if hasattr(f, "tell") else 0
        img = Image.open(f)
        img.verify()
        f.seek(pos)
        w, h = Image.open(f).size
        f.seek(pos)
    except (UnidentifiedImageError, OSError, ValueError):
        raise forms.ValidationError(f"{label} file is damaged or is not a real image.")
    if min(w, h) < settings.SS_MIN_PHOTO_PX:
        raise forms.ValidationError(f"{label} is too small ({w}×{h}). Use at least {settings.SS_MIN_PHOTO_PX}px on each side.")
    return f


# COMPLAINT FORM — the 4-step 'Report a problem' form filled by citizens.
class ComplaintForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True), widget=forms.RadioSelect, empty_label=None,
        error_messages={"required": "Choose what kind of problem it is."},
    )
    latitude = forms.DecimalField(required=False, widget=forms.HiddenInput, max_digits=9, decimal_places=6)
    longitude = forms.DecimalField(required=False, widget=forms.HiddenInput, max_digits=9, decimal_places=6)

    class Meta:
        model = Complaint
        fields = ["photo", "category", "title", "description", "priority", "ward", "address", "landmark", "pincode", "latitude", "longitude"]
        widgets = {
            "photo": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp", "capture": "environment"}),
            "title": forms.TextInput(attrs={"placeholder": "e.g. Garbage pile near the bus stop", "maxlength": 80, "minlength": 8}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "What's the problem? Since when? Is it blocking the road or smelling?", "maxlength": 500, "minlength": 20, "data-counter": "500"}),
            "address": forms.TextInput(attrs={"placeholder": "House/shop no., street, area", "maxlength": 200, "minlength": 10}),
            "landmark": forms.TextInput(attrs={"placeholder": "e.g. Opposite Shiv Mandir", "maxlength": 100}),
            "pincode": forms.TextInput(attrs={"placeholder": "462001", "inputmode": "numeric", "maxlength": 6, "pattern": "[1-9][0-9]{5}"}),
            "priority": forms.RadioSelect,
        }
        labels = {"priority": "How urgent is it?", "title": "Short title", "photo": "Photo of the problem"}

    # Pre-select the citizen's own ward.
    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["ward"].queryset = Ward.objects.all()
        self.fields["ward"].empty_label = "Select ward"
        if user and user.ward_id and not self.is_bound:
            self.initial["ward"] = user.ward_id

    # Photo is checked with validate_photo() above.
    def clean_photo(self):
        return validate_photo(self.cleaned_data["photo"])

    # TITLE VALIDATION: at least 8 characters, not ALL CAPS, must contain words.
    def clean_title(self):
        t = " ".join(self.cleaned_data["title"].split())
        if len(t) < 8:
            raise forms.ValidationError("Title is too short. Use at least 8 characters.")
        if t.isupper() and len(t) > 10:
            raise forms.ValidationError("Please don't write the title in ALL CAPS.")
        if not re.search(r"[A-Za-zऀ-ॿ]", t):
            raise forms.ValidationError("Title must contain words.")
        return t

    # DESCRIPTION VALIDATION: at least 20 characters.
    def clean_description(self):
        d = self.cleaned_data["description"].strip()
        if len(d) < 20:
            raise forms.ValidationError(f"Describe the problem in at least 20 characters ({len(d)} now).")
        return d

    # ADDRESS VALIDATION: at least 10 characters (street + area).
    def clean_address(self):
        a = " ".join(self.cleaned_data["address"].split())
        if len(a) < 10:
            raise forms.ValidationError("Address is too short. Add street and area.")
        return a

    # PIN CODE VALIDATION: 6 digits (rule in accounts/validators.py).
    def clean_pincode(self):
        p = self.cleaned_data["pincode"].strip()
        pincode_validator(p)
        return p

    # WHOLE-FORM CHECKS:
    #  - GPS: both latitude and longitude, and inside India
    #  - DAILY LIMIT: max 5 complaints per citizen in 24 hours
    #  - DUPLICATE: same citizen + same category + same ward, still open, within 24 hours
    def clean(self):
        data = super().clean()
        lat, lng = data.get("latitude"), data.get("longitude")
        if (lat is None) != (lng is None):
            raise forms.ValidationError("Location is incomplete. Tap “Use my location” again.")
        if lat is not None and not (Decimal("6") <= lat <= Decimal("38") and Decimal("68") <= lng <= Decimal("98")):
            raise forms.ValidationError("Location must be inside India.")
        if self.user:
            since = timezone.now() - timedelta(hours=24)
            today_count = Complaint.objects.filter(user=self.user, created_at__gte=since).count()
            if today_count >= settings.SS_DAILY_LIMIT:
                raise forms.ValidationError(f"You can file up to {settings.SS_DAILY_LIMIT} complaints in 24 hours. Please try again later.")
            cat, ward = data.get("category"), data.get("ward")
            if cat and ward:
                dup = Complaint.objects.filter(
                    user=self.user, category=cat, ward=ward, status__in=Complaint.OPEN_STATUSES,
                    created_at__gte=timezone.now() - timedelta(hours=settings.SS_DUPLICATE_HOURS),
                ).first()
                if dup:
                    raise forms.ValidationError(
                        f"You already reported “{cat.name}” in this ward today ({dup.code}). Upvote or follow that one instead."
                    )
        return data


# ADMIN STATUS FORM — on the admin complaint page ('Take action' box).
class StatusForm(forms.Form):
    status = forms.ChoiceField(choices=Complaint.Status.choices, widget=forms.RadioSelect)
    note = forms.CharField(max_length=255, required=False, widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Message to the citizen (required when rejecting)"}))
    after_photo = forms.ImageField(required=False, widget=forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}))
    priority = forms.ChoiceField(choices=Complaint.Priority.choices)

    # Show only the statuses allowed from the current one (ADMIN_MOVES in models.py).
    def __init__(self, *args, complaint=None, **kwargs):
        self.complaint = complaint
        super().__init__(*args, **kwargs)
        if complaint:
            self.fields["status"].choices = [(s, Complaint.Status(s).label) for s in complaint.next_moves]
            self.fields["priority"].initial = complaint.priority

    # After photo is checked with the same validate_photo().
    def clean_after_photo(self):
        f = self.cleaned_data.get("after_photo")
        return validate_photo(f, "After photo") if f else f

    # ADMIN RULES: 'Cleaned' needs an after photo as proof; 'Rejected' needs a reason of 10+ characters.
    def clean(self):
        d = super().clean()
        status = d.get("status")
        if status == Complaint.Status.RESOLVED and not (d.get("after_photo") or (self.complaint and self.complaint.after_photo)):
            self.add_error("after_photo", "Upload an ‘after’ photo as proof that the spot is clean.")
        if status == Complaint.Status.REJECTED and len((d.get("note") or "").strip()) < 10:
            self.add_error("note", "Explain why it is rejected (at least 10 characters).")
        return d


# RATING FORM — citizen gives 1 to 5 stars and optional feedback after cleaning.
class RateForm(forms.Form):
    rating = forms.TypedChoiceField(choices=[(i, i) for i in range(5, 0, -1)], coerce=int, widget=forms.RadioSelect)
    feedback = forms.CharField(max_length=300, required=False, widget=forms.Textarea(attrs={"rows": 2, "placeholder": "How was the work? (optional)"}))


# REOPEN FORM — citizen explains (10+ characters) why the spot is still not clean.
class ReopenForm(forms.Form):
    reason = forms.CharField(min_length=10, max_length=255, widget=forms.Textarea(attrs={"rows": 2, "placeholder": "What is still wrong? (at least 10 characters)"}))


# TRACK FORM — public 'Track a complaint' page.
class TrackForm(forms.Form):
    code = forms.CharField(max_length=16, widget=forms.TextInput(attrs={"placeholder": "SS-2026-0001", "autocomplete": "off"}))

    # Complaint number must look like SS-2026-0001.
    def clean_code(self):
        c = self.cleaned_data["code"].strip().upper()
        if not re.fullmatch(r"SS-\d{4}-\d{4,}", c):
            raise forms.ValidationError("Complaint numbers look like SS-2026-0001.")
        return c


# Admin adds or edits a ward.
class WardForm(forms.ModelForm):
    class Meta:
        model = Ward
        fields = ["number", "name", "zone"]


# Admin adds or edits a category (name, icon, colour, deadline).
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug", "icon", "color", "sla_hours", "description", "is_active"]
        widgets = {"color": forms.TextInput(attrs={"type": "color"})}

    # Colour must be a hex code like #10B981.
    def clean_color(self):
        c = self.cleaned_data["color"]
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", c):
            raise forms.ValidationError("Use a hex colour like #10B981.")
        return c
