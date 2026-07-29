from django.db import migrations

SQL_UP = """
ALTER TABLE reconciliation_record ENABLE ROW LEVEL SECURITY;
CREATE POLICY record_isolation ON reconciliation_record
    USING (org_id = current_setting('app.current_org_id', true));

ALTER TABLE reconciliation_entry ENABLE ROW LEVEL SECURITY;
CREATE POLICY entry_isolation ON reconciliation_entry
    USING (org_id = current_setting('app.current_org_id', true));

ALTER TABLE reconciliation_exception ENABLE ROW LEVEL SECURITY;
CREATE POLICY exception_isolation ON reconciliation_exception
    USING (org_id = current_setting('app.current_org_id', true));

-- dealeros_app is the runtime role the web app connects as (see
-- settings.py / DJANGO_DB_ROLE). It must NOT own these tables --
-- Postgres exempts the table OWNER (and superusers) from RLS by default.
-- dealeros_owner (below) owns these tables because it ran the migration;
-- dealeros_app is a completely separate, non-owning role, so plain
-- ENABLE ROW LEVEL SECURITY already restricts it fully -- no FORCE
-- needed on that side.
--
-- We deliberately do NOT add FORCE ROW LEVEL SECURITY. FORCE would also
-- restrict dealeros_owner (the table owner) despite the owner exemption,
-- which sounds like a stronger guarantee but actually breaks the two
-- legitimate jobs that must run as owner: ingest_csv and reconcile both
-- write rows belonging to EVERY org in a single run (they are loading/
-- computing the whole dataset, not serving one tenant's request) -- no
-- single current_org_id value could ever satisfy a FORCEd policy across
-- multiple orgs in one transaction. The owner role is trusted precisely
-- because it is never used to serve a live user request (see
-- CurrentOrgMiddleware and README) -- only migrations and these two
-- explicitly-run admin commands use it.
GRANT SELECT, INSERT, UPDATE, DELETE ON reconciliation_record TO dealeros_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON reconciliation_entry TO dealeros_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON reconciliation_exception TO dealeros_app;
GRANT SELECT ON tenancy_org TO dealeros_app;
GRANT SELECT ON tenancy_location TO dealeros_app;
GRANT SELECT ON tenancy_userorgmembership TO dealeros_app;
GRANT SELECT ON auth_user TO dealeros_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO dealeros_app;
"""

SQL_DOWN = """
DROP POLICY IF EXISTS record_isolation ON reconciliation_record;
ALTER TABLE reconciliation_record DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS entry_isolation ON reconciliation_entry;
ALTER TABLE reconciliation_entry DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS exception_isolation ON reconciliation_exception;
ALTER TABLE reconciliation_exception DISABLE ROW LEVEL SECURITY;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("reconciliation", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL_UP, reverse_sql=SQL_DOWN),
    ]
