# SaafShehar — Kachra Shikayat (SIH26195)

SaafShehar is a Django web app for reporting garbage and sanitation problems in a city.
A citizen takes a photo of the problem, adds the location and files a complaint. The municipal
team updates its status and must clean it within a fixed deadline, with an "after" photo as proof.
Wards are ranked publicly by how many of their complaints actually got cleaned.

## Roles

| Role | What they can do |
|---|---|
| **Citizen** | Sign up, report a problem (4 steps: photo → category → location → review), track status, upvote complaints they also face, rate the clean-up, reopen within 7 days, get notifications |
| **Municipal admin** | Separate login, dashboard with charts, filter and update complaints, upload the "after" photo, reject with a reason, manage wards, categories and citizens, export CSV |

## Features

- Complaint numbers like `SS-2026-0001` and a full timeline of every status change
- Deadline (SLA) per category, overdue flags and priority levels
- Workflow: Received → Work in progress → Cleaned, or Rejected; a citizen can reopen once
- Before/after photo comparison slider, ratings and feedback
- Upvotes ("I face this too") and an "Around me" feed of open complaints
- Public pages: home, track a complaint by number (no login), ward ranking
- Admin panel: KPIs, 14-day trend, category and ward charts, live ticker, Ctrl+K command palette
- Notifications for both citizens and admins
- Installable as an app (PWA), mobile bottom tab bar
- Scroll animations (GSAP ScrollTrigger)

## Validation and rules

- **Password:** 8+ characters with uppercase, lowercase, number and symbol; no spaces; not similar to name or email
- **Login:** email (any case) + password; account locked for 15 minutes after 5 wrong attempts; citizens and admins use separate login pages
- **Sign-up:** valid 10-digit Indian mobile (starts with 6–9), unique email and phone, letters-only name
- **Photo:** JPG / PNG / WEBP only, up to 5 MB, at least 200 px, must be a real image
- **Complaint:** title 8+ characters, description 20+, address 10+, 6-digit PIN code, GPS inside India
- **Limits:** 5 complaints per citizen in 24 hours; same category + ward within 24 hours counts as a duplicate
- **Admin:** "Cleaned" needs an after photo; "Rejected" needs a reason of 10+ characters

All limits are set at the bottom of `saafshehar/settings.py` (`SS_...`).

## Tech stack

- Python 3, Django 5.2, SQLite
- Pillow (image checks and demo photos)
- HTML templates, custom CSS, vanilla JavaScript
- Chart.js, GSAP + ScrollTrigger (bundled in `static/vendor/`)

## Project structure

```
saafshehar/        settings, root URLs
accounts/          User (citizen / admin), Ward, Notification, validators, email login, login & sign-up views
complaints/        Category, Complaint, ComplaintUpdate, Upvote, forms, workflow (services.py),
                   citizen complaint views, demo data command, tests
core/              public pages, citizen dashboard, admin panel (panel.py), role decorators,
                   template tags, setup_city command
templates/         base layouts, partials, public/, accounts/, user/, panel/, error pages
static/            css/app.css, js/app.js, js/sw.js, img/, vendor/
```

## Database

| Table | Main fields |
|---|---|
| **User** | name, email (unique), phone (unique), role, ward |
| **Ward** | number, name, zone |
| **Category** | name, icon, colour, SLA hours, active |
| **Complaint** | code, user, category, ward, title, description, photo, after photo, address, landmark, PIN code, latitude/longitude, priority, status, admin note, rating, feedback, reopen count, created/resolved time |
| **ComplaintUpdate** | complaint, status, note, changed by, time (the timeline) |
| **Upvote** | complaint, user (one per user per complaint) |
| **Notification** | user, title, body, link, read |

## Main URLs

| URL | Page |
|---|---|
| `/` | Home |
| `/track/` | Track a complaint |
| `/leaderboard/` | Ward ranking |
| `/accounts/signup/`, `/accounts/login/` | Citizen sign-up and login |
| `/dashboard/` | Citizen home |
| `/complaints/new/` | Report a problem |
| `/complaints/mine/`, `/complaints/feed/` | My complaints, Around me |
| `/admin/` | Admin login |
| `/admin-panel/` | Admin panel |

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_city        # 8 categories and 10 wards
python manage.py createsuperuser   # admin account (asks for email and password)
python manage.py seed_demo         # optional demo data
python manage.py runserver
```

Then open http://127.0.0.1:8000. Admins sign in at `/admin/`.

## Demo data

```bash
python manage.py seed_demo            # 28 citizens and 64 complaints over the last month
python manage.py seed_demo --reset    # remove the demo data and create it again
```

Creates fictional citizens, complaints with before/after photos (drawn by `complaints/demo_photos.py`),
timelines, upvotes, ratings and notifications. Demo citizens sign in with their email and the
password `Saaf@Demo2026`. `--reset` removes only demo accounts (username starts with `demo-`).

## Tests

```bash
python manage.py test
```
