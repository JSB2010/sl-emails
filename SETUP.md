# Sports Email Deployment & Runbook

This is the live runbook for the sports email system after the GitHub scheduler cutover.

## Production Architecture

- Cloud Run hosts `sl_emails.web:create_app`
- Firebase Hosting fronts the public hostname
- Firestore stores weekly drafts, approval state, and sent state
- Google Apps Script owns Sunday cron automation and all Gmail sends
- GitHub Actions handles deploys and digital signage only

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

## Required Apps Script Configuration

Set these Script Properties in the Apps Script project:

- `API_BASE_URL`
- `AUTOMATION_API_KEY`
- `ADMIN_NOTIFICATION_EMAILS`
- `MIDDLE_SCHOOL_TO`
- `MIDDLE_SCHOOL_BCC`
- `UPPER_SCHOOL_TO`
- `UPPER_SCHOOL_BCC`

Optional Script Properties:

- `EMAIL_FROM_NAME`
- `API_ACTOR`
- `REPLY_TO_EMAIL`
- `TIMEZONE`

`AUTOMATION_API_KEY` must exactly match the app's `EMAILS_AUTOMATION_KEY`.

## Key Endpoints

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
- `GET /api/emails/weeks/<week-id>/sender-output`
  - Approved-only payloads for Apps Script delivery

## Weekly Timeline

- Daily: `.github/workflows/update-signage.yml` refreshes signage
- Sunday 8:00 AM MT: Apps Script runs `runSundayDraftCycle`
- Sunday morning: admin receives review email linking to `/emails?week=<week-id>`
- Before Sunday 4:00 PM MT: staff review and approve the week
- Sunday 4:00 PM MT: Apps Script runs `sendSportsEmails`

## Operator Checklist

1. Deploy the app to Cloud Run and keep Firebase Hosting pointed at it.
2. Set the auth/runtime env vars, especially `EMAILS_AUTOMATION_KEY`, `EMAILS_SESSION_SECRET`, and the Google OAuth client credentials.
3. Configure the Google OAuth consent/client so the callback URL matches `/auth/google/callback`.
4. Add any additional admin emails in `/emails/settings` after the first sign-in bootstrap.
5. Update Apps Script Script Properties, especially `API_BASE_URL` and `AUTOMATION_API_KEY`.
6. Paste `google-apps-script/sports-email-sender.gs` and `google-apps-script/troubleshooting-functions.gs` into the Apps Script project.
7. Run `debugConfiguration()` and `debugScheduledIngestAccess()` in Apps Script.
8. Run `setupTriggers()` in Apps Script once production config is correct.
9. Run `runSundayDraftCycleManual()` and confirm:
- the backend returns a created or skipped result
- the ops/admin list receives the review email
- the review link opens `/emails?week=<week-id>` after Google sign-in
10. Approve a test week in `/emails`.
11. Run `testApprovedApiAccess()` and then `sendSportsEmailsManual()`.

## Troubleshooting

- If Sunday morning ingest fails:
  - check Cloud Run logs for `/api/emails/automation/weeks/<week-id>/scheduled-ingest`
  - confirm `EMAILS_AUTOMATION_KEY` matches the Apps Script `AUTOMATION_API_KEY` Script Property
  - run `debugScheduledIngestAccess()` in Apps Script
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

- Firestore is the source of truth for sports emails.
- Scheduled ingest never overwrites an existing week.
- Digital signage intentionally still uses GitHub Actions in this phase.
