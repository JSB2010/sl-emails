# Weekly Email Deployment & Operator Runbook

This document is the live deployment/runbook for the Firestore-backed weekly email workflow and the canonical `sl_emails` operational entrypoints.

## Selected Production Architecture

- **Cloud Run** hosts the Flask app exported by `sl_emails.web:create_app`.
- **Firebase Hosting** is the public front door and custom-domain layer in front of Cloud Run.
- **Cloudflare** remains DNS/registrar only.
- **Firestore** stores weekly drafts, approval state, and sent-state.
- **GitHub Actions** runs Sunday ingest and daily signage generation.
- **Google Apps Script** sends only approved payloads.

If any step below suggests Cloudflare Pages or another static host as the primary runtime, treat that as historical fallback guidance only. The active architecture is **Cloud Run + Firebase Hosting + Cloudflare DNS**.

## What the Agent Can Do vs. What the User Must Do

### Agent can do in the repo

- Commit deployment/runbook docs, workflow config, and repo-owned deployment artifacts.
- Name every required secret, env var, and config value.
- Run local doc-consistency checks and targeted smoke checks that do not require cloud credentials.

### User/operator must do manually

- Confirm the production GCP/Firebase project, billing, region, and org-owned credentials.
- Create/rotate service-account keys and store them in GitHub secrets and Cloud Run/Secret Manager.
- Deploy Cloud Run and Firebase Hosting with real cloud credentials.
- Add/update custom-domain records in Cloudflare DNS.
- Update Apps Script config values and enable production triggers.

## Repo-Owned Deployment Artifacts

- `Dockerfile`
  - Builds the production Cloud Run container for `sl_emails.web:create_app` and starts it with Gunicorn via `sl_emails.web.wsgi:app`.
- `.dockerignore`
  - Excludes git metadata, tests, local Firebase JSON files, and `deploy/` from the image build context.
- `deploy/cloudrun/service.template.yaml`
  - Cloud Run service template with placeholders for `PROJECT_ID`, `REGION`, `TAG`, and `serviceAccountName`.
- `.firebaserc`
  - Sets the default Firebase project to `student-leadership-media`.
- `firebase.json`
  - Rewrites every Hosting route (`"**"`) to Cloud Run service `sl-emails` in region `us-central1`.
- `firebase-hosting/404.html`
  - Minimal placeholder public directory content required by Firebase Hosting.

## System of Record

- **Firestore** stores weekly drafts, approval status, and sent-state.
- **`/emails`** is the weekly admin workflow used to review, edit, preview, and approve.
- **GitHub Actions** ingests source events into Firestore and refreshes signage output.
- **Google Apps Script** sends only payloads that the backend reports as approved.
- **`sports-emails/<week>/...html` folders are not the operational source of truth.** They remain optional preview/archive output only.

## Supported Operational Entrypoints

All supported launch commands are root-scoped module execution from the repo root.

### Runtime

```bash
PYTHONPATH=src python3 -m flask --app sl_emails.web:create_app run --port 5050
```

### Sunday ingest

```bash
PYTHONPATH=src python3 -m sl_emails.ingest.generate_games --firestore-draft --skip-html
```

### Manual HTML preview / export

```bash
PYTHONPATH=src python3 -m sl_emails.ingest.generate_games
```

### Daily signage generation

```bash
PYTHONPATH=src python3 -m sl_emails.signage.generate_signage
```

### Poster / carousel generation

```bash
PYTHONPATH=src python3 -m sl_emails.poster.carousel --next-week
```

## Weekly Timeline

- **Daily**: `.github/workflows/update-signage.yml` refreshes `digital-signage/index.html`.
- **Sunday 3:00 PM MT**: `.github/workflows/generate-sports-emails.yml` writes the next week's Firestore draft.
- **On push to `main`**: `.github/workflows/deploy-main.yml` builds the container, deploys Cloud Run + Firebase Hosting together, then smoke-checks `/_health`, `/`, and `/emails` on both the direct Cloud Run URL and the Hosting front door.
- **Before Sunday 4:00 PM MT**: operator reviews the draft at `/emails` and clicks **Approve Week**.
- **Sunday 4:00 PM MT**: Google Apps Script fetches approved output and sends both audience emails.

## Secrets & Platform Inputs

