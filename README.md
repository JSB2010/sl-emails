# Kent Denver Student Leadership Emails

Kent Denver's weekly email workflow runs from the canonical `src/sl_emails` package: Sunday ingest writes Firestore drafts, staff review and approve at `/emails`, Google Apps Script sends only approved payloads, and the same runtime serves the root signage page from `digital-signage/index.html`.

Production deployment is explicitly **Cloud Run for Python compute**, **Firebase Hosting as the public front door**, and **Cloudflare as DNS/registrar only**.

## Live Workflow

1. **Sunday ingest**: GitHub Actions scrapes athletics + arts sources and writes the next week's draft to Firestore.
2. **Admin review**: Staff open `/emails`, edit events, preview both audiences, and approve the week.
3. **Approved send**: Google Apps Script fetches `/api/emails/.../sender-output` and sends only approved payloads.
4. **Daily signage**: The deployed runtime serves `/` from the committed `digital-signage/index.html` artifact.

> **Operational source of truth:** Firestore weekly drafts plus approval/sent-state metadata. Historical HTML week folders under `sports-emails/` are optional preview/archive output, not production runtime state.

## Production Platform Roles

- **Cloud Run** — runs the Flask app exported by `sl_emails.web:create_app` and must serve `/`, `/emails`, `/api/emails/...`, and `/healthz`.
- **Firebase Hosting** — public web front door in front of Cloud Run, including the final school-facing hostname.
- **Cloudflare** — DNS/registrar layer only; not the compute runtime for this deployment.
- **Firebase Firestore** — weekly draft, approval, and sent-state system of record.
- **GitHub Actions** — Sunday ingest and daily signage refresh automation.
- **Google Apps Script** — approved-send Gmail integration only after operator approval.

## Deployment Artifacts

- `Dockerfile` — builds the Cloud Run image for the existing Flask runtime.
- `.dockerignore` — keeps git metadata, tests, local Firebase JSON files, and `deploy/` out of the image build context.
- `deploy/cloudrun/service.template.yaml` — Cloud Run service template with placeholders for `PROJECT_ID`, `REGION`, `TAG`, and the runtime service account.
- `.firebaserc` — sets the default Firebase project to `student-leadership-media`.
- `firebase.json` — configures Firebase Hosting to rewrite all routes to Cloud Run service `sl-emails` in `us-central1`.
- `firebase-hosting/404.html` — placeholder Hosting public directory content required by Firebase Hosting.

## Supported Commands

Install the current dependency manifests from the repo root:

```bash
python3 -m pip install -r sports-emails/requirements.txt
python3 -m pip install -r instagram-poster/requirements.txt
```

### Runtime app

```bash
PYTHONPATH=src python3 -m flask --app sl_emails.web:create_app run --port 5050
```

### Weekly ingest

```bash
PYTHONPATH=src python3 -m sl_emails.ingest.generate_games --firestore-draft --skip-html
PYTHONPATH=src python3 -m sl_emails.ingest.generate_games
```

- The first command matches the production-style Firestore draft publish.
- The second command is the supported local/manual HTML preview path.

### Digital signage generation

```bash
PYTHONPATH=src python3 -m sl_emails.signage.generate_signage
```

This updates the live signage artifact at `digital-signage/index.html`.

### Poster / carousel generation

```bash
PYTHONPATH=src python3 -m sl_emails.poster.carousel --next-week
```

Example custom range:

```bash
PYTHONPATH=src python3 -m sl_emails.poster.carousel \
  --start-date 2026-03-09 \
  --end-date 2026-03-15 \
  --custom-events custom-events.json \
  --heading "This Week at Kent Denver" \
  --output-html instagram-poster/carousel.html
```

## Repository Structure

