-- Removes ALL demo data (rows from 004/005). Real profiles are untouched.
-- Order matters: foreign keys mean children go before parents.
--
--   databricks psql --project matchmaker --branch production -p koantek-free -- \
--     -d databricks_postgres -f db/demo_remove.sql

BEGIN;

DELETE FROM help_requests
WHERE sender_id    IN (SELECT id FROM consultants WHERE workspace_user_id LIKE 'demo-%')
   OR recipient_id IN (SELECT id FROM consultants WHERE workspace_user_id LIKE 'demo-%');

DELETE FROM consultant_skills
WHERE consultant_id IN (SELECT id FROM consultants WHERE workspace_user_id LIKE 'demo-%');

DELETE FROM consultants WHERE workspace_user_id LIKE 'demo-%';

-- Skills nobody lists any more (the app already hides these; this tidies the table).
DELETE FROM skills s
WHERE NOT EXISTS (SELECT 1 FROM consultant_skills cs WHERE cs.skill_id = s.id)
  AND NOT EXISTS (SELECT 1 FROM help_requests hr     WHERE hr.skill_id = s.id);

COMMIT;
