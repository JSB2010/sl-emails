# Kent Denver Student Leadership Emails

This repo powers two production surfaces for Kent Denver Student Leadership:

- the public daily signage page at `/signage`
- the weekly sports/arts email review and delivery workflow at `/emails`

The current production entrypoint is Firebase Hosting in front of Cloud Run.

## System Overview

The live system is split across five pieces:

- Firebase Hosting serves the public hostname, caches static assets, and rewrites app traffic to Cloud Run.
- Cloud Run runs the Flask app in `src/sl_emails/web`.
- Firestore stores signage day snapshots, weekly drafts, admin settings, public request submissions, and activity logs.
- Google Apps Script owns cron-driven automation and Gmail delivery.
- GitHub Actions runs CI and deploys the app and hosting config from `main`.

## What The App Does

The runtime has four main responsibilities:

- Render the public signage page from Firestore-backed daily snapshots.
- Provide a Google-authenticated admin UI for weekly review, copy editing, approval, and send-state tracking.
- Accept public event requests that staff can approve into a week.
- Expose protected automation endpoints used by Apps Script for scheduled ingest, sender-output retrieval, activity logging, and signage refresh.

## Weekly Automation Flow

1. Every day at midnight in `America/Denver`, Apps Script calls `/api/signage/automation/days/<day-id>/refresh`.
2. Sunday at 8:00 AM MT, Apps Script calls `/api/emails/automation/weeks/<week-id>/scheduled-ingest`.
3. The app fetches athletics and arts sources, creates the draft week if it does not exist, and never overwrites an existing draft automatically.
4. Apps Script emails the admin/ops recipients a review link to `/emails?week=<YYYY-MM-DD>`.
5. Staff sign in with Google, review or edit the week, optionally generate Gemini copy, and approve it.
6. Every day at 4:00 PM MT, Apps Script decides whether anything should send that day:
   - Sunday sends the default week.
   - Monday through Thursday can send postponed weeks.
   - weeks marked `skip` are suppressed
7. Apps Script fetches `/api/emails/weeks/<week-id>/sender-output`, claims the week for sending, delivers both audience emails, and marks the week sent.
8. If a week is approved after its scheduled window, staff can use `Send Now` on `/emails`; the Flask app calls the Apps Script web app with the shared settings-backed automation key.

## Production Topology

- `firebase.json` rewrites all app traffic to the Cloud Run service `sl-emails` in `us-central1`.
- `firebase-hosting/` contains the Hosting-only assets, including long-cache icon copies.
- `Dockerfile` builds the same container image used by Cloud Run.
- `.github/workflows/deploy-main.yml` runs tests, deploys Cloud Run, deploys Firebase Hosting, and refreshes the current signage day.
- `deploy/cloudrun/service.template.yaml` is a reference manifest for the Cloud Run service.

## Key Routes

Public:

- `/` returns plain-text `OK`
- `/signage` renders the current Firestore signage snapshot
- `/_health` and `/healthz` return `{"ok": true}`
- `/request` serves the public event request form
- `/api/emails/requests` accepts public event submissions

Admin:

- `/login` starts Google sign-in
- `/emails` serves the weekly review dashboard
- `/emails/settings` manages allowlist, notifications, and Apps Script delivery settings
- `/api/emails/settings` reads or updates admin settings
- `/api/emails/settings/test-apps-script` tests the Apps Script web app URL and key without sending email
- `/api/emails/weeks/<week-id>` reads or saves a weekly draft
- `/api/emails/weeks/<week-id>/preview` renders both audience outputs
- `/api/emails/weeks/<week-id>/source-refresh` refreshes source events while preserving custom events
- `/api/emails/weeks/<week-id>/approve` approves a week
- `/api/emails/weeks/<week-id>/manual-send` asks the Apps Script web app to send an approved, unsent week immediately
- `/api/emails/weeks/<week-id>/sent` claims, marks sent, or resets send state
- `/api/emails/weeks/<week-id>/activity` lists activity log records
- `/api/emails/weeks/<week-id>/requests` lists public requests for that week

Automation:

- `/api/emails/automation/ping` verifies Apps Script shared-key access without changing data
- `/api/emails/automation/settings` returns Apps Script delivery config
- `/api/emails/automation/weeks/<week-id>/scheduled-ingest` creates a missing draft week
- `/api/emails/automation/weeks/<week-id>/activity` records Apps Script audit events
- `/api/emails/weeks/<week-id>/sender-output` returns approved-only send payloads
- `/api/signage/automation/days/<day-id>/refresh` refreshes the daily signage snapshot
- `/api/signage/local/days/<day-id>/refresh` is available only in testing/local-dev

