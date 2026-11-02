# TutorConnect

A platform where parents find verified tutors and an administrator coordinates every introduction. It also has a private job board for approved tutors, and lets administrators record requests received by telephone.

**Stack:** React 18 + TypeScript (Vite) · Django 5 + Django REST Framework · PostgreSQL (SQLite for quick local dev) · JWT authentication.

> **Status: written but not yet run.** The code was produced in an environment with no access to PyPI or npm, so nothing here has been installed, migrated, tested or built. The steps below are what you run to find out. Expect to fix some first-run errors; send them back and they get fixed.
> **Migrations are not generated yet** (needs Django). Step 3 creates them.

```
tutorconnect/
├─ backend/    Django + DRF API (accounts, catalog, tutors, tutor_requests, jobs, introductions,
│              inquiries, notifications, audit, reporting) + tests/
└─ frontend/   React + TypeScript single-page app
```

## Prerequisites
Python 3.11+, Node 20+, and (recommended) PostgreSQL 14+.

## 1. Backend setup
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # then edit .env
```
In `.env`: set `DJANGO_SECRET_KEY` (any long random string), keep `DJANGO_DEBUG=1` locally, and either
* **SQLite (quickest):** leave `DB_NAME` empty, or
* **PostgreSQL:** create a database and user, then fill in `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.
  ```sql
  CREATE USER tutorconnect WITH PASSWORD 'choose-a-password';
  CREATE DATABASE tutorconnect OWNER tutorconnect;
  ```

## 2. Generate migrations (first time only) and migrate
```bash
python manage.py makemigrations accounts catalog tutors tutor_requests jobs introductions inquiries notifications audit
python manage.py migrate
```
Commit the generated `*/migrations/0001_initial.py` files afterwards.

## 3. Reference data and the first administrator
```bash
python manage.py seed_reference_data      # subjects, grade levels, Addis Ababa areas (real reference data)
python manage.py createsuperuser          # asks for email, full name, password -> creates an Administrator
```
There is no public administrator sign-up. `createsuperuser` is the only way an administrator is created.

Optional, **development only** (refuses to run unless `DJANGO_DEBUG=1`): `python manage.py seed_demo_data` creates fake tutors, a demo parent and a demo admin (`admin@demo.test`, password printed by the command). Never run it against production data.

## 4. Run the tests
```bash
python manage.py test tests
```
Covers role permissions, tutor verification and public visibility, directory filters, requests (online and telephone), job publishing/applications/duplicates/closed jobs, introductions, and privacy (private documents, parent contact never in job listings, inquiry confidentiality). **Run these first.** They are the quickest way to find anything that needs fixing.

## 5. Run the apps
```bash
# terminal 1
cd backend && python manage.py runserver            # API on http://127.0.0.1:8000

# terminal 2
cd frontend
npm install
npm run typecheck                                   # optional but recommended on first run
npm run dev                                         # http://localhost:5173 (proxies /api to Django)
```

## Try the main flows
1. **Tutor:** register at `/register/tutor` → complete profile, add a qualification, upload a PDF/JPG/PNG → *Submit application*. Profile stays private.
2. **Administrator:** log in → *Tutor Applications* → open the tutor → download and verify the document → *Approve*. The tutor now appears in `/tutors` and can open the job board.
3. **Parent:** register at `/register` → *Request This Tutor* (or a general request) → track it in *My Requests*.
4. **Telephone request:** Admin → *Phone Inquiries* → *Record phone request* (all fields optional; save as draft if incomplete) → *Find matching tutors* or *Create job from request*.
5. **Job:** Admin → publish the job → approved tutor *Express Interest* → Admin reviews applicants (shortlist, select) → *Introductions* (record both parties' agreement, then share contact).

## Deployment guidance
* Set `DJANGO_DEBUG=0`, a strong `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `DJANGO_SECURE_SSL=1` (behind HTTPS).
* Use PostgreSQL. Run `python manage.py migrate` and `collectstatic`; serve with `gunicorn config.wsgi` behind nginx/Caddy.
* **Private files:** set `PRIVATE_MEDIA_ROOT` to a directory the web server does **not** serve. Credentials are only ever returned by the authenticated download endpoint. Back it up with the database.
* **Public files:** only profile photos use `MEDIA_ROOT`; serve that path from the web server in production (Django only serves it when `DEBUG=1`).
* Build the frontend with `npm run build` and serve `frontend/dist` as static files. Route unknown paths to `index.html` (single-page app). Set `VITE_API_URL` at build time if the API is on another origin.
* Rotate `DJANGO_SECRET_KEY` only knowingly: it invalidates all sessions.

## What is implemented
* Roles (parent, tutor, administrator) enforced in the backend; no public admin registration.
* Public tutor directory with database-side filters (gender, location, subject, grade, mode, experience, rate, availability day) and pagination; only approved + active tutors ever appear.
* Tutor registration → profile → qualifications → private document upload (type/size/content checks) → submit → administrator review (approve, reject, request info, suspend, reinstate) with reasons, history and audit log. Edits to credentials after approval are flagged for renewed review.
* Parent requests (minimal form), private inquiries, parent dashboard, request status tracking.
* Administrator-recorded telephone requests (incomplete drafts allowed), assignment, status workflow, outcomes.
* Jobs separate from requests; create-from-request prefill (private details are not copied); private job board for approved tutors; applications with duplicate prevention and deliberate resubmission; shortlist/select/finalize.
* Matching suggestions with reasons and concerns; introductions with recorded consent from both parties before any contact is shared.
* In-app notifications, audit logs, status histories, operational reports, admin settings for subjects/grades/locations.

## Known limitations / not done
* **Never run or tested end to end** (see top). Migrations need generating.
* No email verification and no email delivery by default (settings exist; notifications are in-app only). Telephone/SMS is not integrated.
* No identity or background checks. The "verified" badge only means an administrator reviewed a supporting document; the UI says so.
* Reviews and ratings (spec section 19, marked optional) are not implemented.
* No dedicated "platform settings" key-value store; featured tutors are a fixed top-6 by experience.
* JWTs are kept in `localStorage` for simplicity. For stricter XSS protection move them to HttpOnly cookies. Refresh tokens are not blacklisted on logout.
* Tutors' job board shows open jobs only; the job-status filter listed in the spec is therefore not offered to tutors.
* Spec asked for Django templates + Bootstrap; this build uses React + TypeScript with a custom stylesheet, as requested.
* Reconstructed files: `backend/config/settings.py`, `config/urls.py`, `config/wsgi.py`, `manage.py`, `requirements.txt` and `.env.example` were accidentally overwritten during development and rebuilt from compiled caches. Values marked "(reconstructed)" in `settings.py` (refresh-token rotation, test password hasher) were inferred; review them.
