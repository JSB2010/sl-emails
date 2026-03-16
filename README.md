# Kent Denver Student Leadership Emails

Kent Denver's sports email workflow now runs through the deployed app plus Google Apps Script:

1. Sunday 8:00 AM MT: Apps Script calls the app's protected scheduled-ingest endpoint.
2. The app fetches athletics + arts sources, creates the next week's Firestore draft if missing, and never overwrites an existing week automatically.
3. Apps Script emails the ops/admin list a review link to `/emails?week=<YYYY-MM-DD>`.
4. Staff sign in with Google, review, edit, preview, and approve in `/emails`.
5. Sunday 4:00 PM MT: Apps Script fetches approved sender-output and sends both audience emails.

Digital signage still stays on GitHub Actions for now. GitHub remains deployment and signage automation only for sports email operations.

## Production Roles

- Cloud Run: Flask runtime serving `/`, `/emails`, and `/api/emails/...`
- Firebase Hosting: public front door in front of Cloud Run
- Cloudflare: DNS/registrar only
- Firestore: weekly drafts, approval state, and sent state
- Google Apps Script: Sunday cron triggers and Gmail delivery
- GitHub Actions: deploy pipeline and daily signage refresh only

## Key Routes

- `/` — signage page from `digital-signage/index.html`
- `/login` — Google sign-in entrypoint for sports email admins
- `/emails` — weekly admin review UI (Google sign-in + allowlist required)
- `/emails?week=YYYY-MM-DD` — deep link to a specific Monday week
- `/emails/settings` — allowlist and ops-notification settings
- `/api/emails/weeks/<week-id>` — weekly draft CRUD
- `/api/emails/weeks/<week-id>/source-refresh` — manual source refresh that preserves custom events
- `/api/emails/automation/weeks/<week-id>/scheduled-ingest` — protected Sunday morning ingest endpoint
- `/api/emails/automation/weeks/<week-id>/activity` — protected automation activity/audit endpoint
- `/api/emails/weeks/<week-id>/sender-output` — approved output for Apps Script sends
- `/_health` — health check

## Runtime Config

The deployed app expects:

- `FIREBASE_PROJECT_ID`
- `FIREBASE_SERVICE_ACCOUNT_JSON`
- `FIRESTORE_COLLECTION` (optional; defaults to `emailWeeks`)
- `FIRESTORE_EMULATOR_HOST` (local only)
- `EMAILS_AUTOMATION_KEY` (required for scheduled-ingest calls)
- `EMAILS_SESSION_SECRET` (required for stable admin sessions)
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_CALLBACK_URL` (recommended in production)
- `EMAILS_BOOTSTRAP_ALLOWED_EMAILS` (optional; defaults to `appdev@kentdenver.org,studentleader@kentdenver.org`)
- `EMAILS_BOOTSTRAP_NOTIFICATION_EMAILS` (optional; defaults to the same two emails)

Apps Script expects:

- Script Properties, not hardcoded constants
- Required:
  - `API_BASE_URL`
  - `AUTOMATION_API_KEY`
  - `ADMIN_NOTIFICATION_EMAILS`
  - `MIDDLE_SCHOOL_TO`
  - `MIDDLE_SCHOOL_BCC`
  - `UPPER_SCHOOL_TO`
  - `UPPER_SCHOOL_BCC`
- Optional:
  - `EMAIL_FROM_NAME`
  - `API_ACTOR`
  - `REPLY_TO_EMAIL`
  - `TIMEZONE`

## Supported Commands

Install dependencies from the repo root:

```bash
python3 -m pip install -r sports-emails/requirements.txt
python3 -m pip install -r instagram-poster/requirements.txt
```

Run the web app locally:

```bash
PYTHONPATH=src python3 -m flask --app sl_emails.web:create_app run --port 5050
```

Generate local/manual HTML previews:

```bash
PYTHONPATH=src python3 -m sl_emails.ingest.generate_games
```

Refresh signage locally:

```bash
PYTHONPATH=src python3 -m sl_emails.signage.generate_signage
```

Generate poster/carousel output:

```bash
PYTHONPATH=src python3 -m sl_emails.poster.carousel --next-week
```

## Repository Structure

```text
sl-emails/
├── src/sl_emails/                 # Runtime, services, ingest, signage, poster tools
├── src/sl_emails/web/templates/   # /emails admin UI
├── src/sl_emails/web/static/      # /emails static assets
├── google-apps-script/            # Sunday draft/send automation + troubleshooting
├── digital-signage/index.html     # Signage artifact served at /
├── .github/workflows/             # Deploy + signage automation
├── README.md
└── SETUP.md
```

## Notes

- Firestore is the operational source of truth for sports email weeks, admin allowlists, and app-side audit records.
- Historical `sports-emails/<week>/...html` output is optional preview/archive output only.
- The legacy Firestore REST publish path remains in the repo for manual tooling compatibility, but it is no longer the production scheduler path.
