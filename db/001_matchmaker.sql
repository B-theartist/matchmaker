BEGIN;

CREATE TABLE consultants (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    workspace_user_id text NOT NULL UNIQUE,
    display_name text NOT NULL CHECK (trim(display_name) <> ''),
    project_context text NOT NULL DEFAULT ''
);

CREATE TABLE skills (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL UNIQUE CHECK (trim(name) <> '')
);

CREATE TABLE consultant_skills (
    consultant_id bigint NOT NULL REFERENCES consultants(id),
    skill_id bigint NOT NULL REFERENCES skills(id),
    PRIMARY KEY (consultant_id, skill_id)
);

CREATE TABLE help_requests (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sender_id bigint NOT NULL REFERENCES consultants(id),
    recipient_id bigint NOT NULL REFERENCES consultants(id),
    skill_id bigint NOT NULL REFERENCES skills(id),
    kind text NOT NULL CHECK (kind IN ('knowledge_sharing', 'technical_review')),
    message text NOT NULL CHECK (trim(message) <> ''),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (sender_id <> recipient_id)
);

COMMIT;
