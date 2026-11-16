-- Run ONCE in the Supabase SQL editor, and again after any migration that
-- adds tables (the default privileges below make that automatic for tables
-- created by the postgres role, which is what Django connects as).
--
-- Why: Supabase exposes every table in `public` through its auto-generated
-- REST API, authorised by the project's anon key - which is public by design
-- (it ships in browser apps). Django tables are only protected by Django.
-- Without this, anyone holding the anon key could read or write budget data.
-- Also turn the Data API off: Project Settings -> Data API (belt and braces).
--
-- Django is unaffected: it connects as `postgres`, which owns the tables and
-- bypasses RLS.

DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', r.tablename);
  END LOOP;
END $$;

REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon, authenticated;

ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES    FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM anon, authenticated;
