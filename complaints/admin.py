# =============================================================================
# FILE: complaints/admin.py
# WHAT IS HERE: how complaints and categories look in Django's built-in admin (/django-admin/).
# =============================================================================
from django.contrib import admin

from .models import Category, Complaint, ComplaintUpdate, Upvote


class UpdateInline(admin.TabularInline):
    model = ComplaintUpdate
    extra = 0


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ["code", "title", "category", "ward", "status", "priority", "created_at"]
    list_filter = ["status", "priority", "category", "ward"]
    search_fields = ["code", "title", "address"]
    inlines = [UpdateInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "sla_hours", "is_active"]
    prepopulated_fields = {"slug": ["name"]}


admin.site.register(Upvote)