## Runtime Configuration

Required app configuration:

- `FIREBASE_PROJECT_ID`
- `EMAILS_SESSION_SECRET`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`

Required in production unless you deliberately derive them elsewhere:

- `GOOGLE_OAUTH_CALLBACK_URL`
- `PUBLIC_BASE_URL`

Firestore access:

- preferred in production: attach a Cloud Run service account with Firestore access
- supported fallback: `FIREBASE_SERVICE_ACCOUNT_JSON`
- local emulator: `FIRESTORE_EMULATOR_HOST`
- optional override: `FIRESTORE_COLLECTION` defaults to `emailWeeks`

Optional app configuration:

- `EMAILS_LOCAL_DEV=1` for local plain-HTTP development
- `GEMINI_API_KEY` to enable AI copy generation
- `GEMINI_MODEL` defaults to `gemini-3-flash-preview`
- `EMAILS_BOOTSTRAP_ALLOWED_EMAILS`
- `EMAILS_BOOTSTRAP_NOTIFICATION_EMAILS`
- `EMAILS_AUTOMATION_KEY` as a legacy/bootstrap fallback before the settings-backed key is configured

Required Apps Script properties:

- `API_BASE_URL`
- `AUTOMATION_API_KEY`

Apps Script pulls the rest of its delivery configuration from `/api/emails/automation/settings`:

- ops/admin notification recipients
- middle-school and upper-school `to`/`bcc` recipients
- sender display name
- reply-to email
- timezone

Manual sends also require the Apps Script web app `/exec` URL and the automation key in `/emails/settings`. When rotating the key there, update the Apps Script `AUTOMATION_API_KEY` Script Property to the same value.

## Local Development

Install dependencies:

```bash
python3 -m pip install -r requirements-dev.txt
```

Start from the sample env file:

```bash
cp .env.local.example .env.local
```

Run Flask directly:

```bash
PYTHONPATH=src python3 -m flask --app sl_emails.web:create_app run --port 5050
```

Run the Cloud Run container locally:

```bash
./scripts/run_cloudrun_local.sh
```

Notes:

- the Docker runner reads `.env.local` by default
- it sets `EMAILS_LOCAL_DEV=1`
- it mounts local ADC automatically when available
- it serves Gunicorn on `http://localhost:8080`

Utility commands:

```bash
PYTHONPATH=src python3 -m sl_emails.ingest.generate_games
PYTHONPATH=src python3 -m sl_emails.signage.generate_signage
```

## Testing

Run the Python suite with coverage:

```bash
PYTHONPATH=src pytest --cov=src/sl_emails --cov-report=term-missing -q
```

Run the Apps Script tests:

```bash
node --test google-apps-script/tests/*.js
```

CI and production deploys run both suites before any release.

## Repository Map

```text
sl-emails/
├── src/sl_emails/
│   ├── web/              # Flask runtime, routes, templates, static assets
│   ├── services/         # Firestore stores, ingest orchestration, outputs
│   ├── domain/           # Shared data normalization and record models
│   ├── ingest/           # Source scraping and HTML email rendering
│   └── signage/          # Signage HTML renderer
├── google-apps-script/   # Scheduled automation and troubleshooting helpers
├── firebase-hosting/     # Hosting-served static assets
├── deploy/cloudrun/      # Reference Cloud Run manifest
├── scripts/              # Local tooling
├── .github/workflows/    # CI and deploy automation
├── README.md
└── SETUP.md
```

## Operational Notes

- Firestore is the operational source of truth for signage snapshots, weekly drafts, admin settings, request queue records, and activity logs.
- Source refreshes fail closed. If athletics or arts fetches fail, the app returns `503` and preserves the existing week or day.
- `/signage` is cacheable through the next Denver midnight. During the first three hours after midnight, it can temporarily fall back to the prior day if the new snapshot is not available yet.
- Weekly scheduled ingest skips existing drafts by design.
- `digital-signage/index.html` is only for local/manual preview generation and is not part of the deployed runtime path.
- The legacy Firestore REST publish tooling remains in the repo for compatibility, but it is not the production scheduling path.
