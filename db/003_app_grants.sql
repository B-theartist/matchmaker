-- 003: give the deployed app's identity (its service principal) exactly the access it needs.
--
-- databricks.yml (CAN_CONNECT_AND_CREATE) lets the app LOG IN to the database.
-- The tables were created by Braeden, so he owns them; the app can't touch them
-- until the owner grants it. Least privilege: only the verbs each route uses.
--
-- Run with the app's role name (its service principal client ID):
--   databricks psql --project matchmaker -p koantek-free -- -d databricks_postgres \
--     -v app_role=<service_principal_client_id> -f db/003_app_grants.sql

BEGIN;

GRANT USAGE ON SCHEMA public TO :"app_role";

GRANT SELECT                 ON consultants, skills, consultant_skills, help_requests TO :"app_role";
GRANT INSERT, UPDATE         ON consultants       TO :"app_role";  -- save / edit My Profile
GRANT INSERT                 ON skills            TO :"app_role";  -- first person to list a new skill
GRANT INSERT, DELETE         ON consultant_skills TO :"app_role";  -- add / remove my skills
GRANT INSERT                 ON help_requests     TO :"app_role";  -- send a request (never edit/delete)

GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO :"app_role";  -- generated ids

COMMIT;
