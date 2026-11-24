# Skill & Knowledge Matchmaker

A small internal app for a consulting firm: consultants list what they're working on and
which skills they can help with, find colleagues on other engagements who know a skill,
and send them an asynchronous **knowledge-sharing** or **technical-review** request.

Built on Databricks: **React + TypeScript** UI, **FastAPI** backend, **Lakebase** (serverless
Postgres), deployed as a **Databricks App** and defined end to end as a
**Declarative Automation Bundle** (`databricks.yml`), with **GitHub Actions** for CI/CD.

```
Browser (React) -> Databricks Apps sign-in proxy -> FastAPI (app.py) -> Lakebase (Postgres)
  what you see       adds who you are                the rules            where data lives
```

## What's where

| Path | What it is |
|---|---|
| `frontend/` | React + TypeScript (Vite). Four tabs: My Profile, Find Peers, Inbox, Sent. |
| `app.py` | FastAPI: every `/api` route; also serves the built React app. OpenAPI docs at `/docs`. |
| `server/auth.py` | Who is calling: trusted `X-Forwarded-*` headers from the Databricks Apps proxy. |
| `server/db.py` | Lakebase connection pool; the password is a short-lived OAuth token, never stored. |
| `server/models.py` | Pydantic request/response models (input validation + `/docs`). |
| `db/001–003` | Schema, case-insensitive skills + indexes, least-privilege grants for the app. |
| `db/004, 005, demo_remove.sql` | Demo data only (three seeded colleagues, tagged `demo-`). |
| `databricks.yml` | The bundle: the app, its Lakebase project/branch/database, two targets. |
| `tests/` | API unit tests (no database needed). |
| `.github/workflows/ci-cd.yml` | CI on pull requests, CD to prod on merge to main. |

## Data model

`consultants` (one per signed-in user) ⟷ `consultant_skills` ⟷ `skills`, and
`help_requests` (sender → recipient, about one skill, kind = knowledge_sharing | technical_review).
Integrity lives in Postgres (foreign keys, CHECKs, a unique index on `lower(skills.name)`);
rules that depend on current state (the recipient still offers that skill, the sender is the
signed-in user) live in the API.

## Environments (bundle targets)

| Target | App | Lakebase branch | Deployed by |
|---|---|---|---|
| `dev` | `matchmaker-dev` | `dev` (copy-on-write test copy) | You, from your laptop |
| `prod` | `matchmaker` | `production` | GitHub Actions, after merge + approval |

Databricks Free Edition has a single workspace, so both targets live in it. With separate
workspaces, only each target's `workspace.host` would change.

## Run it locally

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
databricks auth login --host <workspace-url> --profile koantek-free
./scripts/dev.sh                         # backend on :8000 against the dev branch
(cd frontend && npm install && npm run dev)   # UI on :5173 with a local user switcher
.venv/bin/pytest -v                      # tests
```

## Deploy

```bash
(cd frontend && npm run build)
databricks bundle validate -t dev -p koantek-free
databricks bundle deploy   -t dev -p koantek-free
databricks bundle run matchmaker -t dev -p koantek-free
```

Prod is deployed by the `CI/CD` workflow. It signs in as the `matchmaker-deployer` service
principal (OAuth M2M; secrets `DATABRICKS_CLIENT_ID` / `DATABRICKS_CLIENT_SECRET`) and waits
for approval on the `production` environment.

## Status

Walking skeleton: register, discover, request, inbox/sent are working end to end.
Planned: replies and request status, notifications, an analytics view of skill demand vs supply.
