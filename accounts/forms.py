# =============================================================================
# FILE: accounts/forms.py
# WHAT IS HERE: forms + VALIDATION for login, sign-up and profile.
#   LoginForm   -> wrong password counter + 15-minute lock + role check (citizen vs admin login)
#   SignupForm  -> name, unique email, valid unique phone, strong matching password, agree box
#   ProfileForm -> edit name, phone, ward
# VIVA TIP: "Sign-up and login validation is in accounts/forms.py."
# =============================================================================
from django import forms
from django.conf import settings
from django.contrib.auth import authenticate, password_validation
from django.core.cache import cache

from .models import User, Ward
from .validators import name_validator, phone_validator


# Key used to store the number of wrong passwords for an email in the cache.
def _lock_key(email):
    return f"login-fails:{email}"


# LOGIN FORM — used by both /accounts/login/ (citizens) and /admin/ (admins).
class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "you@example.com", "autocomplete": "email", "autofocus": True}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Your password", "autocomplete": "current-password"}))
    remember = forms.BooleanField(required=False, initial=True, label="Keep me signed in")

    def __init__(self, request=None, *args, role=None, **kwargs):
        self.request = request
        self.role = role  # "USER" on the citizen sign-in, "ADMIN" on /admin/
        self.user = None
        super().__init__(*args, **kwargs)

    # LOGIN VALIDATION, step by step:
    #  1) if this email already failed 5 times -> 'Try again in 15 minutes'
    #  2) wrong email/password -> add 1 to the fail counter and show an error
    #  3) right password but wrong page (admin on citizen login or citizen on /admin/) -> error
    def clean(self):
        data = super().clean()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password")
        if not email or not password:
            return data
        fails = cache.get(_lock_key(email), 0)
        if fails >= settings.SS_LOGIN_MAX_FAILS:
            raise forms.ValidationError(
                f"Too many wrong attempts. Try again in {settings.SS_LOGIN_LOCK_MINUTES} minutes.", code="locked"
            )
        user = authenticate(self.request, username=email, password=password)
        if user is None:
            fails += 1
            cache.set(_lock_key(email), fails, settings.SS_LOGIN_LOCK_MINUTES * 60)
            left = settings.SS_LOGIN_MAX_FAILS - fails
            msg = "Email or password is incorrect."
            if 0 < left <= 2:
                msg += f" {left} attempt{'s' if left > 1 else ''} left before a {settings.SS_LOGIN_LOCK_MINUTES}-minute lock."
            raise forms.ValidationError(msg, code="invalid_login")
        cache.delete(_lock_key(email))
        if self.role and user.role != self.role:
            if self.role == "ADMIN":
                raise forms.ValidationError("This sign-in is only for municipal admins. Citizens sign in from the main website.", code="wrong_role")
            raise forms.ValidationError("Municipal admin accounts sign in from the admin login page.", code="wrong_role")
        self.user = user
        return data


# SIGN-UP FORM — creates a new CITIZEN account (never an admin).
class SignupForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password", strip=False,
        widget=forms.PasswordInput(attrs={"placeholder": "Create a strong password", "autocomplete": "new-password", "data-strength": "1"}),
    )
    password2 = forms.CharField(
        label="Confirm password", strip=False,
        widget=forms.PasswordInput(attrs={"placeholder": "Type it again", "autocomplete": "new-password", "data-match": "id_password1"}),
    )
    agree = forms.BooleanField(label="I confirm my complaints will be genuine and my photos are my own.")

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "ward"]
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "Ankit", "autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Vishwakarma", "autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"placeholder": "you@example.com", "autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"placeholder": "10-digit mobile", "inputmode": "numeric", "maxlength": "10", "autocomplete": "tel", "pattern": "[6-9][0-9]{9}"}),
        }
        labels = {"ward": "Your ward"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ["first_name", "phone", "ward"]:
            self.fields[f].required = True
        self.fields["first_name"].validators.append(name_validator)
        self.fields["first_name"].widget.attrs["pattern"] = "[A-Za-z][A-Za-z .'-]{1,49}"
        self.fields["ward"].queryset = Ward.objects.all()
        self.fields["ward"].empty_label = "Select your ward"

    # Last name is optional, but if given it must be letters only.
    def clean_last_name(self):
        v = self.cleaned_data["last_name"].strip()
        if v:
            name_validator(v)
        return v

    # EMAIL VALIDATION: saved in lowercase and must not already be registered.
    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists. Try signing in.")
        return email

    # PHONE VALIDATION: valid Indian mobile and not used by another account.
    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip().replace(" ", "")
        phone_validator(phone)
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("This mobile number is already registered.")
        return phone

    # PASSWORD VALIDATION: both passwords must match, then all password rules run
    # (length, not too common, not similar to name/email, upper+lower+number+symbol).
    def clean(self):
        data = super().clean()
        p1, p2 = data.get("password1"), data.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords don't match.")
        if p1:
            probe = User(email=data.get("email", ""), first_name=data.get("first_name", ""), last_name=data.get("last_name", ""))
            try:
                password_validation.validate_password(p1, probe)
            except forms.ValidationError as e:
                self.add_error("password1", e)
        return data

    # Save the new user: username = email, role = citizen, password stored as a secure hash.
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        user.role = User.Role.USER
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


# PROFILE FORM — citizen/admin edits their name, phone and ward on the Profile page.
class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "ward"]
        labels = {"ward": "Your ward"}
        widgets = {"phone": forms.TextInput(attrs={"inputmode": "numeric", "maxlength": "10"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["first_name"].validators.append(name_validator)

    # Phone is optional here, but if given it must be valid and not belong to someone else.
    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if phone:
            phone_validator(phone)
            if User.objects.filter(phone=phone).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("This mobile number is already registered.")
        return phone
