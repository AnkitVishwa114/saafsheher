# =============================================================================
# FILE: complaints/management/commands/seed_demo.py
# WHAT IS HERE: command 'python manage.py seed_demo' — fills the site with demo citizens and complaints.
# =============================================================================
"""
Fill the app with believable demo data: citizens, complaints with photos, timelines, admin notes,
upvotes, ratings and notifications, spread over the last month.

    python manage.py seed_demo            # add demo data (skips if it already exists)
    python manage.py seed_demo --reset    # remove earlier demo data and create it again

All people, phone numbers and complaints are fictional. Demo citizens are marked by a username
that starts with "demo-", so --reset removes only them (and their complaints and photos).
Every demo citizen signs in with the password in DEMO_PASSWORD.
"""

import os
import random
from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Notification, User, Ward
from complaints.demo_photos import make as make_photos
from complaints.models import Category, Complaint, ComplaintUpdate, Upvote

DEMO_PASSWORD = "Saaf@Demo2026"

CITIZENS = [
    ("Priya", "Sharma"), ("Rahul", "Verma"), ("Ananya", "Iyer"), ("Mohammed", "Arif"), ("Sneha", "Patil"),
    ("Vikram", "Chauhan"), ("Neha", "Gupta"), ("Arjun", "Reddy"), ("Fatima", "Khan"), ("Rohit", "Yadav"),
    ("Kavya", "Nair"), ("Aditya", "Joshi"), ("Pooja", "Mishra"), ("Harpreet", "Kaur"), ("Imran", "Qureshi"),
    ("Meera", "Pillai"), ("Suresh", "Tiwari"), ("Divya", "Saxena"), ("Amit", "Choudhary"), ("Ritu", "Agarwal"),
    ("Nikhil", "Dubey"), ("Shabnam", "Ansari"), ("Gaurav", "Malviya"), ("Lakshmi", "Menon"), ("Deepak", "Rathore"),
    ("Sana", "Siddiqui"), ("Karan", "Mehta"), ("Anjali", "Bhatt"),
]
MAIL = ["gmail.com", "gmail.com", "gmail.com", "yahoo.in", "outlook.com", "rediffmail.com"]

# ward number -> (pincode, lat, lng, streets, landmarks)
PLACES = {
    1: ("462001", 23.2635, 77.4040, ["Collectorate Road", "Lane 2, Civil Lines", "Court Road", "Kotwali Marg"], ["near District Court gate", "opposite SBI ATM", "behind Collectorate parking"]),
    2: ("462023", 23.2790, 77.3920, ["Gali No. 4, Gandhi Nagar", "Main Market Road", "Sector B, Gandhi Nagar", "Airport Road service lane"], ["near Hanuman Mandir", "next to Gupta Kirana Store", "opposite Gandhi Nagar Thana"]),
    3: ("462016", 23.2330, 77.4310, ["Shastri Colony Block C", "Shiv Mandir Road", "Lane 7, Shastri Colony", "Sabzi Mandi Road"], ["behind Sabzi Mandi", "near Shiv Mandir", "opposite Govt. Primary School"]),
    4: ("462003", 23.2470, 77.4390, ["Nehru Nagar Main Road", "Gali No. 2, Nehru Nagar", "Kolar Link Road", "Bus Stand Road"], ["near Nehru Nagar bus stop", "next to Sharma Medical", "opposite Community Hall"]),
    5: ("462001", 23.2668, 77.4136, ["Platform 1 approach road", "Station Road", "Chhola Road crossing", "Bharat Talkies Road"], ["near Railway Station gate 2", "opposite Bharat Talkies", "next to auto stand"]),
    6: ("462001", 23.2690, 77.4010, ["Chowk Bazaar", "Ibrahimpura Gali", "Peer Gate Road", "Jama Masjid Road"], ["near Peer Gate", "behind Chowk Bazaar", "near Moti Masjid"]),
    7: ("462021", 23.2190, 77.4180, ["Indira Colony Phase 2", "Gali No. 9, Indira Colony", "Ayodhya Bypass service road", "Park Road"], ["near Indira Park", "opposite Anganwadi Kendra", "next to water tank"]),
    8: ("462016", 23.2290, 77.4420, ["Shivaji Nagar 10 No. Market", "Lane 3, Shivaji Nagar", "Link Road No. 1", "Bittan Market Road"], ["near 10 No. stop", "behind Bittan Market", "opposite Shivaji Park"]),
    9: ("462011", 23.2460, 77.4680, ["Industrial Area Sector D", "Factory Road", "Govindpura Main Road", "Transport Nagar Gali"], ["near BHEL gate 4", "opposite truck parking", "behind Govindpura ITI"]),
    10: ("462026", 23.2010, 77.4330, ["University Road", "Hostel Lane", "Campus Back Gate Road", "Professors Colony"], ["near University back gate", "opposite Girls Hostel", "next to canteen"]),
}