### Secret inventory

- **GitHub Actions secret:** `FIREBASE_SERVICE_ACCOUNT_JSON`
  - Full JSON key used by `.github/workflows/generate-sports-emails.yml` for Firestore draft publish auth and by `.github/workflows/deploy-main.yml` for Cloud Build, Cloud Run deploy, and Firebase Hosting deploy.
  - The service account behind this key must be able to run Cloud Build, deploy Cloud Run, act as the runtime service account, and deploy Firebase Hosting.
- **GitHub Actions variable:** `FIREBASE_SERVICE_ACCOUNT_EMAIL`
  - Email for the same service account used during GitHub Actions auth.
- **GitHub Actions variable:** `GCP_PROJECT_ID`
  - Optional override for `.github/workflows/deploy-main.yml`; defaults to `student-leadership-media`.
- **GitHub Actions variable:** `GCP_REGION`
  - Optional override for `.github/workflows/deploy-main.yml`; defaults to `us-central1`.
- **GitHub Actions variable:** `CLOUD_RUN_SERVICE`
  - Optional override for `.github/workflows/deploy-main.yml`; defaults to `sl-emails`.
- **GitHub Actions variable:** `CLOUD_RUN_RUNTIME_SERVICE_ACCOUNT`
  - Optional override for `.github/workflows/deploy-main.yml`; defaults to `sl-emails-runtime@student-leadership-media.iam.gserviceaccount.com`.
- **GitHub Actions variable:** `ARTIFACT_REGISTRY_REPOSITORY`
  - Optional override for `.github/workflows/deploy-main.yml`; defaults to `sl-emails`.
- **GitHub Actions variable:** `FIRESTORE_DATABASE_ID`
  - Keep set to `(default)` for the current runtime/backend implementation.
- **GitHub Actions variable:** `FIRESTORE_COLLECTION`
  - Set to `emailWeeks` unless you intentionally change the collection name everywhere; reused by both ingest and deploy workflows.
- **GitHub Actions variable:** `FIREBASE_HOSTING_URL`
  - Optional smoke-test override for `.github/workflows/deploy-main.yml`; defaults to `https://<project-id>.web.app`.
- **Cloud Run env var:** `FIREBASE_PROJECT_ID`
  - Firebase project ID used by the runtime.
- **Cloud Run secret/env var:** `FIREBASE_SERVICE_ACCOUNT_JSON`
  - Same credential material as GitHub Actions, stored as a platform-managed secret rather than a repo file.
- **Cloud Run env var:** `FIRESTORE_COLLECTION`
  - Usually `emailWeeks`.
- **Cloud Run env var:** `FIRESTORE_EMULATOR_HOST`
  - Local/dev only; do not set in production.
- **Apps Script config values:** `CONFIG.API_BASE_URL`, `CONFIG.ADMIN_EMAIL`, `CONFIG.EMAIL_RECIPIENTS`, `CONFIG.EMAIL_FROM_NAME`
  - Must be updated manually in the Apps Script project before live sends.

> Do **not** use a committed JSON credential file as production runtime input. If the repo-root Firebase service-account JSON still exists, treat it as a migration artifact and rotate/store the real credential in platform-managed secrets before go-live.

## Required Firebase / Firestore Configuration

### Firebase project

1. Use a Firebase project with **Cloud Firestore in Native mode**.
2. Keep the live email workflow in the **default Firestore database** (`(default)`).
3. Create a service account with permission to read/write the weekly draft collection.

### GitHub Actions secrets and vars

Configure these in the GitHub repository settings used by `.github/workflows/generate-sports-emails.yml` and `.github/workflows/deploy-main.yml`.

- **Secret:** `FIREBASE_SERVICE_ACCOUNT_JSON`
  - Full JSON key for the Firebase/Google service account.
  - Reused by the main deploy workflow, so the same service account also needs deploy permissions for Cloud Build, Cloud Run, `iam.serviceAccounts.actAs` on the runtime service account, and Firebase Hosting.
- **Variable:** `FIREBASE_SERVICE_ACCOUNT_EMAIL`
  - Email address of the same service account; currently required by the Sunday ingest workflow.
- **Variable:** `GCP_PROJECT_ID`
  - Optional override for the main deploy workflow; default is `student-leadership-media`.
