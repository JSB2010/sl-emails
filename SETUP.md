# Deployment & Operations Runbook

This runbook reflects the current production shape:

- Firebase Hosting is the public entrypoint
- Cloud Run hosts the Flask app
- Google Apps Script owns cron and Gmail delivery

## Production Architecture

Request flow:

1. Firebase Hosting receives public traffic.
2. Static icon assets under `/static/icons/**` are served and long-cached by Hosting.
3. All other app traffic is rewritten to the Cloud Run service `sl-emails`.
4. Cloud Run serves the Flask runtime from `sl_emails.web.wsgi:app`.
5. Firestore stores:
   - signage snapshots
   - weekly drafts
   - admin settings
   - public event requests
   - activity log records

Automation flow:

1. Apps Script refreshes signage every day at midnight MT.
2. Apps Script creates or confirms the weekly draft on Sunday at 8:00 AM MT.
3. Staff review and approve the draft in `/emails`.
4. Apps Script attempts scheduled sends every day at 4:00 PM MT.

## GitHub Deploy Inputs

The production workflow is `.github/workflows/deploy-main.yml`.

Required GitHub secrets:

- `FIREBASE_SERVICE_ACCOUNT_JSON`
- `EMAILS_SESSION_SECRET`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`

Optional GitHub secret:

- `EMAILS_AUTOMATION_KEY` only if you need the legacy/bootstrap fallback before `/emails/settings` is configured

Optional GitHub variables:

- `GCP_PROJECT_ID`
- `GCP_REGION`
- `CLOUD_RUN_SERVICE`
- `CLOUD_RUN_RUNTIME_SERVICE_ACCOUNT`
- `ARTIFACT_REGISTRY_REPOSITORY`
- `FIRESTORE_COLLECTION`
- `FIREBASE_HOSTING_URL`
- `GOOGLE_OAUTH_CALLBACK_URL`
- `PUBLIC_BASE_URL`
- `GEMINI_MODEL`
- `GEMINI_API_KEY_SECRET_NAME`
- `EMAILS_BOOTSTRAP_ALLOWED_EMAILS`
- `EMAILS_BOOTSTRAP_NOTIFICATION_EMAILS`

## Runtime Configuration

Required on Cloud Run:

- `FIREBASE_PROJECT_ID`
- `EMAILS_SESSION_SECRET`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`

Recommended in production:

- `GOOGLE_OAUTH_CALLBACK_URL=https://<public-host>/auth/google/callback`
- `PUBLIC_BASE_URL=https://<public-host>`
- `GEMINI_MODEL=gemini-3-flash-preview`

Optional depending on Firestore auth strategy:

- attached Cloud Run service account with Firestore access
- or `FIREBASE_SERVICE_ACCOUNT_JSON`

Optional bootstrap values:

- `EMAILS_BOOTSTRAP_ALLOWED_EMAILS`
- `EMAILS_BOOTSTRAP_NOTIFICATION_EMAILS`

Local-only:

- `FIRESTORE_EMULATOR_HOST`
- `EMAILS_LOCAL_DEV=1`
- `EMAILS_AUTOMATION_KEY` as a local or legacy fallback before `/emails/settings` is configured

## Required Apps Script Configuration

Set these Script Properties:

- `API_BASE_URL`
- `AUTOMATION_API_KEY`

`AUTOMATION_API_KEY` must match the automation key stored in `/emails/settings`. `EMAILS_AUTOMATION_KEY` is only a legacy/bootstrap fallback for Cloud Run.

The app now owns these automation settings in `/emails/settings`:

- automation key
- Apps Script web app URL for manual sends
- admin notification recipients
- middle-school and upper-school delivery recipients
- sender display name
- reply-to email
- timezone

## First Production Bootstrap

1. Deploy Cloud Run and Firebase Hosting from GitHub Actions or manually with equivalent config.
2. Confirm Firebase Hosting rewrites to the `sl-emails` Cloud Run service.
3. Configure Google OAuth so the callback URL matches `/auth/google/callback` on the public host.
4. Sign in once through `/login`.
5. In `/emails/settings`, set:
   - allowlisted admin emails
   - ops/admin notification emails
   - middle-school and upper-school recipients
   - sender display name, reply-to email, and timezone
   - automation key
