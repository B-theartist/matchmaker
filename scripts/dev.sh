#!/usr/bin/env bash
# Run the backend on your Mac against the Lakebase *dev* branch (a throwaway copy
# of production), signed in to Postgres as YOU via the koantek-free CLI profile.
#
#   ./scripts/dev.sh                 -> pretend to be maya@example.com
#   DEV_USER=jordan@example.com ./scripts/dev.sh
set -euo pipefail
cd "$(dirname "$0")/.."

export DATABRICKS_CONFIG_PROFILE=koantek-free
export LAKEBASE_ENDPOINT="${LAKEBASE_ENDPOINT:-projects/matchmaker/branches/dev/endpoints/primary}"
# No PGUSER here on purpose: server/db.py asks Databricks "who am I?" with your
# CLI login and uses that as the Postgres user. So no email is written in the repo.
export PGDATABASE=databricks_postgres
export DEV_USER="${DEV_USER:-maya@example.com}"
unset PGHOST  # let server/db.py look up the host for LAKEBASE_ENDPOINT

exec .venv/bin/uvicorn app:app --reload --port 8000
