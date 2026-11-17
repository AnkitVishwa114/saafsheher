# SaafShehar — Kachra Shikayat (SIH26195)

A Django web app where citizens report garbage problems with a photo and location, and the
municipal team cleans them up within a fixed deadline, with photo proof.

## Roles

| Role | What they can do |
|---|---|
| **User (citizen)** | Sign up, report a problem (4-step form: photo → location → details → review), track status, upvote nearby complaints, rate the clean-up, reopen within 7 days, get notifications |
| **Admin (municipal)** | Dashboard with charts, filter and update complaints, upload "after" photo, reject with reason, manage wards, categories and users, export CSV |

## Main features

- Complaint codes like `SS-2026-0001`, timeline of every status change
- SLA per category, overdue flags, priority
- Photo checks (real image, max 5 MB, min 200 px), daily limit of 5, duplicate check (24 h)
- Strong password rules, email login, account lock after 5 wrong passwords (15 min)
- Public pages: home, track a complaint by code, ward ranking
- Installable as an app (PWA), works on phones with a bottom tab bar
- Scroll motion with GSAP ScrollTrigger (pinned "how it works" cards, word reveals, parallax)

## Project structure

```
saafshehar/        settings, root urls
accounts/          User (role USER/ADMIN), Ward, Notification, validators, email login backend
complaints/        Category, Complaint, ComplaintUpdate, Upvote, forms, services, tests
core/              public pages, citizen dashboard, admin panel (panel.py), template tags,
                   setup_city management command
templates/         base, partials, public/, accounts/, user/, panel/, error pages
static/            css/app.css, js/app.js, js/sw.js, img/, vendor/ (gsap, ScrollTrigger, chart.js)
media/             uploaded photos
```

## Database (main tables)

- **User** — name, email (unique), phone, role, ward
- **Ward** — name, number, zone
- **Category** — name, icon, colour, SLA hours, active
- **Complaint** — code, user, category, ward, title, description, photo, after photo, address,
  pincode, lat/lng, priority, status, admin note, rating, feedback, reopen count, resolved at
- **ComplaintUpdate** — complaint, status, note, by, time (the timeline)
- **Upvote** — user + complaint (unique together)
- **Notification** — user, message, link, read

## Where is what (quick answers for the viva)

| If sir asks about… | File | Function / class |
|---|---|---|
| Database tables | `accounts/models.py`, `complaints/models.py` | `User`, `Ward`, `Notification`, `Category`, `Complaint`, `ComplaintUpdate`, `Upvote` |
| Complaint number SS-2026-0001 | `complaints/models.py` | `Complaint.save()` |
| Deadline / overdue logic | `complaints/models.py` | `due_at`, `is_overdue`, `hours_left` |
| Password rules | `accounts/validators.py` | `StrongPasswordValidator` (switched on in `settings.py`) |
| Phone / PIN / name rules | `accounts/validators.py` | `phone_validator`, `pincode_validator`, `name_validator` |
| Sign-up validation | `accounts/forms.py` | `SignupForm` (`clean_email`, `clean_phone`, `clean`) |
| Login + 15-minute lock | `accounts/forms.py` | `LoginForm.clean()` |
| Login with email | `accounts/backends.py` | `EmailBackend.authenticate()` |
| Citizen login vs admin login | `accounts/views.py` | `login_view` (`/accounts/login/`), `admin_login` (`/admin/`) |
| Only admins can open admin pages | `core/decorators.py` | `admin_required`, `citizen_required` |
| Photo validation (type, 5 MB, real image) | `complaints/forms.py` | `validate_photo()` |
| Complaint form validation, 5-per-day limit, duplicates | `complaints/forms.py` | `ComplaintForm` (`clean_title`, `clean`) |
| "Cleaned" needs after photo, "Rejected" needs reason | `complaints/forms.py` | `StatusForm.clean()` |
| What happens when status changes (timeline + notification) | `complaints/services.py` | `file_complaint`, `change_status`, `reopen`, `rate`, `toggle_upvote` |
| Citizen pages | `complaints/views.py` | `new`, `mine`, `detail`, `rate`, `reopen`, `upvote`, `feed` |
| Admin panel pages | `core/panel.py` | `dashboard`, `complaints`, `complaint`, `export_csv`, `wards`, `categories`, `users`, `user_toggle` |
| Ward ranking formula | `core/views.py` | `ward_ranking()` |
| All business limits (5 MB, 5/day, 7 days, 15 min) | `saafshehar/settings.py` | `SS_...` settings at the bottom |
| All URLs | `saafshehar/urls.py` + each app's `urls.py` | |
| Front-end behaviour (animations, live checks) | `static/js/app.js` | section list at the top of the file |

Every Python file starts with a short `# FILE: … WHAT IS HERE …` block, every template starts with a
`{# PAGE: … view … URL … #}` note, and each function has a one-line plain-English comment above it.

## Run it

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_city        # loads 8 categories and 10 wards
python manage.py createsuperuser   # creates the admin account (asks for email and password)
python manage.py seed_demo         # optional: demo citizens, complaints and photos
python manage.py runserver
```

Open http://127.0.0.1:8000.

- **Citizens** sign up and sign in at `/accounts/signup/` and `/accounts/login/`.
- **Municipal admins** sign in only at **`/admin/`** (separate page, no sign-up). The admin account in the
  included database is `ankitvishwa114@gmail.com` (password kept separately).
- Each login refuses the other role, and signed-out visits to `/admin-panel/` go to `/admin/`.
- Django's built-in admin is at `/django-admin/`.

## Demo data

```bash
python manage.py seed_demo            # 28 citizens, 64 complaints over the last month
python manage.py seed_demo --reset    # wipe the demo data and create it again
```

Fills the app with fictional but realistic data: Indian names, ward-wise addresses and landmarks,
photos of each problem (drawn by `complaints/demo_photos.py`, with a cleaned "after" photo), full
timelines with admin notes, upvotes, ratings, feedback and notifications. Demo citizens sign in
with their email (see the Citizens page in the admin panel) and the password `Saaf@Demo2026`.
`--reset` removes only demo accounts (username starts with `demo-`), never real ones.

## Tests

```bash
python manage.py test
```
