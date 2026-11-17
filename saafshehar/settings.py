# =============================================================================
# FILE: saafshehar/settings.py
# WHAT IS HERE: project settings — installed apps, database, login rules, password rules,
# photo upload limits and other business rules (at the bottom).
# VIVA TIP: "All limits like 5 MB photo, 5 complaints a day, 15-minute lock are in settings.py, at the end."
# =============================================================================
"""
Django settings for SaafShehar – Kachra Shikayat (SIH26195).

Values that differ between a laptop and a server come from environment
variables, with safe local defaults.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-u0&9dkmh(g=#1ja!xfdz*m0+bcu#lfkg@kc!=5f_!kdp42@ahn",
)
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,.onrender.com,.pythonanywhere.com"
).split(",")
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o]

# Our three apps: accounts (users/login), complaints (complaint data), core (pages + admin panel).
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "core",
    "accounts",
    "complaints",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "saafshehar.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "saafshehar.wsgi.application"

# DATABASE: SQLite file db.sqlite3 in the project folder.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# LOGIN SETUP: we use our own User model (accounts/models.py) and log in with EMAIL, not username
# (the email login code is in accounts/backends.py).
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["accounts.backends.EmailBackend"]

# PASSWORD RULES: Django's built-in checks + our StrongPasswordValidator
# (uppercase + lowercase + number + symbol) from accounts/validators.py.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "accounts.validators.StrongPasswordValidator"},
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "core:home"

# Sessions end when the browser closes unless "Remember me" is ticked.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False

# CACHE: used to count wrong login attempts for the 15-minute account lock.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
# UPLOADED PHOTOS are saved inside the media/ folder.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

FILE_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 7 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Business rules, kept in one place so they are easy to explain in the viva.
SS_MAX_PHOTO_MB = 5            # largest photo a citizen can upload
SS_MIN_PHOTO_PX = 200          # photos smaller than this (width or height) are rejected
SS_DAILY_LIMIT = 5             # complaints one citizen can file per day
SS_DUPLICATE_HOURS = 24        # same category + ward within this window = duplicate
SS_REOPEN_DAYS = 7             # a resolved complaint can be reopened within this many days
SS_LOGIN_MAX_FAILS = 5         # wrong passwords before the account is locked…
SS_LOGIN_LOCK_MINUTES = 15     # …for this many minutes