6. Copy `google-apps-script/sports-email-sender.gs` and `google-apps-script/troubleshooting-functions.gs` into the Apps Script project.
7. Deploy the Apps Script project as a web app, set it to execute as the script owner, and copy the `/exec` URL into `/emails/settings`.
8. Set Apps Script Script Properties to `API_BASE_URL` and `AUTOMATION_API_KEY`. The property value must match `/emails/settings`.
9. Run `debugConfiguration()` in Apps Script.
10. Run `debugBackendConnection()` in Apps Script and use `Test Connection` in `/emails/settings`.
11. Run `debugScheduledIngestAccess()` and `refreshDailySignageManual()`.
12. Confirm `/signage` renders the current day and `/emails?week=<week-id>` loads after sign-in.
13. Run `setupTriggers()` once production configuration is correct.

## Weekly Operating Timeline

- Daily 12:00 AM MT: `refreshDailySignage`
- Sunday 8:00 AM MT: `runSundayDraftCycle`
- Sunday morning: admins receive the review email
- Sunday 4:00 PM MT: default delivery window
- Monday through Thursday 4:00 PM MT: postponed delivery window

Weeks marked `skip` are intentionally suppressed. Existing drafts are never overwritten by scheduled ingest.

## Local Cloud Run-Style Run

For container parity with production:

```bash
./scripts/run_cloudrun_local.sh
```

Notes:

- the script builds `Dockerfile` and runs the Gunicorn entrypoint used by Cloud Run
- it reads `.env.local` by default
- start from `.env.local.example`
- local ADC is mounted automatically when available
- `EMAILS_LOCAL_DEV=1` switches cookies and callback generation to local HTTP
- add `GEMINI_API_KEY` only if you need AI copy generation locally

## Verification Checklist

After any deploy, verify:

1. `/_health` returns `200`.
2. `/signage` renders HTML and not an error body.
3. `/login` loads and Google sign-in completes for an allowlisted account.
4. `/api/emails/automation/settings` succeeds with the automation key.
5. `debugBackendConnection()` succeeds in Apps Script.
6. `Test Connection` succeeds in `/emails/settings`.
7. `refreshDailySignageManual()` succeeds in Apps Script.
8. `runSundayDraftCycleManual()` creates or skips the target week without error.
9. A test approval in `/emails` exposes approved sender-output.
10. `sendSportsEmailsManualForWeek("<week-id>")` completes and records send state in Apps Script.
11. The `Send Now` button on `/emails?week=<week-id>` completes for an approved, unsent week.

## Troubleshooting

If Sunday draft ingest fails:

- inspect Cloud Run logs for `/api/emails/automation/weeks/<week-id>/scheduled-ingest`
- confirm `/emails/settings` automation key matches Apps Script `AUTOMATION_API_KEY`
- run `debugScheduledIngestAccess()`

If signage is blank or stale:

- inspect Cloud Run logs for `/api/signage/automation/days/<day-id>/refresh`
- run `refreshDailySignageManual()`
- verify the correct Firestore day snapshot exists
- remember that `/signage` can fall back to the previous day only during the first three Denver-local hours after midnight

If admin sign-in fails:

- confirm `EMAILS_SESSION_SECRET`, `GOOGLE_OAUTH_CLIENT_ID`, and `GOOGLE_OAUTH_CLIENT_SECRET`
- confirm the callback URL matches the public host exactly
- confirm the user is allowlisted in `/emails/settings`

If Apps Script cannot send:

- run `debugBackendConnection()`
- run `debugApprovedApiAccess()`
- inspect approval and send-state in `/emails`
- confirm the Apps Script web app URL is set in `/emails/settings` if the UI `Send Now` button is failing
- use `Mark Unsent` in the UI only after confirming whether any delivery already happened

If source refresh fails:

- the app intentionally fails closed and preserves the last good week/day
- inspect `source_health` in the API response or activity log to identify the failing source

## Local Test Commands

```bash
PYTHONPATH=src pytest --cov=src/sl_emails --cov-report=term-missing -q
node --test google-apps-script/tests/*.js
```