TITLES = {
    "garbage-pile": ["Garbage heap on the roadside", "Huge pile of waste near the market", "Kachra dumped on empty plot", "Rotting garbage outside shops", "Waste pile blocking footpath"],
    "overflowing-dustbin": ["Community bin overflowing", "Dustbin full for 3 days", "Bin not emptied, waste on road", "Overflowing dhalao near colony", "Garbage spilling out of big bin"],
    "blocked-drain": ["Naali choked, water on road", "Blocked drain near the school", "Sewer overflow after rain", "Drain full of plastic", "Water logging due to choked drain"],
    "burning-garbage": ["Someone burning garbage in the open", "Smoke from burning kachra", "Waste being burnt every evening", "Plastic burning near houses"],
    "dead-animal": ["Dead dog on the road", "Dead cow near the market", "Carcass lying since morning"],
    "construction-debris": ["Malba dumped on the road", "Construction debris blocking lane", "Bricks and rubble left on footpath", "Building waste dumped on park side"],
    "dirty-public-toilet": ["Public toilet very dirty", "No water in public toilet", "Toilet block not cleaned for days", "Sulabh-style toilet stinking badly"],
    "street-not-swept": ["Street not swept for a week", "Market road full of litter", "Leaves and plastic all over the lane", "Sweeper has not come since Monday"],
}

DESCRIPTIONS = {
    "garbage-pile": [
        "There is a big heap of household waste {where}. It has been lying here for {days} days and stray dogs keep spreading it on the road. The smell is very bad in the evening.",
        "Shopkeepers and residents are dumping kachra {where}. Nobody has lifted it this week. Please send the team and also put a board so people stop dumping here.",
        "Plastic bags, food waste and thermocol are piled up {where}. Kids walk past this to school every morning. Please clean it soon.",
    ],
    "overflowing-dustbin": [
        "The big green bin {where} is completely full and garbage is falling on the road. It was last emptied {days} days ago. Cows are eating plastic from it.",
        "Community dustbin {where} overflows every day by noon. Please increase pickup to twice a day, the waste spreads all over the lane.",
    ],
    "blocked-drain": [
        "The naali {where} is fully choked with plastic and silt. Dirty water is standing on the road and mosquitoes are breeding. Two-wheelers are slipping here.",
        "After last night's rain the drain {where} overflowed and sewage water entered the lane. It needs desilting urgently.",
    ],
    "burning-garbage": [
        "Someone sets fire to the garbage {where} almost every evening. The smoke enters our houses and elderly people are having trouble breathing.",
        "Plastic waste is being burnt {where}. Thick black smoke since 7 pm. Please stop this and lift the waste so there is nothing to burn.",
    ],
    "dead-animal": [
        "A dead animal is lying {where} since early morning. It is starting to smell and is a health risk. Please remove it quickly.",
    ],
    "construction-debris": [
        "Someone has dumped malba (bricks, sand and cement waste) {where}. Half the road is blocked and there was a near accident yesterday.",
        "Construction waste from a nearby building is dumped {where} for {days} days. Please remove it and fine the builder.",
    ],
    "dirty-public-toilet": [
        "The public toilet {where} has not been cleaned for {days} days. There is no water in the tank and the floor is very dirty. Women are not able to use it.",
        "Toilet block {where} is stinking and the doors are broken. Please clean it and fix the water supply.",
    ],
    "street-not-swept": [
        "The road {where} has not been swept for about a week. Plastic, paper and leaves are all over. Please send the safai karmachari regularly.",
        "Market area {where} is full of litter after the weekly bazaar. It was not swept the next day.",
    ],
}