```text
sl-emails/
├── Dockerfile                     # Cloud Run image build for the Flask runtime
├── .dockerignore                  # Excludes local secrets/tests from the image build context
├── deploy/cloudrun/service.template.yaml
│                                  # Cloud Run service template with runtime/env placeholders
├── .firebaserc                    # Default Firebase project mapping (`student-leadership-media`)
├── firebase.json                  # Firebase Hosting rewrite to Cloud Run service `sl-emails`
├── firebase-hosting/404.html      # Placeholder public asset required by Firebase Hosting
├── src/sl_emails/                  # Canonical runtime, ingest, signage, poster, and shared services
├── src/sl_emails/web/templates/    # Canonical Flask templates for the /emails admin workflow
├── src/sl_emails/web/static/       # Canonical Flask static assets and shared runtime logo
├── google-apps-script/             # Approved-send Gmail integration and troubleshooting helpers
├── digital-signage/index.html      # Generated signage artifact served at /
├── instagram-poster/               # Poster export artifact location + runtime requirements manifest
├── sports-emails/                  # Optional generated HTML previews + shared requirements manifest
├── .github/workflows/              # Sunday ingest and daily signage automation
├── README.md                       # Architecture and supported commands
└── SETUP.md                        # Deployment/runbook and operator checklist
```

## Key Routes

- `/` — signage page sourced from `digital-signage/index.html`
- `/emails` — weekly admin workflow for review, preview, approval, and custom events
- `/api/emails/weeks/<week-id>` — Firestore-backed weekly draft APIs
- `/healthz` — runtime health check

## Config & Dependency Ownership

- Shared repo paths and Firestore env names live in `src/sl_emails/config.py`.
- Production secrets belong in GitHub secrets/vars, Cloud Run secrets/env vars, and Apps Script config values — **not** in committed repo files.
- The repo-root Firebase service-account JSON should be treated as a migration artifact, not a production credential source.
- Runtime Firestore config ownership:
  - `FIREBASE_PROJECT_ID`
  - `FIREBASE_SERVICE_ACCOUNT_JSON`
  - `FIRESTORE_COLLECTION`
  - `FIRESTORE_EMULATOR_HOST` *(local/dev only)*
- GitHub Actions ingest ownership:
  - `FIRESTORE_ACCESS_TOKEN`
  - `FIRESTORE_PROJECT_ID`
  - `FIRESTORE_DATABASE_ID`
  - `FIRESTORE_COLLECTION`
- Dependency ownership remains split:
  - `sports-emails/requirements.txt` owns the shared scrape/render stack used by ingest, signage, and source-backed preview tooling.
  - `instagram-poster/requirements.txt` adds the Flask runtime dependency used by the web app.

## Documentation

- **[README.md](README.md)** — architecture, supported commands, and repo navigation
- **[SETUP.md](SETUP.md)** — deployment cutover, secrets inventory, operator-vs-agent ownership, and weekly runbook
- **[google-apps-script/sports-email-sender.gs](google-apps-script/sports-email-sender.gs)** — Gmail sender configuration and approved-send flow
- **`Dockerfile` + `deploy/cloudrun/service.template.yaml`** — repo-owned Cloud Run deployment artifacts
- **`.firebaserc` + `firebase.json`** — repo-owned Firebase Hosting front-door configuration

## Technologies

- **Python 3.11+** — scraping, rendering, signage generation, poster tooling, and Flask runtime
- **Flask** — deployed app serving `/`, `/emails`, and email APIs
- **Google Cloud Run** — production Python compute/runtime target
- **Firebase Hosting** — public hosting layer and custom-domain front door
- **Firebase Firestore** — weekly draft, approval, and sent-state storage
- **GitHub Actions** — scheduled Sunday ingest and daily signage regeneration
- **Google Apps Script** — Gmail delivery for approved payloads only
- **Cloudflare DNS** — registrar/DNS management for the production hostname

## Author

**Jacob Barkin** (jbarkin28@kentdenver.org)  
Student Leadership Media Team

---

**Last Updated:** March 2026
