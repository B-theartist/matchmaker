"""Who is calling?

Deployed on Databricks Apps, every request passes through Databricks' sign-in proxy.
The proxy signs the user in with their workspace account and adds trusted headers
(X-Forwarded-User, X-Forwarded-Email). Anything a browser tries to send in those
headers itself is replaced by the proxy, so the backend can trust them.

On your Mac there is no proxy, so local development uses a pretend user instead.
That fallback is switched OFF automatically when running inside Databricks Apps.
"""

import os
from dataclasses import dataclass

from fastapi import HTTPException, Request

# Databricks Apps sets DATABRICKS_APP_NAME in the app's environment.
RUNNING_IN_DATABRICKS = bool(os.environ.get("DATABRICKS_APP_NAME"))


@dataclass
class Caller:
    user_id: str  # stable workspace identity -> consultants.workspace_user_id
    email: str


def current_caller(request: Request) -> Caller:
    if RUNNING_IN_DATABRICKS:
        user_id = request.headers.get("X-Forwarded-User")
        email = request.headers.get("X-Forwarded-Email", "")
    else:
        # Local dev only: pretend to be someone via the X-Dev-User header or DEV_USER env var.
        email = request.headers.get("X-Dev-User") or os.environ.get("DEV_USER", "")
        user_id = email
    if not user_id:
        raise HTTPException(status_code=401, detail="Not signed in")
    return Caller(user_id=user_id, email=email or user_id)
