-- 005 (demo only, run AFTER you've saved your own profile in the app):
-- Marcus sends you a help request so your Inbox isn't empty in the demo.
-- The demo people can't sign in, so this is the only way to receive one in a
-- single-user workspace. "You" = every consultant that isn't a demo- row.
--
--   databricks psql --project matchmaker --branch production -p koantek-free -- \
--     -d databricks_postgres -f db/005_demo_request_to_me.sql

BEGIN;

INSERT INTO skills (name) VALUES ('Lakebase')
ON CONFLICT ((lower(name))) DO NOTHING;

INSERT INTO help_requests (sender_id, recipient_id, skill_id, kind, message)
SELECT marcus.id, me.id, s.id, 'technical_review',
       'Hi! I saw you deployed an app on Lakebase. Could you review how I''m handling the OAuth token refresh in my connection pool before we go live on Friday?'
FROM consultants marcus
JOIN consultants me ON me.workspace_user_id NOT LIKE 'demo-%'
JOIN skills s       ON lower(s.name) = 'lakebase'
WHERE marcus.workspace_user_id = 'demo-marcus'
  AND NOT EXISTS (SELECT 1 FROM help_requests r
                  WHERE r.sender_id = marcus.id AND r.recipient_id = me.id);

COMMIT;
