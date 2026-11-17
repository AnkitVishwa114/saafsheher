# =============================================================================
# FILE: complaints/urls.py
# WHAT IS HERE: URLs for citizen complaint pages (/complaints/...).
# =============================================================================
from django.urls import path

from . import views

app_name = "complaints"

urlpatterns = [
    path("new/", views.new, name="new"),
    path("mine/", views.mine, name="mine"),
    path("feed/", views.feed, name="feed"),
    path("<str:code>/", views.detail, name="detail"),
    path("<str:code>/rate/", views.rate, name="rate"),
    path("<str:code>/reopen/", views.reopen, name="reopen"),
    path("<str:code>/upvote/", views.upvote, name="upvote"),
]