- **Variable:** `GCP_REGION`
  - Optional override for the main deploy workflow; default is `us-central1`.
- **Variable:** `CLOUD_RUN_SERVICE`
  - Optional override for the main deploy workflow; default is `sl-emails`.
- **Variable:** `CLOUD_RUN_RUNTIME_SERVICE_ACCOUNT`
  - Optional override for the main deploy workflow; default is `sl-emails-runtime@student-leadership-media.iam.gserviceaccount.com`.
- **Variable:** `ARTIFACT_REGISTRY_REPOSITORY`
  - Optional override for the main deploy workflow; default is `sl-emails`.
- **Variable:** `FIRESTORE_DATABASE_ID`
  - Set to `(default)` for the current runtime/backend implementation.
- **Variable:** `FIRESTORE_COLLECTION`
  - Set to `emailWeeks` unless you intentionally want a different collection.
- **Variable:** `FIREBASE_HOSTING_URL`
  - Optional override for smoke checks after deploy; default target is `https://<project-id>.web.app`.

### Runtime environment variables

Configure these on the deployed Python runtime that serves the Flask app created by `sl_emails.web:create_app`. These are the runtime-owned values consumed by `RuntimeFirestoreConfig`:

- `FIREBASE_PROJECT_ID=<your-firebase-project-id>`
- `FIREBASE_SERVICE_ACCOUNT_JSON=<same JSON used in GitHub Actions, single-line or platform secret>`
- `FIRESTORE_COLLECTION=emailWeeks` *(optional if you use the default; required if GitHub Actions uses a custom collection name)*
- `FIRESTORE_EMULATOR_HOST=host:port` *(optional; local development/testing only)*

`instagram-poster/requirements.txt` owns the deployed runtime dependencies (`flask`, `gunicorn`, and `firebase-admin`), so install guidance and container builds should come from that manifest rather than an ad hoc extra pip package.

### Current config-only constraint

- The runtime currently reads from the **default Firestore database only**.
- Keep `FIRESTORE_DATABASE_ID=(default)` in GitHub Actions so ingest and `/emails` stay aligned.
- If you need a non-default Firestore database later, that is a follow-up deployment task, not part of the current cutover.

## Cloud Run Manual Setup

These steps require the user's cloud credentials. The agent can prepare repo-owned deployment artifacts, but the user must perform the live deploy.

1. Select the production GCP project and region for the live service.
2. Build and publish the container image from the repo root `Dockerfile`:

```bash
gcloud builds submit --tag us-central1-docker.pkg.dev/student-leadership-media/sl-emails/sl-emails:TAG
```

3. Open `deploy/cloudrun/service.template.yaml` and replace these placeholders before deploy:
   - `PROJECT_ID` → your real GCP project ID (currently expected: `student-leadership-media`)
   - `REGION` → your Cloud Run / Artifact Registry region (currently expected: `us-central1`)
   - `TAG` → the image tag you built
   - `serviceAccountName` → the runtime service account email that should access Firestore
4. Deploy the rendered Cloud Run service template:

```bash
gcloud run services replace deploy/cloudrun/service.template.yaml --region us-central1 --project student-leadership-media
```

5. Set runtime config on the Cloud Run service:
   - `FIREBASE_PROJECT_ID=<your-firebase-project-id>`
   - `FIRESTORE_COLLECTION=emailWeeks` (or your chosen non-default collection if changed everywhere)
   - `FIREBASE_SERVICE_ACCOUNT_JSON` via Secret Manager or equivalent Cloud Run secret wiring
   - Or prefer the attached Cloud Run service account / ADC path already noted in `deploy/cloudrun/service.template.yaml`
6. Do **not** set `FIRESTORE_EMULATOR_HOST` in production.
7. Confirm the deployed revision can read bundled repo assets needed by the app:
   - `digital-signage/index.html`
   - `src/sl_emails/web/templates/`
   - `src/sl_emails/web/static/`
8. Capture the default `run.app` URL and smoke-test it before involving Firebase Hosting:
   - `GET /_health`
   - `GET /`
   - `GET /emails`
   - Use exact `/_health` for public probes; Google-managed frontends may intercept exact `/healthz` before Flask.

## Firebase Hosting Manual Setup

These steps also require user-owned Firebase credentials.

