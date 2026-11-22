"""Shapes of data going in and out of the API.

FastAPI uses these to (1) reject bad input automatically with a 422 error and
(2) generate the /docs page. They are the "contract" between React and Python.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RequestKind = Literal["knowledge_sharing", "technical_review"]


class Skill(BaseModel):
    id: int
    name: str


class SkillWithCount(Skill):
    consultant_count: int


class Consultant(BaseModel):
    id: int
    display_name: str
    project_context: str
    skills: list[Skill]


class Me(BaseModel):
    email: str
    profile: Consultant | None  # None until the person saves My Profile the first time


class ProfileIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)
    project_context: str = Field(default="", max_length=2000)
    skills: list[str] = Field(default_factory=list, max_length=25)


class PersonRef(BaseModel):
    id: int
    display_name: str


class HelpRequestIn(BaseModel):
    recipient_id: int
    skill_id: int
    kind: RequestKind
    message: str = Field(min_length=1, max_length=4000)


class HelpRequest(BaseModel):
    id: int
    kind: RequestKind
    message: str
    created_at: datetime
    skill: Skill
    sender: PersonRef
    recipient: PersonRef
