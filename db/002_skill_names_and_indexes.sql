-- 002: case-insensitive skill names + indexes for the app's most common lookups.
-- Safe to run on the live database: it only adds an index-backed rule and indexes.

BEGIN;

-- "SQL", "sql" and "Sql" are the same skill. The UNIQUE(name) from 001 is
-- case-sensitive, so this stops near-duplicates from splitting search results.
CREATE UNIQUE INDEX IF NOT EXISTS skills_name_lower_key ON skills (lower(name));

-- Find Peers: "who lists skill X?" (the primary key already covers consultant_id first)
CREATE INDEX IF NOT EXISTS consultant_skills_skill_id_idx ON consultant_skills (skill_id);

-- Inbox (recipient_id = me) and Sent (sender_id = me), newest first
CREATE INDEX IF NOT EXISTS help_requests_recipient_idx ON help_requests (recipient_id, created_at DESC);
CREATE INDEX IF NOT EXISTS help_requests_sender_idx    ON help_requests (sender_id, created_at DESC);

COMMIT;