1. Confirm `.firebaserc` points at the intended Firebase project (`student-leadership-media` by default).
2. Confirm `firebase.json` still matches the live Cloud Run target:
   - `hosting.public` = `firebase-hosting`
   - rewrite target `serviceId` = `sl-emails`
   - rewrite target `region` = `us-central1`
3. Deploy **Firebase Hosting** as the public front door in front of the Cloud Run service:

```bash
firebase deploy --only hosting --project student-leadership-media
```

4. Verify the generated Hosting URL works before changing DNS:
   - `/_health`
   - `/`
   - `/emails`
5. Start the Firebase Hosting custom-domain flow for the final school-facing hostname.
6. Keep Firebase Hosting — not Cloud Run directly — as the public host that Apps Script and users will hit after cutover.

## Cloudflare DNS Manual Steps

Cloudflare remains DNS only. The user must make these DNS changes manually.

1. In the Firebase Hosting custom-domain wizard, enter the production hostname.
2. Wait for Firebase to show the exact verification and routing records required for that hostname.
3. In Cloudflare DNS, remove or demote any conflicting old Pages/static records for the same host.
4. Create the exact TXT/A/AAAA/CNAME records that Firebase Hosting requests.
5. Do **not** point the production hostname directly at Cloud Run; Firebase Hosting is the supported public front door.
6. Wait until Firebase marks the domain connected and the managed certificate is active before calling cutover complete.

## Required Runtime / Hosting Configuration

After cutover, the primary school-facing hostname must reach Firebase Hosting first and then the Cloud Run-backed Flask runtime, rather than a static Pages-only build of `digital-signage/`.

### Runtime expectations

- Install both current dependency manifests:
  - `python3 -m pip install -r sports-emails/requirements.txt`
  - `python3 -m pip install -r instagram-poster/requirements.txt`
- Serve the Flask app exported by `sl_emails.web:create_app`.
- The production Cloud Run container now starts the app through Gunicorn (`sl_emails.web.wsgi:app`) from the repo `Dockerfile`.
- For basic live/local testing, the supported start command is:

```bash
PYTHONPATH=src python3 -m flask --app sl_emails.web:create_app run --port 5050
```

- The deployed app must have repository access to `digital-signage/index.html`, because `/` reads that file directly.
- The deployed app must also have repository access to `src/sl_emails/web/templates/` and `src/sl_emails/web/static/`, because the runtime serves `/emails` and shared preview/static assets from those canonical package paths.

### Routes that must exist on the live host

- `/` → signage HTML
- `/emails` → weekly admin UI
- `/api/emails/weeks/<week-id>` and related subroutes → weekly draft APIs
- `/_health` → public health check

### Cloudflare-specific cutover note

- The previous **Cloudflare Pages build output = `digital-signage`** setup is now a **legacy signage-only fallback**.
- If you keep that old static-only deployment as the primary host, `/emails` will not exist.
- For live cutover, point the school-facing route/domain at **Firebase Hosting**, which then fronts the `sl_emails.web:create_app` runtime on Cloud Run.

## Required Google Apps Script Configuration

Update `google-apps-script/sports-email-sender.gs` before testing or enabling triggers:

- `CONFIG.API_BASE_URL`
  - Set to the Firebase Hosting URL or final custom domain that serves `/emails`, for example `https://studentleader.kentdenver.org`
  - Do **not** include a trailing slash.
  - Use the Cloud Run `run.app` URL only for pre-cutover testing; once Hosting is live, Apps Script should target Hosting/custom-domain URLs.
- `CONFIG.ADMIN_EMAIL`
  - Address that should receive send-failure notifications.
- `CONFIG.EMAIL_RECIPIENTS.MIDDLE_SCHOOL` / `UPPER_SCHOOL`
  - Confirm `to` and `bcc` values for the real recipient lists.
- `CONFIG.EMAIL_FROM_NAME`
  - Leave as desired sender display name.

### Apps Script test sequence

