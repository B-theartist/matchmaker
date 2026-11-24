-- 004: three demo consultants so "Find peers" has someone to find.
--
-- Why: in a real rollout every consultant signs in and fills in their own profile.
-- For a one-person demo workspace we seed three fake colleagues instead.
-- Their workspace_user_id starts with "demo-", so they can never collide with a
-- real Databricks user and are easy to find and remove (db/demo_remove.sql).
-- Safe to run twice: existing demo rows are left alone.
--
--   databricks psql --project matchmaker --branch production -p koantek-free -- \
--     -d databricks_postgres -f db/004_seed_demo_people.sql

BEGIN;

-- 1. The people
INSERT INTO consultants (workspace_user_id, display_name, project_context) VALUES
  ('demo-priya',  'Priya Shah',
   'Migrating a retail client''s on-prem Hadoop jobs to Databricks. Currently building Delta Live Tables pipelines and setting up Unity Catalog permissions.'),
  ('demo-marcus', 'Marcus Lee',
   'Building a customer-support app for an insurance client on Databricks Apps (FastAPI + React) backed by Lakebase.'),
  ('demo-elena',  'Elena Ruiz',
   'Churn model for a telecom client. Tracking experiments in MLflow and serving the model with Model Serving.')
ON CONFLICT (workspace_user_id) DO NOTHING;

-- 2. The skills (case-insensitive: reuses "fastapi" if someone already typed it)
INSERT INTO skills (name) VALUES
  ('Delta Live Tables'), ('Unity Catalog'), ('PySpark'), ('SQL'),
  ('Databricks Apps'), ('FastAPI'), ('React'), ('Lakebase'),
  ('MLflow'), ('Python'), ('Model Serving')
ON CONFLICT ((lower(name))) DO NOTHING;

-- 3. Who knows what
INSERT INTO consultant_skills (consultant_id, skill_id)
SELECT c.id, s.id
FROM (VALUES
  ('demo-priya',  'Delta Live Tables'), ('demo-priya',  'Unity Catalog'),
  ('demo-priya',  'PySpark'),           ('demo-priya',  'SQL'),
  ('demo-marcus', 'Databricks Apps'),   ('demo-marcus', 'FastAPI'),
  ('demo-marcus', 'React'),             ('demo-marcus', 'Lakebase'),
  ('demo-elena',  'MLflow'),            ('demo-elena',  'Python'),
  ('demo-elena',  'Model Serving'),     ('demo-elena',  'PySpark')
) AS pair(who, skill)
JOIN consultants c ON c.workspace_user_id = pair.who
JOIN skills      s ON lower(s.name) = lower(pair.skill)
ON CONFLICT DO NOTHING;

COMMIT;