PROGRESS_NOTES = [
    "Team assigned. Garbage vehicle will reach by evening.",
    "Safai team from the ward office is on the way.",
    "Supervisor visited the spot. JCB requested for lifting.",
    "Desilting team scheduled for tomorrow morning.",
    "Work started. Will update with photo once done.",
]
DONE_NOTES = [
    "Waste lifted, area swept and lime powder sprayed.",
    "Bin emptied and washed. Pickup increased to twice a day.",
    "Drain desilted and water cleared from the road.",
    "Debris removed with JCB. Builder has been issued a notice.",
    "Toilet cleaned and water supply restored.",
    "Road swept and litter collected. Sweeper roster updated.",
]
REJECT_NOTES = [
    "This spot is inside private property. The owner has been informed to clean it.",
    "Duplicate of an earlier complaint at the same spot, which is already being handled.",
    "The photo does not show the reported problem. Please file again with a clear photo of the spot.",
]
REOPEN_NOTES = [
    "Garbage was dumped again at the same place the next morning.",
    "Only half the pile was removed, the rest is still lying there.",
]
FEEDBACK = {
    5: ["Very quick action, thank you team!", "Cleaned the same day. Great work.", "Excellent, the lane looks clean now.", "Superb, didn't expect such fast work."],
    4: ["Good work, took a little time but done properly.", "Cleaned well. Please keep checking this spot.", "Thank you, much better now."],
    3: ["Cleaned, but it took longer than promised.", "Okay work, some waste still left on the side."],
    2: ["Took too long and the spot is still not fully clean."],
}


