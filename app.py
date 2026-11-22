"""Skill & Knowledge Matchmaker - FastAPI backend.

Every /api route follows the same pattern:
  1. figure out WHO is calling (server/auth.py - never trusted from the request body)
  2. validate the input (server/models.py)
  3. run SQL inside one transaction (server/db.py)
  4. return JSON shaped by a model
"""

import re
from contextlib import asynccontextmanager
from pathlib import Path

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from psycopg_pool import PoolTimeout

from server import db
from server.auth import Caller, current_caller
from server.models import (
    Consultant,
    HelpRequest,
    HelpRequestIn,
    Me,
    ProfileIn,
    SkillWithCount,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.open_pool()
    yield
    db.close_pool()


app = FastAPI(
    title="Skill & Knowledge Matchmaker",
    description="Find consultants with the expertise you need and ask them for async help.",
    version="0.1.0",
    lifespan=lifespan,
)


# A database outage should look different from "no results": 503, not an empty list.
@app.exception_handler(psycopg.OperationalError)
@app.exception_handler(PoolTimeout)
async def database_unavailable(_request, exc):
    return JSONResponse(status_code=503, content={"detail": "Database unavailable"})


# ---------- health ----------

@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    """The web server is up (says nothing about the database)."""
    return {"status": "ok"}


@app.get("/api/health/db", tags=["health"])
def health_db() -> dict[str, str]:
    """The web server can reach Lakebase and run a query."""
    with db.transaction() as cur:
        cur.execute("SELECT current_user AS db_user, now()::text AS db_time")
        row = cur.fetchone()
    return {"status": "ok", **row}


# ---------- shared SQL ----------

# One consultant + their skills as a JSON list (json_agg). Used by several routes.
CONSULTANT_SQL = """
SELECT c.id, c.display_name, c.project_context,
       COALESCE(
         json_agg(json_build_object('id', s.id, 'name', s.name) ORDER BY s.name)
           FILTER (WHERE s.id IS NOT NULL),
         '[]'
       ) AS skills
FROM consultants c
LEFT JOIN consultant_skills cs ON cs.consultant_id = c.id
LEFT JOIN skills s ON s.id = cs.skill_id
"""

REQUEST_SQL = """
SELECT r.id, r.kind, r.message, r.created_at,
       json_build_object('id', s.id, 'name', s.name)               AS skill,
       json_build_object('id', a.id, 'display_name', a.display_name) AS sender,
       json_build_object('id', b.id, 'display_name', b.display_name) AS recipient
FROM help_requests r
JOIN skills s      ON s.id = r.skill_id
JOIN consultants a ON a.id = r.sender_id
JOIN consultants b ON b.id = r.recipient_id
"""


def _my_consultant_id(cur, caller: Caller) -> int | None:
    cur.execute(
        "SELECT id FROM consultants WHERE workspace_user_id = %s", (caller.user_id,)
    )
    row = cur.fetchone()
    return row["id"] if row else None


def _clean_skill_names(names: list[str]) -> list[str]:
    """Trim, collapse spaces, drop blanks, and de-duplicate ignoring case."""
    seen, out = set(), []
    for raw in names:
        name = re.sub(r"\s+", " ", raw).strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            out.append(name[:60])
    return out


# ---------- my profile ----------

@app.get("/api/me", response_model=Me, tags=["profile"])
def get_me(caller: Caller = Depends(current_caller)):
    """Who am I, and have I created my profile yet?"""
    with db.transaction() as cur:
        cur.execute(CONSULTANT_SQL + " WHERE c.workspace_user_id = %s GROUP BY c.id",
                    (caller.user_id,))
        profile = cur.fetchone()
    return {"email": caller.email, "profile": profile}


@app.put("/api/me", response_model=Consultant, tags=["profile"])
def save_me(body: ProfileIn, caller: Caller = Depends(current_caller)):
    """Create or update MY profile (name, current project, skills) in one transaction.
    The row is keyed on the signed-in identity, so you can only ever edit your own."""
    if not body.display_name.strip():
        raise HTTPException(422, "Display name can't be blank")
    skills = _clean_skill_names(body.skills)

    with db.transaction() as cur:
        # Upsert: insert the first time, update every time after.
        cur.execute(
            """
            INSERT INTO consultants (workspace_user_id, display_name, project_context)
            VALUES (%s, %s, %s)
            ON CONFLICT (workspace_user_id)
            DO UPDATE SET display_name = EXCLUDED.display_name,
                          project_context = EXCLUDED.project_context
            RETURNING id
            """,
            (caller.user_id, body.display_name.strip(), body.project_context.strip()),
        )
        me_id = cur.fetchone()["id"]

        # Reuse an existing skill if the name matches ignoring case ("sql" == "SQL").
        skill_ids = []
        for name in skills:
            cur.execute(
                "INSERT INTO skills (name) VALUES (%s) ON CONFLICT ((lower(name))) DO NOTHING",
                (name,),
            )
            cur.execute("SELECT id FROM skills WHERE lower(name) = lower(%s)", (name,))
            skill_ids.append(cur.fetchone()["id"])

        # Make my skill list exactly what the form sent.
        cur.execute(
            "DELETE FROM consultant_skills WHERE consultant_id = %s AND skill_id <> ALL(%s)",
            (me_id, skill_ids),
        )
        for sid in skill_ids:
            cur.execute(
                "INSERT INTO consultant_skills (consultant_id, skill_id) VALUES (%s, %s) "
                "ON CONFLICT DO NOTHING",
                (me_id, sid),
            )

        cur.execute(CONSULTANT_SQL + " WHERE c.id = %s GROUP BY c.id", (me_id,))
        return cur.fetchone()


# ---------- discovery ----------

@app.get("/api/skills", response_model=list[SkillWithCount], tags=["discovery"])
def list_skills(_caller: Caller = Depends(current_caller)):
    """Every skill anyone has listed, with how many consultants offer it."""
    with db.transaction() as cur:
        cur.execute(
            """
            SELECT s.id, s.name, count(cs.consultant_id)::int AS consultant_count
            FROM skills s
            LEFT JOIN consultant_skills cs ON cs.skill_id = s.id
            GROUP BY s.id
            HAVING count(cs.consultant_id) > 0
            ORDER BY lower(s.name)
            """
        )
        return cur.fetchall()


@app.get("/api/consultants", response_model=list[Consultant], tags=["discovery"])
def search_consultants(
    skill_id: int | None = Query(None, description="Only people who list this skill"),
    caller: Caller = Depends(current_caller),
):
    """Find peers (everyone except me), optionally filtered to one skill."""
    with db.transaction() as cur:
        cur.execute(
            CONSULTANT_SQL
            + """
            WHERE c.workspace_user_id <> %(me)s
              AND (%(skill_id)s::bigint IS NULL OR EXISTS (
                    SELECT 1 FROM consultant_skills x
                    WHERE x.consultant_id = c.id AND x.skill_id = %(skill_id)s))
            GROUP BY c.id
            ORDER BY c.display_name
            """,
            {"me": caller.user_id, "skill_id": skill_id},
        )
        return cur.fetchall()


# ---------- help requests ----------

@app.post("/api/requests", response_model=HelpRequest, status_code=201, tags=["requests"])
def create_request(body: HelpRequestIn, caller: Caller = Depends(current_caller)):
    """Send a knowledge-sharing or technical-review request to a peer.
    The SENDER is always the signed-in caller - the browser can't choose it."""
    with db.transaction() as cur:
        sender_id = _my_consultant_id(cur, caller)
        if sender_id is None:
            raise HTTPException(409, "Create your profile before sending requests")
        if body.recipient_id == sender_id:
            raise HTTPException(422, "You can't send a request to yourself")

        cur.execute("SELECT 1 FROM consultants WHERE id = %s", (body.recipient_id,))
        if cur.fetchone() is None:
            raise HTTPException(404, "Recipient not found")

        # The foreign key proves the skill exists; this proves the recipient offers it.
        cur.execute(
            "SELECT 1 FROM consultant_skills WHERE consultant_id = %s AND skill_id = %s",
            (body.recipient_id, body.skill_id),
        )
        if cur.fetchone() is None:
            raise HTTPException(422, "That person doesn't list this skill")

        cur.execute(
            """
            INSERT INTO help_requests (sender_id, recipient_id, skill_id, kind, message)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (sender_id, body.recipient_id, body.skill_id, body.kind, body.message.strip()),
        )
        new_id = cur.fetchone()["id"]
        cur.execute(REQUEST_SQL + " WHERE r.id = %s", (new_id,))
        return cur.fetchone()


@app.get("/api/requests/inbox", response_model=list[HelpRequest], tags=["requests"])
def inbox(caller: Caller = Depends(current_caller)):
    """Requests other people sent ME (filtered by recipient_id = me)."""
    with db.transaction() as cur:
        me_id = _my_consultant_id(cur, caller)
        if me_id is None:
            return []
        cur.execute(REQUEST_SQL + " WHERE r.recipient_id = %s ORDER BY r.created_at DESC",
                    (me_id,))
        return cur.fetchall()


@app.get("/api/requests/sent", response_model=list[HelpRequest], tags=["requests"])
def sent(caller: Caller = Depends(current_caller)):
    """Requests I sent (filtered by sender_id = me)."""
    with db.transaction() as cur:
        me_id = _my_consultant_id(cur, caller)
        if me_id is None:
            return []
        cur.execute(REQUEST_SQL + " WHERE r.sender_id = %s ORDER BY r.created_at DESC",
                    (me_id,))
        return cur.fetchall()


# ---------- React frontend ----------
# The built React app (frontend/dist) is served from the same app at "/".
# Mounted last so it never shadows the /api routes above.
_dist = Path(__file__).parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
