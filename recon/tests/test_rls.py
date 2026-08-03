import psycopg2

from config import settings
from recon.models import Discrepancy
from tenancy.models import Org, Location
from django.test import TransactionTestCase

def _raw_connect_as_app():
    return psycopg2.connect(
        dbname=settings.DATABASES["default"]["NAME"],
        user="adosx_app",
        password="adosx_app",
        host=settings.DATABASES["default"]["HOST"],
        port=settings.DATABASES["default"]["PORT"],
    )
class TestRLS(TransactionTestCase):
    def setUp(self):
        self.org_a = Org.objects.create(org_id="ORG-A", name="ORG-A")
        self.org_b = Org.objects.create(org_id="ORG-B", name="ORG-B")
        loc_a = Location.objects.create(location_id="LOC-A1", org=self.org_a, name="A1")
        loc_b = Location.objects.create(location_id="LOC-B1", org=self.org_b, name="B1")
        Discrepancy.objects.create(
            org=self.org_a, location=loc_a, reason_code="MISSING_IN_B",
            summary="org A secret", detail={},
        )
        Discrepancy.objects.create(
            org=self.org_b, location=loc_b, reason_code="MISSING_IN_B",
            summary="org B secret", detail={},
        )

    def _rows_visible_as_org(self, org_id):
        conn = _raw_connect_as_app()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.current_org_id', %s, false)", [org_id])
                cur.execute("SELECT summary FROM recon_exception")  # no WHERE clause, on purpose
                rows = cur.fetchall()
                print("Angeerasa", rows)
                return [row[0] for row in rows]
        finally:
            conn.close()

    def test_org_a_cannot_see_org_b_rows(self):
        rows = self._rows_visible_as_org("ORG-A")
        self.assertIn("org A secret", rows)
        self.assertNotIn("org B secret", rows)

    def test_org_b_cannot_see_org_a_rows(self):
        rows = self._rows_visible_as_org("ORG-B")
        self.assertIn("org B secret", rows)
        self.assertNotIn("org A secret", rows)

    def test_no_org_set_returns_nothing(self):
        rows = self._rows_visible_as_org("")
        self.assertEqual(rows, [])