class Command(BaseCommand):
    help = "Add realistic demo citizens, complaints, photos, timelines and ratings."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Remove earlier demo data first.")
        parser.add_argument("--complaints", type=int, default=64)

    def handle(self, *args, **opts):
        call_command("setup_city", verbosity=0)
        demo = User.objects.filter(username__startswith="demo-")
        if demo.exists():
            if not opts["reset"]:
                self.stdout.write(self.style.WARNING("Demo data already exists. Use --reset to create it again."))
                return
            self._remove(demo)
        admin = User.objects.filter(role=User.Role.ADMIN).order_by("id").first()
        if admin is None:
            self.stdout.write(self.style.ERROR("Create the admin account first (createsuperuser)."))
            return
        with transaction.atomic():
            n = self._seed(admin, opts["complaints"])
        self.stdout.write(self.style.SUCCESS(
            f"Demo data ready: {len(CITIZENS)} citizens, {n} complaints. Citizens sign in with password {DEMO_PASSWORD}."
        ))

    # ------------------------------------------------------------------ remove
    def _remove(self, demo):
        files = []
        for c in Complaint.objects.filter(user__in=demo):
            files += [f.path for f in (c.photo, c.after_photo) if f]
        codes = list(Complaint.objects.filter(user__in=demo).values_list("code", flat=True))
        Notification.objects.filter(link__in=[f"/admin-panel/complaints/{c}/" for c in codes]).delete()
        demo.delete()
        for p in files:
            if os.path.isfile(p):
                os.remove(p)
        self.stdout.write(f"Removed earlier demo data ({len(codes)} complaints, {len(files)} photos).")

    # ------------------------------------------------------------------ create
    def _seed(self, admin, how_many):
        rng = random.Random(2026)
        now = timezone.now()
        wards = {w.number: w for w in Ward.objects.all()}
        cats = {c.slug: c for c in Category.objects.filter(is_active=True)}

        people = []
        used_phones = set(User.objects.exclude(phone="").values_list("phone", flat=True))
        for i, (first, last) in enumerate(CITIZENS):
            ward = wards[(i % 10) + 1]
            while True:
                phone = str(rng.choice([6, 7, 8, 9])) + "".join(str(rng.randint(0, 9)) for _ in range(9))
                if phone not in used_phones:
                    used_phones.add(phone)
                    break
            email = f"{first.lower()}.{last.lower()}{rng.choice(['', str(rng.randint(10, 99)), '.bpl'])}@{rng.choice(MAIL)}"
            u = User.objects.create_user(
                username=f"demo-{first.lower()}-{last.lower()}", email=email, password=DEMO_PASSWORD,
                first_name=first, last_name=last, phone=phone, ward=ward,
            )
            User.objects.filter(pk=u.pk).update(date_joined=now - timedelta(days=rng.randint(32, 75), hours=rng.randint(0, 23)))
            people.append(u)

        # Weighted mix that looks like a real month in a city.
        slugs = list(cats)
        weights = {"garbage-pile": 22, "overflowing-dustbin": 18, "blocked-drain": 14, "street-not-swept": 12,
                   "construction-debris": 10, "burning-garbage": 8, "dirty-public-toilet": 9, "dead-animal": 4}
        plan = []
        for _ in range(how_many):
            slug = rng.choices(slugs, weights=[weights.get(s, 8) for s in slugs])[0]
            sla_h = cats[slug].sla_hours
            r = rng.random()
            status = ("RESOLVED" if r < 0.5 else "IN_PROGRESS" if r < 0.68 else "RECEIVED" if r < 0.86 else "REJECTED" if r < 0.94 else "REOPENED")
            # Open complaints are mostly still inside their deadline; about one in five has slipped.
            if status in ("RECEIVED", "IN_PROGRESS"):
                late = rng.random() < 0.2
                share = rng.uniform(1.1, 1.8) if late else rng.uniform(0.1 if status == "RECEIVED" else 0.3, 0.85)
                created = now - timedelta(hours=max(1.0, sla_h * share))
            else:
                created = now - timedelta(days=rng.uniform(2, 31))
            plan.append((created, status, slug))
        plan.sort()

        for idx, (created, status, slug) in enumerate(plan):
            cat = cats[slug]
            owner = rng.choice(people)
            ward = owner.ward if rng.random() < 0.8 else rng.choice(list(wards.values()))
            pin, lat, lng, streets, marks = PLACES[ward.number]
            street, mark = rng.choice(streets), rng.choice(marks)
            where = f"on {street}, {mark}"
            title = rng.choice(TITLES[slug])
            desc = rng.choice(DESCRIPTIONS[slug]).format(where=where, days=rng.randint(2, 5))
            priority = "HIGH" if cat.sla_hours <= 12 or rng.random() < 0.2 else rng.choice(["MEDIUM", "MEDIUM", "LOW"])

            # timeline
            sla = timedelta(hours=cat.sla_hours)
            steps = [("RECEIVED", created, owner, "Complaint filed")]
            if status in ("IN_PROGRESS", "RESOLVED", "REOPENED"):
                t = created + timedelta(minutes=rng.randint(25, 300))
                steps.append(("IN_PROGRESS", min(t, now - timedelta(minutes=10)), admin, rng.choice(PROGRESS_NOTES)))
            resolved_at = None
            if status in ("RESOLVED", "REOPENED"):
                resolved_at = created + sla * rng.uniform(0.35, 1.25)
                resolved_at = min(resolved_at, now - timedelta(hours=2))
                steps.append(("RESOLVED", resolved_at, admin, rng.choice(DONE_NOTES)))
            if status == "REOPENED":
                steps.append(("REOPENED", resolved_at + timedelta(hours=rng.uniform(8, 30)), owner, rng.choice(REOPEN_NOTES)))
            if status == "REJECTED":
                steps.append(("REJECTED", created + timedelta(hours=rng.uniform(2, 20)), admin, rng.choice(REJECT_NOTES)))

            stamp = lambda t: timezone.localtime(t).strftime("%d/%m/%Y  %H:%M")
            before, after = make_photos(slug, 1000 + idx, stamp(created), stamp(resolved_at) if resolved_at else None)

            c = Complaint(
                user=owner, category=cat, ward=ward, title=title, description=desc,
                address=f"{street}, {ward.name}", landmark=mark[:100], pincode=pin,
                latitude=Decimal(str(round(lat + rng.uniform(-0.006, 0.006), 6))),
                longitude=Decimal(str(round(lng + rng.uniform(-0.006, 0.006), 6))),
                priority=priority, status=status,
            )
            c.photo.save(f"spot-{idx + 1}.jpg", ContentFile(before), save=False)
            if after and status != "REOPENED":
                c.after_photo.save(f"clean-{idx + 1}.jpg", ContentFile(after), save=False)
            if status == "REJECTED":
                c.admin_note = steps[-1][3]
            elif status in ("RESOLVED", "IN_PROGRESS"):
                c.admin_note = steps[-1][3]
            if status == "REOPENED":
                c.reopen_count = 1
            c.save()

            rating = feedback = None
            if status == "RESOLVED" and rng.random() < 0.72:
                late = resolved_at > created + sla
                rating = rng.choice([3, 4, 4]) if late else rng.choice([4, 5, 5, 5])
                if rng.random() < 0.08:
                    rating = 2
                feedback = rng.choice(FEEDBACK[rating]) if rng.random() < 0.8 else ""
            Complaint.objects.filter(pk=c.pk).update(
                created_at=created, updated_at=steps[-1][1], resolved_at=resolved_at if status == "RESOLVED" else None,
                rating=rating, feedback=feedback or "",
            )

            for st, at, by, note in steps:
                u = ComplaintUpdate.objects.create(complaint=c, status=st, by=by, note=note)
                ComplaintUpdate.objects.filter(pk=u.pk).update(created_at=at)
                self._notify_for(c, st, at, owner, admin, note, now)

            # neighbours who face the same problem
            neighbours = [p for p in people if p.ward_id == ward.id and p != owner] + rng.sample([p for p in people if p != owner], 3)
            for p in rng.sample(neighbours, k=min(len(neighbours), rng.choice([0, 1, 1, 2, 3, 4, 6]))):
                v, made = Upvote.objects.get_or_create(complaint=c, user=p)
                if made:
                    Upvote.objects.filter(pk=v.pk).update(created_at=created + timedelta(hours=rng.uniform(1, 30)))
        return len(plan)

    def _notify_for(self, c, status, at, owner, admin, note, now):
        texts = {
            "IN_PROGRESS": (owner, "Work started", f"The team is working on {c.code}.", c.get_absolute_url(), "truck"),
            "RESOLVED": (owner, "Spot cleaned", f"{c.code} is marked clean. See the after photo and rate the work.", c.get_absolute_url(), "check"),
            "REJECTED": (owner, "Complaint closed", f"{c.code} was rejected: {note}", c.get_absolute_url(), "x"),
            "RECEIVED": (admin, f"New complaint {c.code}", f"{c.category.name} · {c.ward}", c.get_admin_url(), "inbox"),
            "REOPENED": (admin, f"{c.code} reopened", note, c.get_admin_url(), "alert"),
        }
        user, title, body, link, icon = texts[status]
        if user == admin and now - at > timedelta(days=4):
            return                                   # keep the admin inbox to recent items
        n = Notification.objects.create(user=user, title=title, body=body[:255], link=link, icon=icon,
                                        is_read=now - at > timedelta(days=2))
        Notification.objects.filter(pk=n.pk).update(created_at=at)
