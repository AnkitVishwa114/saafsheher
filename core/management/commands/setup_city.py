# =============================================================================
# FILE: core/management/commands/setup_city.py
# WHAT IS HERE: command 'python manage.py setup_city' — creates the 8 categories and 10 wards.
# =============================================================================
"""
Create the master data the app needs: complaint categories and wards.
Safe to run again; it only adds what is missing. Edit wards later in the admin panel
to match your own city.

    python manage.py setup_city
"""

from django.core.management.base import BaseCommand

from accounts.models import Ward
from complaints.models import Category

CATEGORIES = [
    # name, slug, icon, colour, SLA hours, description
    ("Garbage pile", "garbage-pile", "trash", "#10B981", 24, "Heap of waste on the road or an empty plot"),
    ("Overflowing dustbin", "overflowing-dustbin", "bin", "#0EA5E9", 12, "Community bin full and spilling over"),
    ("Blocked drain", "blocked-drain", "droplet", "#6366F1", 48, "Choked nali or sewer, water logging"),
    ("Burning garbage", "burning-garbage", "flame", "#F97316", 6, "Waste being burnt in the open, smoke"),
    ("Dead animal", "dead-animal", "alert", "#EF4444", 8, "Carcass that needs urgent removal"),
    ("Construction debris", "construction-debris", "bricks", "#A16207", 72, "Malba / rubble dumped on public land"),
    ("Dirty public toilet", "dirty-public-toilet", "toilet", "#8B5CF6", 24, "Public toilet not cleaned or no water"),
    ("Street not swept", "street-not-swept", "broom", "#14B8A6", 24, "Road or market area not swept"),
]

WARDS = [
    (1, "Civil Lines", "North"), (2, "Gandhi Nagar", "North"), (3, "Shastri Colony", "East"),
    (4, "Nehru Nagar", "East"), (5, "Station Road", "Central"), (6, "Old City", "Central"),
    (7, "Indira Colony", "South"), (8, "Shivaji Nagar", "South"), (9, "Industrial Area", "West"),
    (10, "University Campus", "West"),
]


class Command(BaseCommand):
    help = "Create complaint categories and wards."

    def handle(self, *args, **opts):
        nc = sum(
            Category.objects.get_or_create(slug=slug, defaults=dict(name=n, icon=i, color=c, sla_hours=h, description=d))[1]
            for n, slug, i, c, h, d in CATEGORIES
        )
        nw = sum(Ward.objects.get_or_create(number=num, defaults=dict(name=name, zone=zone))[1] for num, name, zone in WARDS)
        if opts["verbosity"]:
            self.stdout.write(self.style.SUCCESS(
                f"Ready: {Category.objects.count()} categories (+{nc}), {Ward.objects.count()} wards (+{nw})."
            ))
