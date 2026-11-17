# =============================================================================
# FILE: accounts/admin.py
# WHAT IS HERE: how the User table looks in Django's built-in admin (/django-admin/).
# =============================================================================
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Notification, User, Ward


@admin.register(User)
class SSUserAdmin(UserAdmin):
    list_display = ["email", "display_name", "role", "phone", "ward", "is_active"]
    list_filter = ["role", "is_active", "ward"]
    search_fields = ["email", "first_name", "last_name", "phone"]
    ordering = ["-date_joined"]
    fieldsets = UserAdmin.fieldsets + (("SaafShehar", {"fields": ["role", "phone", "ward"]}),)


admin.site.register([Ward, Notification])
admin.site.site_header = "SaafShehar Administration"
