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

Local-only:

- `FIRESTORE_EMULATOR_HOST`

## Required Apps Script Configuration

Update `google-apps-script/sports-email-sender.gs` with:

- `CONFIG.API_BASE_URL`
- `CONFIG.AUTOMATION_API_KEY`
- `CONFIG.ADMIN_EMAIL`
- `CONFIG.EMAIL_RECIPIENTS`
- `CONFIG.EMAIL_FROM_NAME`

`CONFIG.AUTOMATION_API_KEY` must exactly match the app's `EMAILS_AUTOMATION_KEY`.

## Key Endpoints

- `POST /api/emails/automation/weeks/<week-id>/scheduled-ingest`
  - Protected by `X-Automation-Key`
  - Creates a missing week from source events
  - Skips without mutation if the week already exists
- `POST /api/emails/weeks/<week-id>/source-refresh`
  - Manual admin refresh
  - Replaces source events, preserves custom events/heading/notes, resets review/send state
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
2. Set `EMAILS_AUTOMATION_KEY` in the runtime environment.
3. Update Apps Script config values, especially `API_BASE_URL` and `AUTOMATION_API_KEY`.
4. Run `setupTriggers()` in Apps Script once production config is correct.
5. Run `runSundayDraftCycleManual()` and confirm:
   - the backend returns a created or skipped result
   - the admin receives the review email
   - the review link opens `/emails?week=<week-id>`
6. Approve a test week in `/emails`.
7. Run `testApprovedApiAccess()` and then `sendSportsEmailsManual()`.

## Troubleshooting

- If Sunday morning ingest fails:
  - check Cloud Run logs for `/api/emails/automation/weeks/<week-id>/scheduled-ingest`
  - confirm `EMAILS_AUTOMATION_KEY` matches `CONFIG.AUTOMATION_API_KEY`
  - run `debugScheduledIngestAccess()` in Apps Script
- If the review UI needs a manual rebuild:
  - open `/emails?week=<week-id>`
  - click `Refresh Source Events`
- If send fails:
  - run `debugApprovedApiAccess()`
  - inspect the week's approval/sent state in `/emails`
  - if needed, use `Mark Unsent` in the UI before retrying

## Notes

- Firestore is the source of truth for sports emails.
- Scheduled ingest never overwrites an existing week.
- Digital signage intentionally still uses GitHub Actions in this phase.
