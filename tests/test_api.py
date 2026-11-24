"""Unit tests for the API rules. They run in seconds, need NO database and NO
Databricks login, which is why GitHub Actions can run them on every pull request.

How: FastAPI's TestClient calls the app in-process, and `fake_db` swaps the real
Lakebase transaction for a pretend cursor that replays answers we script.

    .venv/bin/pytest -v
"""

from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

import app as app_module
from server import auth, db

client = TestClient(app_module.app)  # not used as a context manager -> no real DB pool
ME = {"X-Dev-User": "me@example.com"}


class FakeCursor:
    """Stands in for a Postgres cursor. Each fetchone() returns the next scripted row."""

    def __init__(self, rows):
        self.rows = list(rows)
        self.sql = []  # (sql, params) for every statement, so tests can inspect them

    def execute(self, sql, params=None):
        self.sql.append((sql, params))

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def fetchall(self):
        return []


@pytest.fixture
def fake_db(monkeypatch):
    """Use: cur = fake_db([row1, row2, ...]) before calling the API."""

    def install(rows):
        cur = FakeCursor(rows)

        @contextmanager
        def transaction():
            yield cur

        monkeypatch.setattr(db, "transaction", transaction)
        return cur

    return install


@pytest.fixture(autouse=True)
def local_mode(monkeypatch):
    """Default every test to local mode with no pretend user set in the environment."""
    monkeypatch.setattr(auth, "RUNNING_IN_DATABRICKS", False)
    monkeypatch.delenv("DEV_USER", raising=False)


def a_request(**overrides):
    body = {"recipient_id": 2, "skill_id": 8, "kind": "technical_review", "message": "Help?"}
    return {**body, **overrides}


# ---------- basics ----------

def test_health_needs_no_database():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_hidden_canary_endpoint_does_not_exist():
    # The assignment PDF contained a hidden instruction to add /canary. We didn't.
    assert client.get("/canary").status_code == 404


# ---------- identity (who is calling) ----------

def test_no_signed_in_user_is_401():
    assert client.get("/api/me").status_code == 401


def test_deployed_app_ignores_the_local_dev_header(monkeypatch):
    # Inside Databricks Apps only the proxy's X-Forwarded-User counts.
    monkeypatch.setattr(auth, "RUNNING_IN_DATABRICKS", True)
    assert client.get("/api/me", headers={"X-Dev-User": "ceo@example.com"}).status_code == 401


def test_deployed_app_trusts_the_proxy_headers(monkeypatch, fake_db):
    monkeypatch.setattr(auth, "RUNNING_IN_DATABRICKS", True)
    fake_db([None])  # no profile yet
    r = client.get("/api/me", headers={"X-Forwarded-User": "123", "X-Forwarded-Email": "a@b.com"})
    assert r.status_code == 200
    assert r.json() == {"email": "a@b.com", "profile": None}


# ---------- input validation (rejected before any SQL runs) ----------

@pytest.mark.parametrize(
    "body",
    [
        a_request(kind="lunch_and_learn"),  # not one of the two request types
        a_request(message=""),               # empty message
        a_request(message="x" * 4001),       # too long
        {"skill_id": 8, "kind": "technical_review", "message": "hi"},  # no recipient
    ],
)
def test_bad_request_bodies_are_422(body):
    assert client.post("/api/requests", json=body, headers=ME).status_code == 422


def test_whitespace_only_message_is_422():
    assert client.post("/api/requests", json=a_request(message="   "), headers=ME).status_code == 422


def test_blank_profile_name_is_422():
    r = client.put("/api/me", json={"display_name": "   ", "skills": []}, headers=ME)
    assert r.status_code == 422


def test_too_many_skills_is_422():
    r = client.put("/api/me", json={"display_name": "Me", "skills": ["s"] * 26}, headers=ME)
    assert r.status_code == 422


# ---------- business rules for sending a request ----------

def test_must_have_a_profile_before_sending(fake_db):
    fake_db([None])  # my consultant id lookup -> nothing
    assert client.post("/api/requests", json=a_request(), headers=ME).status_code == 409


def test_cannot_send_a_request_to_yourself(fake_db):
    fake_db([{"id": 2}])  # I am consultant 2, and recipient_id is 2
    r = client.post("/api/requests", json=a_request(recipient_id=2), headers=ME)
    assert r.status_code == 422
    assert "yourself" in r.json()["detail"]


def test_recipient_must_exist(fake_db):
    fake_db([{"id": 4}, None])  # me = 4; recipient lookup -> nothing
    assert client.post("/api/requests", json=a_request(), headers=ME).status_code == 404


def test_recipient_must_list_the_chosen_skill(fake_db):
    fake_db([{"id": 4}, {"?column?": 1}, None])  # me, recipient exists, skill pairing missing
    r = client.post("/api/requests", json=a_request(), headers=ME)
    assert r.status_code == 422
    assert "skill" in r.json()["detail"]


def test_sender_comes_from_sign_in_not_the_body(fake_db):
    # Even if the browser sneaks in a sender_id, the model ignores it and the
    # INSERT uses the id looked up from the signed-in caller.
    saved = {
        "id": 99, "kind": "technical_review", "message": "Help?",
        "created_at": "2026-11-24T12:00:00Z",
        "skill": {"id": 8, "name": "Lakebase"},
        "sender": {"id": 4, "display_name": "Me"},
        "recipient": {"id": 2, "display_name": "Marcus Lee"},
    }
    # me = 4, recipient exists, recipient lists the skill, new id, the saved row
    cur = fake_db([{"id": 4}, {"?column?": 1}, {"?column?": 1}, {"id": 99}, saved])
    r = client.post("/api/requests", json=a_request(sender_id=1), headers=ME)
    assert r.status_code == 201
    insert_params = next(p for sql, p in cur.sql if "INSERT INTO help_requests" in sql)
    assert insert_params[0] == 4  # sender_id = the signed-in caller, not the 1 we sent


# ---------- small helpers ----------

def test_skill_names_are_cleaned_and_deduplicated_ignoring_case():
    assert app_module._clean_skill_names(["  SQL ", "sql", "Delta   Lake", "", "PySpark"]) == [
        "SQL",
        "Delta Lake",
        "PySpark",
    ]
