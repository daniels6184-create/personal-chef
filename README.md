# Personal Chef

A private, single-user chef and sports-nutrition app. Installable on Android as a PWA.

**Status: Stage A (foundation).** Sign-in (password + passkeys), profile, body measurements,
nutrition targets with an approval flow, data export, encrypted backups. The diary, chef, food
recognition, planner, pantry and training link are later stages and are **not** in this release.

## How it fits together

| Part | What | Where |
|---|---|---|
| `frontend/` | Svelte 5 PWA (Vite, Workbox service worker) | Built into the Docker image |
| `backend/` | FastAPI, SQLAlchemy, Alembic migrations | Render free web service (Docker) |
| Database | Postgres | Neon free project `personal-chef` (Europe) |
| Backups | Nightly `pg_dump`, encrypted with `age`, kept 90 days | GitHub Actions artifacts |

Rules that the code enforces:
- Nutrition targets are only ever **proposed**; one becomes active only when you tap Approve.
  The database allows a single active target. No route edits or deletes a target.
- Every state-changing request needs the `X-Requested-With: personal-chef` header and a matching
  Origin (blocks cross-site forgery). Login is throttled: 5 failures per IP, 20 overall, per 15 min.
- `/healthz` never touches the database, so health checks don't wake Neon. The app opens a new
  database connection per request (no pool), so Neon can scale to zero when you're not using it.
- Logs contain request paths and status codes only, never bodies.

## First deploy (once, about 20 minutes)

1. **Neon** → your existing account → *New project* `personal-chef`, region Europe (Frankfurt),
   Postgres 17. Copy the connection string.
2. **Render** → *New* → *Blueprint* → pick this repo. It reads `render.yaml` and asks for:
   - `DATABASE_URL`: the Neon string.
   - `APP_PASSWORD`: long and unique (a password manager's 24+ characters). It's the backup sign-in.
   - `APP_ORIGIN`: `https://personal-chef.onrender.com`, or whatever address Render gives you,
     **exactly**, with no trailing slash. Passkeys are tied to this address.
   Tables and your starting profile are created on first boot.
3. Open the address in **Chrome on your phone** → sign in with the password → ⋮ menu →
   **Add to Home screen** (or **Install app**).
4. In the app: **Settings → Add a passkey on this device**. From then on, sign in with your fingerprint.

The free instance sleeps after 15 minutes idle. The first open after that takes up to about a
minute; the app shows "Warming up the kitchen" and your last-loaded profile and targets in the meantime.

## Backups (once, about 10 minutes)

1. Install `age` on your PC and run `age-keygen -o personal-chef-backup-key.txt`. **Keep this
   file in your password manager.** Without it the backups cannot be opened, by anyone.
2. In Neon, create a **read-only** role for backups (SQL editor):
   ```sql
   CREATE ROLE chef_backup WITH LOGIN PASSWORD '<long random>';
   GRANT pg_read_all_data TO chef_backup;
   ```
3. In GitHub → this repo → Settings → Secrets and variables → Actions:
   - Secret `BACKUP_DATABASE_URL`: the Neon string with `chef_backup` as the user.
   - Variable `AGE_RECIPIENT`: the `age1...` public key printed by `age-keygen`.
4. Actions → Backup → *Run workflow* once to check it, then it runs nightly at 03:17 UTC.

**Restore** (into an empty database only; the script refuses one that has tables):
```
TARGET_DATABASE_URL=postgresql://... scripts/restore.sh personal-chef-2026-11-20.dump.age personal-chef-backup-key.txt
```
**Export** any time from Settings → Export all data (JSON).

## Working on it locally

```
python -m venv .venv && .venv/bin/pip install -r backend/requirements-dev.txt
cd frontend && npm ci && npm run build && cd ..
# a local Postgres, then:
cd backend
DATABASE_URL=postgresql://localhost/chef APP_PASSWORD=dev-pass APP_ORIGIN=http://localhost:8000 \
  COOKIE_SECURE=false FRONTEND_DIR=../frontend/dist ../.venv/bin/alembic upgrade head
# same env vars, then: ../.venv/bin/uvicorn app.main:app --port 8000
```

Tests:
- `cd backend && TEST_DATABASE_URL=postgresql://localhost/chef_test ../.venv/bin/python -m pytest`
  (wipes that database on every test).
- Phone end-to-end (Pixel 7 emulation, real passkey via a virtual authenticator):
  `BASE=http://localhost:8000 PASSWORD=dev-pass node e2e/smoke.cjs` (needs Playwright).
- `scripts/reset_dev_db.sh` wipes and re-seeds a **local** database (refuses Neon/Render URLs).

Changing the database: add a migration in `backend/migrations/versions/`, never edit an old one.

## Costs

£0. Render free web service, Neon free project, GitHub Actions on a private repo. Nothing here
can bill you: no card is on file, Neon refuses writes at its storage cap instead of charging, and
the backup job uses about 1 minute of Actions time a day.
