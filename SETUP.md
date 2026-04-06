# Sports Email Deployment & Runbook

This is the live runbook for the sports email system after the GitHub scheduler cutover.

## Production Architecture

- Cloud Run hosts `sl_emails.web:create_app`
- Firebase Hosting fronts the public hostname
- Firestore stores public signage snapshots plus weekly drafts, approval state, and sent state
- Google Apps Script owns daily signage refresh, Sunday cron automation, and all Gmail sends
- GitHub Actions handles deploys only

## Required Runtime Configuration

Configure these on the deployed app:

- `FIREBASE_PROJECT_ID`
- `FIREBASE_SERVICE_ACCOUNT_JSON`
- `FIRESTORE_COLLECTION=emailWeeks` (or your chosen collection)
- `EMAILS_AUTOMATION_KEY=<shared secret for Apps Script>`
- `EMAILS_SESSION_SECRET=<stable Flask session secret>`
- `GOOGLE_OAUTH_CLIENT_ID=<Google OAuth web client ID>`
- `GOOGLE_OAUTH_CLIENT_SECRET=<Google OAuth web client secret>`
- `GOOGLE_OAUTH_CALLBACK_URL=https://<your-host>/auth/google/callback`
- `EMAILS_BOOTSTRAP_ALLOWED_EMAILS=appdev@kentdenver.org,studentleader@kentdenver.org`
- `EMAILS_BOOTSTRAP_NOTIFICATION_EMAILS=appdev@kentdenver.org,studentleader@kentdenver.org`

Local-only:

- `FIRESTORE_EMULATOR_HOST`
- `EMAILS_LOCAL_DEV=1` when you run the Cloud Run container over plain local HTTP

## Required Apps Script Configuration

Set these Script Properties in the Apps Script project:

- `API_BASE_URL`
- `AUTOMATION_API_KEY`

`AUTOMATION_API_KEY` must exactly match the app's `EMAILS_AUTOMATION_KEY`.
All delivery recipients, ops/admin notification emails, sender display name, reply-to email, and timezone now live in `/emails/settings` inside the Cloud Run app.

## Key Endpoints

- `POST /api/signage/automation/days/<day-id>/refresh`
  - Protected by `X-Automation-Key`
  - Refreshes the Firestore-backed signage snapshot for the target Denver-local date
- `POST /api/emails/automation/weeks/<week-id>/scheduled-ingest`
  - Protected by `X-Automation-Key`
  - Creates a missing week from source events
  - Skips without mutation if the week already exists
- `POST /api/emails/weeks/<week-id>/source-refresh`
  - Manual admin refresh
  - Replaces source events, preserves custom events/heading/notes, resets review/send state
- `POST /api/emails/automation/weeks/<week-id>/activity`
  - Protected by `X-Automation-Key`
  - Records review-notification/send failure audit entries from Apps Script
- `GET /api/emails/automation/settings`
  - Protected by `X-Automation-Key`
  - Returns the Apps Script sender + recipient settings from Cloud Run
- `GET /api/emails/weeks/<week-id>/sender-output`
  - Approved-only payloads for Apps Script delivery

## Weekly Timeline

- Daily 12:00 AM MT: Apps Script runs `refreshDailySignage`
- Sunday 8:00 AM MT: Apps Script runs `runSundayDraftCycle`
- Sunday morning: admin receives review email linking to `/emails?week=<week-id>`
- Before Sunday 4:00 PM MT: staff review and approve the week
- Sunday 4:00 PM MT: Apps Script runs `sendSportsEmails`

## Operator Checklist

1. Deploy the app to Cloud Run and keep Firebase Hosting pointed at it.
2. Set the auth/runtime env vars, especially `EMAILS_AUTOMATION_KEY`, `EMAILS_SESSION_SECRET`, the Google OAuth client credentials, `GEMINI_API_KEY`, and `PUBLIC_BASE_URL`.
3. Configure the Google OAuth consent/client so the callback URL matches `/auth/google/callback`.
4. Add any additional admin emails and all automation delivery recipients in `/emails/settings` after the first sign-in bootstrap.
5. Update Apps Script Script Properties so only `API_BASE_URL` and `AUTOMATION_API_KEY` remain.
6. Paste `google-apps-script/sports-email-sender.gs` and `google-apps-script/troubleshooting-functions.gs` into the Apps Script project.
7. Run `debugConfiguration()` and `debugScheduledIngestAccess()` in Apps Script.
8. Run `refreshDailySignageManual()` and confirm `/signage` renders the current day snapshot.
9. Run `setupTriggers()` in Apps Script once production config is correct.
10. Run `runSundayDraftCycleManual()` and confirm:
- the backend returns a created or skipped result
- the ops/admin list receives the review email
- the review link opens `/emails?week=<week-id>` after Google sign-in
11. Approve a test week in `/emails`.
12. Run `testApprovedApiAccess()` and then `sendSportsEmailsManual()`.

## Local Cloud Run-Style Run

For local parity with the deployed container, use:

```bash
./scripts/run_cloudrun_local.sh
```

Notes:

- This builds the repo `Dockerfile` and runs the same Gunicorn entrypoint that Cloud Run uses.
- The script reads `.env.local` by default. Start from `.env.local.example`.
- Add `GEMINI_API_KEY` for AI copy generation. `GEMINI_MODEL` defaults to `gemini-3-flash-preview`.
- Set `PUBLIC_BASE_URL` in deployed environments so email HTML uses absolute icon URLs.
- For live Firestore without embedding a service-account JSON string, the script mounts local ADC from `~/.config/gcloud/application_default_credentials.json` when present.
- `EMAILS_LOCAL_DEV=1` switches cookies and generated callback URLs to local HTTP so Google sign-in can work on `localhost`.
- Local contributor installs should use `python3 -m pip install -r requirements-dev.txt` so pytest is available.

## Troubleshooting

- If Sunday morning ingest fails:
  - check Cloud Run logs for `/api/emails/automation/weeks/<week-id>/scheduled-ingest`
  - confirm `EMAILS_AUTOMATION_KEY` matches the Apps Script `AUTOMATION_API_KEY` Script Property
  - run `debugScheduledIngestAccess()` in Apps Script
- If signage is blank or missing:
  - check Cloud Run logs for `/api/signage/automation/days/<day-id>/refresh`
  - run `refreshDailySignageManual()` in Apps Script
  - confirm `/signage` returns HTML for the current Denver-local date
- If admins cannot sign in:
  - confirm the deployed app has `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, and `EMAILS_SESSION_SECRET`
  - confirm the OAuth callback URL matches `https://<host>/auth/google/callback`
  - confirm the Google account is on the allowlist in `/emails/settings`
- If the review UI needs a manual rebuild:
  - open `/emails?week=<week-id>`
  - click `Refresh Events`
- If send fails:
  - run `debugApprovedApiAccess()`
  - inspect the week's approval/sent state in `/emails`
  - if needed, use `Mark Unsent` in the UI before retrying

## Notes

- Firestore is the source of truth for signage and sports emails.
- Weekly ingest and signage refresh now fail closed. If any source fetch fails, the app records the failure and preserves the last known good week/day data.
- Scheduled ingest never overwrites an existing week.
