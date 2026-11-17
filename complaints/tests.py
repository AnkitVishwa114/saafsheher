# =============================================================================
# FILE: complaints/tests.py
# WHAT IS HERE: automatic tests. Run with 'python manage.py test'.
# =============================================================================
import io
import shutil
import tempfile
from datetime import timedelta

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from accounts.models import User, Ward

from .models import Category, Complaint

PW = "Clean@City2026"
MEDIA = tempfile.mkdtemp()


def photo(name="spot.jpg", size=(640, 480), fmt="JPEG"):
    buf = io.BytesIO()
    Image.new("RGB", size, (90, 160, 90)).save(buf, fmt)
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=MEDIA)
class SaafSheharTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_city", verbosity=0)
        cls.ward = Ward.objects.get(number=5)
        cls.cat = Category.objects.get(slug="garbage-pile")
        cls.admin = User.objects.create_superuser(username="boss@city.in", email="boss@city.in", password=PW, first_name="Boss")

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        cache.clear()

    # ------------------------------------------------------------ helpers
    def signup(self, email="riya@mail.in", phone="9876543210", password=PW, **extra):
        data = {"first_name": "Riya", "last_name": "Sharma", "email": email, "phone": phone, "ward": self.ward.pk,
                "password1": password, "password2": password, "agree": "on"}
        data.update(extra)
        return self.client.post(reverse("accounts:signup"), data)

    def file(self, **extra):
        data = {"photo": photo(), "category": self.cat.pk, "title": "Garbage pile near bus stop",
                "description": "Huge pile of plastic and food waste, smelling for three days.", "priority": "HIGH",
                "ward": self.ward.pk, "address": "Station Road, near platform gate", "landmark": "Bus stop",
                "pincode": "462001", "latitude": "23.259900", "longitude": "77.412600"}
        data.update(extra)
        return self.client.post(reverse("complaints:new"), data)

    # ------------------------------------------------------------ accounts
    def test_signup_and_login_with_email_case_insensitive(self):
        self.assertEqual(self.signup().status_code, 302)
        self.client.logout()
        r = self.client.post(reverse("accounts:login"), {"email": "RIYA@MAIL.IN", "password": PW})
        self.assertRedirects(r, reverse("core:dashboard"), fetch_redirect_response=False)

    def test_weak_passwords_are_rejected(self):
        for bad in ["password", "abcdefgh1", "ABCDEFGH1!", "Abcdefgh!", "Abc1!", "Aaaa1111!!"]:
            r = self.signup(email=f"x{len(bad)}{bad[:2]}@m.in", password=bad)
            self.assertEqual(r.status_code, 200, bad)
        self.assertFalse(User.objects.filter(role="USER").exists())

    def test_signup_field_validation(self):
        self.assertEqual(self.signup(phone="12345").status_code, 200)               # bad phone
        self.assertEqual(self.signup(password2="Other@Pass99").status_code, 200)   # mismatch
        self.assertEqual(self.signup(first_name="R2D2").status_code, 200)          # digits in name
        self.signup()
        self.client.logout()
        self.assertEqual(self.signup(email="RIYA@mail.in", phone="9123456780").status_code, 200)  # duplicate email
        self.assertEqual(self.signup(email="new@mail.in").status_code, 200)        # duplicate phone
        self.assertEqual(User.objects.filter(role="USER").count(), 1)

    def test_login_lockout_after_five_failures(self):
        self.signup()
        self.client.logout()
        for _ in range(5):
            self.client.post(reverse("accounts:login"), {"email": "riya@mail.in", "password": "Wrong@123"})
        r = self.client.post(reverse("accounts:login"), {"email": "riya@mail.in", "password": PW})
        self.assertContains(r, "Too many wrong attempts")

    # ------------------------------------------------------------ complaints
    def test_full_flow_file_progress_resolve_rate_reopen(self):
        self.signup()
        self.assertEqual(self.file().status_code, 302)
        c = Complaint.objects.get()
        self.assertEqual(c.code, f"SS-{timezone.localdate().year}-0001")
        self.client.logout()

        self.client.login(username="boss@city.in", password=PW)
        url = reverse("panel:complaint", args=[c.code])
        self.client.post(url, {"status": "IN_PROGRESS", "priority": "HIGH", "note": "Team sent"})
        # Cleaned without an after photo is refused
        self.client.post(url, {"status": "RESOLVED", "priority": "HIGH"})
        c.refresh_from_db()
        self.assertEqual(c.status, "IN_PROGRESS")
        self.client.post(url, {"status": "RESOLVED", "priority": "HIGH", "after_photo": photo("after.jpg")})
        c.refresh_from_db()
        self.assertEqual(c.status, "RESOLVED")
        self.assertTrue(c.after_photo and c.resolved_at)
        self.client.logout()

        self.client.post(reverse("accounts:login"), {"email": "riya@mail.in", "password": PW})
        self.client.post(reverse("complaints:rate", args=[c.code]), {"rating": 4, "feedback": "Quick work"})
        self.client.post(reverse("complaints:rate", args=[c.code]), {"rating": 1})   # second rating ignored
        c.refresh_from_db()
        self.assertEqual(c.rating, 4)
        self.client.post(reverse("complaints:reopen", args=[c.code]), {"reason": "Garbage is back again today"})
        c.refresh_from_db()
        self.assertEqual(c.status, "REOPENED")
        self.assertEqual(list(c.updates.values_list("status", flat=True)), ["RECEIVED", "IN_PROGRESS", "RESOLVED", "REOPENED"])
        self.assertEqual(c.user.notifications.count(), 2)  # work started, cleaned

    def test_photo_validation(self):
        self.signup()
        bad_files = [
            SimpleUploadedFile("doc.pdf", b"%PDF-1.4", content_type="application/pdf"),          # wrong type
            SimpleUploadedFile("fake.jpg", b"not really an image", content_type="image/jpeg"),   # fake image
            photo("tiny.jpg", size=(80, 80)),                                                     # too small
        ]
        for f in bad_files:
            self.assertEqual(self.file(photo=f).status_code, 200, f.name)
        self.assertFalse(Complaint.objects.exists())

    def test_text_and_location_validation(self):
        self.signup()
        for extra in [{"title": "Short"}, {"title": "GARBAGE EVERYWHERE HERE"}, {"description": "too short"},
                      {"pincode": "012345"}, {"address": "abc"}, {"latitude": "51.5", "longitude": "-0.12"},
                      {"latitude": "23.25", "longitude": ""}]:
            self.assertEqual(self.file(**extra).status_code, 200, extra)
        self.assertFalse(Complaint.objects.exists())

    def test_duplicate_and_daily_limit(self):
        self.signup()
        self.file()
        self.assertEqual(self.file().status_code, 200)  # same category + ward today = duplicate
        cats = list(Category.objects.exclude(pk=self.cat.pk)[:5])
        for cat in cats[:4]:
            self.file(category=cat.pk)
        self.assertEqual(Complaint.objects.count(), 5)
        self.assertContains(self.file(category=cats[4].pk), "up to 5 complaints")

    def test_reject_needs_reason_and_upvote_rules(self):
        self.signup()
        self.file()
        c = Complaint.objects.get()
        # owner cannot upvote own complaint
        r = self.client.post(reverse("complaints:upvote", args=[c.code]), headers={"x-requested-with": "fetch"})
        self.assertEqual(r.status_code, 400)
        self.client.logout()
        self.signup(email="aman@mail.in", phone="9123456780")
        r = self.client.post(reverse("complaints:upvote", args=[c.code]), headers={"x-requested-with": "fetch"})
        self.assertEqual(r.json()["count"], 1)
        r = self.client.post(reverse("complaints:upvote", args=[c.code]), headers={"x-requested-with": "fetch"})
        self.assertEqual(r.json()["count"], 0)  # toggles off
        self.client.logout()
        self.client.login(username="boss@city.in", password=PW)
        url = reverse("panel:complaint", args=[c.code])
        self.client.post(url, {"status": "REJECTED", "priority": "LOW", "note": "no"})
        c.refresh_from_db()
        self.assertEqual(c.status, "RECEIVED")
        self.client.post(url, {"status": "REJECTED", "priority": "LOW", "note": "This location is private property."})
        c.refresh_from_db()
        self.assertEqual(c.status, "REJECTED")

    def test_overdue_and_roles(self):
        self.signup()
        self.file()
        c = Complaint.objects.get()
        Complaint.objects.filter(pk=c.pk).update(created_at=timezone.now() - timedelta(hours=self.cat.sla_hours + 1))
        c.refresh_from_db()
        self.assertTrue(c.is_overdue)
        self.assertEqual(self.client.get(reverse("panel:dashboard")).status_code, 403)   # citizen can't open admin
        self.client.logout()
        self.client.login(username="boss@city.in", password=PW)
        self.assertEqual(self.client.get(reverse("complaints:new")).status_code, 403)    # admin can't file
        self.assertContains(self.client.get(reverse("panel:complaints") + "?overdue=1"), c.code)
        self.assertEqual(self.client.get(reverse("panel:export")).status_code, 200)

    def test_public_pages(self):
        self.signup()
        self.file()
        code = Complaint.objects.get().code
        self.client.logout()
        for url in [reverse("core:home"), reverse("core:leaderboard"), reverse("accounts:login"), reverse("accounts:signup")]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertContains(self.client.get(reverse("core:track") + f"?code={code}"), code)
        self.assertContains(self.client.get(reverse("core:track") + "?code=hello"), "look like SS-")

    def test_admin_login_is_separate_from_citizen_login(self):
        self.signup()
        self.client.logout()
        # Signed-out visit to the panel goes to /admin/, not the citizen login.
        r = self.client.get(reverse("panel:dashboard"))
        self.assertRedirects(r, reverse("admin_login") + "?next=" + reverse("panel:dashboard"), fetch_redirect_response=False)
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        # A citizen can't use the admin login, and an admin can't use the citizen login.
        r = self.client.post(reverse("admin_login"), {"email": "riya@mail.in", "password": PW})
        self.assertContains(r, "only for municipal admins")
        self.assertNotIn("_auth_user_id", self.client.session)
        r = self.client.post(reverse("accounts:login"), {"email": "boss@city.in", "password": PW})
        self.assertContains(r, "admin login page")
        self.assertNotIn("_auth_user_id", self.client.session)
        # The admin signs in at /admin/ and lands on the panel; signing out returns to /admin/.
        r = self.client.post(reverse("admin_login"), {"email": "BOSS@city.in", "password": PW})
        self.assertRedirects(r, reverse("panel:dashboard"))
        r = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(r, reverse("admin_login"))
