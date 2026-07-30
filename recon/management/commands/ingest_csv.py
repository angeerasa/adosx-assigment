import re
from decimal import Decimal, InvalidOperation

import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction

from tenancy.models import Location, Org
from recon.models import Entry, Record

DATA_DIR = "data"

def normalize_ref(raw: str) -> str:
    digits = re.sub(r"\D", "", str(raw))
    return f"REC-{digits}" if digits else str(raw).strip()

def parse_decimal(raw):
    if pd.isna(raw) or str(raw).strip() == "":
        return None
    cleaned = str(raw).strip().replace(",", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None

class Command(BaseCommand):
    help = "Load system_a.csv, system_b.csv and locations.csv into the database using pandas"

    def handle(self, *args, **options):
        with transaction.atomic():
            locations = self._load_locations()
            records_by_id = self._load_system_a_records(locations)
            self._load_entries(records_by_id, locations)
        self.stdout.write(self.style.SUCCESS("Ingest complete."))

    def _load_locations(self):
        df = pd.read_csv(f"{DATA_DIR}/locations.csv", dtype=str, keep_default_na=False)
        locations = {}
        for row in df.itertuples(index=False):
            org, _ = Org.objects.get_or_create(org_id=row.org_id, defaults={"name": row.org_id})
            loc, _ = Location.objects.update_or_create(
                location_id=row.location_id,
                defaults={"org": org, "name": row.location_name},
            )
            locations[loc.location_id] = loc
        self.stdout.write(f"  locations: {len(df)} loaded")
        return locations

    def _load_system_a_records(self, locations):
        df = pd.read_csv(f"{DATA_DIR}/system_a.csv", dtype=str, keep_default_na=False)
        records_by_id = {}
        for row in df.itertuples(index=False):
            loc = locations[row.location_id]
            record, _ = Record.objects.update_or_create(
                record_id=row.record_id,
                defaults=dict(
                    location=loc,
                    org=loc.org,
                    event_date=row.event_date,
                    category_code=row.category_code,
                    actor_id=row.actor_id.strip(),
                    base_value=Decimal(row.base_value),
                    adjustment=Decimal(row.adjustment),
                    total_value=Decimal(row.total_value),
                    state=row.state.strip(),
                ),
            )
            records_by_id[record.record_id] = record

        self.stdout.write(f"  records: {len(df)} loaded")
        return records_by_id

    def _load_entries(self, records_by_id, locations):
        df = pd.read_csv(f"{DATA_DIR}/system_b.csv", dtype=str, keep_default_na=False)
        df["normalized_ref"] = df["record_ref"].apply(normalize_ref)

        created = 0
        for row in df.itertuples(index=False):
            record = records_by_id.get(row.normalized_ref)
            loc = locations.get(row.location_id)
            value = parse_decimal(row.value)
            org = record.org if record else (loc.org if loc else None)

            Entry.objects.update_or_create(
                entry_id=row.entry_id,
                defaults=dict(
                    raw_record_ref=row.record_ref,
                    record=record,
                    location=loc,
                    org=org,
                    recorded_on=row.recorded_on or None,
                    value=value,
                    raw_value=row.value,
                    label=row.label.strip(),
                ),
            )
            created += 1
        self.stdout.write(f"  entries: {created} loaded")