1. Create or update the Apps Script project with `google-apps-script/sports-email-sender.gs`.
2. Optionally add `google-apps-script/troubleshooting-functions.gs` for debug helpers such as `sendTestEmail()`.
3. Run `testApprovedApiAccess()` from `sports-email-sender.gs`.
4. Confirm the logs show the expected week ID, approval state, and both audience payloads.
5. If you installed `google-apps-script/troubleshooting-functions.gs`, run `sendTestEmail()` from that file.
6. Confirm subject/body render correctly in a real inbox.
7. Run `setupTriggers()` from `sports-email-sender.gs` only after the final Hosting/custom domain is stable and verified.

## Cutover Order

1. **Prepare secrets first**
   - GitHub Actions secret/vars configured.
   - Cloud Run runtime env vars/secrets configured.
   - Apps Script config values identified but triggers still disabled.
2. **Deploy and verify Cloud Run directly**
   - Build from `Dockerfile` and deploy the rendered `deploy/cloudrun/service.template.yaml`.
   - Smoke-test the Cloud Run service URL for `/_health`, `/`, and `/emails`.
   - Stop here if any route is broken.
3. **Deploy and verify Firebase Hosting**
   - Deploy `firebase.json` / `.firebaserc` with `firebase deploy --only hosting --project student-leadership-media`.
   - Confirm the Hosting-proxied/default URL works before touching Cloudflare.
4. **Update Apps Script for the new base URL**
   - First test against the Hosting URL.
   - Run `testApprovedApiAccess()` first; run `sendTestEmail()` only if `google-apps-script/troubleshooting-functions.gs` is installed.
5. **Perform Cloudflare DNS cutover**
   - Apply the Firebase-requested DNS records.
   - Wait for Firebase domain verification and certificate readiness.
6. **Switch Apps Script to the final custom domain**
   - Re-run `testApprovedApiAccess()` after DNS and certificate issuance complete.
7. **Enable production sending**
   - Send to test recipients first.
   - Only then enable or restore time-based triggers.

## Weekly Operator Runbook

### 1. Confirm Sunday ingest completed

In GitHub Actions, open **Generate Sports Emails** and verify:

- the run succeeded
- the summary lists the expected draft week key
- the draft review status is `draft` or `pending`

### 2. Review the week in `/emails`

1. Open the deployed Hosting/custom-domain `/emails` page.
2. Confirm the Monday date is correct.
3. Click **Load Draft**.
4. If no draft exists yet, click **Create from Source Events**.
5. Review imported rows, hide anything that should not send, and add any custom school events.
6. Click **Refresh Preview** and check both audiences.
7. Click **Approve Week** only when both previews are correct.

### 3. Send path behavior

- The sender fetches only `/api/emails/weeks/<week-id>/sender-output` from approved weeks.
- The sender claims the week as `sending` before Gmail delivery.
- A successful run finalizes the week as `sent`.

### 4. If the sender reports `sending`

- Treat this as a possible partial-send state.
- Check Apps Script execution logs before rerunning.
- Confirm whether either audience email already delivered.
- Clear or repair sent-state only after you understand whether a partial delivery happened.

## Focused Regression Checklist

Use this checklist after deployment changes or secret rotation:

1. `GET /_health` returns `{"ok": true}` on the direct Cloud Run URL before front-door cutover.
2. `GET /_health` also returns `{"ok": true}` through Firebase Hosting/custom domain after cutover.
3. `GET /` still shows the signage HTML.
4. `GET /emails` loads the weekly review UI.
5. Load an existing draft week from Firestore.
6. Refresh preview and verify both middle-school and upper-school outputs.
7. Approve the week.
8. Run `testApprovedApiAccess()` in Apps Script.
9. Confirm the sender refuses unapproved weeks and does not resend already-sent weeks.

## Rollback / Legacy Fallback

- If the direct Cloud Run URL fails, stop and fix Cloud Run before Firebase Hosting or DNS cutover.
- If Cloud Run works but Firebase Hosting does not, leave Cloudflare unchanged and keep testing on the Cloud Run/Hosting-generated URLs only.
- If custom-domain cutover fails, revert Cloudflare records to the previous known-good state or leave the prior production host in place.
- If Apps Script tests fail, keep triggers disabled and do not send production mail until `testApprovedApiAccess()` passes, plus `sendTestEmail()` if you installed the optional troubleshooting helpers.
- Root signage can still fall back to the committed `digital-signage/index.html` artifact if the runtime host has issues.
- The old static signage deployment should be treated as a rollback-only/manual path, not the default operating model.
