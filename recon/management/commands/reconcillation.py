"""
Reads ingested Record/Entry rows and writes Discrepancy rows -- one per
disagreement between System A and System B that a human should look at.
Deliberately excludes disagreements that are not errors (the brief asks
explicitly for this): a record legitimately split across two B entries
whose values sum correctly is not flagged, it is just how System B
represents that event.

Usage:
    python manage.py reconcile
"""
from collections import defaultdict
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from recon.models import Discrepancy, Entry, Record

CENTS = Decimal("0.01")


class Command(BaseCommand):
    help = "Compare ingested Record/Entry data and generate Discrepancy rows."

    def handle(self, *args, **options):
        with transaction.atomic():
            Discrepancy.objects.all().delete()  # reconcile is re-runnable/idempotent
            count = 0
            count += self._check_matched_records()
            count += self._check_missing_in_b()
            count += self._check_orphan_entries()
        self.stdout.write(self.style.SUCCESS(f"Reconcile complete: {count} exceptions."))

    # -- helpers ----------------------------------------------------

    def _make(self, *, org, record=None, entry=None, location, reason, summary, detail):
        Discrepancy.objects.create(
            org=org, record=record, entry=entry, location=location,
            reason_code=reason, summary=summary, detail=detail,
        )

    # -- passes -------------------------------------------------------

    def _check_matched_records(self):
        """Every Record that has at least one Entry pointing at it."""
        n = 0
        entries_by_record = defaultdict(list)
        for e in Entry.objects.filter(record__isnull=False).select_related("record", "location"):
            entries_by_record[e.record_id].append(e)

        for record in Record.objects.select_related("location", "org").filter(
            record_id__in=entries_by_record.keys()
        ): #Angeerasa: scope to eliminate Org table completely and use Location table to store org-name
            entries = entries_by_record[record.record_id]

            #Angeerasa: I DON'T WANT TO CONSIDER THIS AS AN EXCEPTION
            # if record.state == "VOIDED":
            #     n += self._flag_voided(record, entries)
            #     continue

            if len(entries) > 1:
                n += self._check_multi_entry(record, entries)
                continue

            n += self._check_single_entry(record, entries[0])
        return n

    #Angeerasa : this function was made irrelevant-> not usages
    def _flag_voided(self, record, entries):
        entry = entries[0]
        self._make(
            org=record.org, record=record, entry=entry, location=record.location,
            reason="VOIDED_BUT_PRESENT",
            summary=(
                f"{record.record_id} was voided in System A but System B still carries "
                f"entry {entry.entry_id} as live. Confirm whether the void should propagate."
            ),
            detail={
                "record_id": record.record_id, "record_state": record.state,
                "entry_id": entry.entry_id, "entry_value": str(entry.value),
            },
        )
        return 1

    def _check_multi_entry(self, record, entries):
        values = [e.value for e in entries if e.value is not None]
        entry_ids = ", ".join(e.entry_id for e in entries)

        if len(values) == len(entries) and sum(values) == record.total_value:
            return 0  # legitimate split entry -- not an error, not reported

        if len(set((e.value, e.recorded_on) for e in entries)) == 1:
            self._make(
                org=record.org, record=record, entry=entries[0], location=record.location,
                reason="DUPLICATE_ENTRY",
                summary=(
                    f"{record.record_id} has {len(entries)} identical entries in System B "
                    f"({entry_ids}) -- looks like a duplicate submission, not a split."
                ),
                detail={"record_id": record.record_id, "entry_ids": [e.entry_id for e in entries],
                        "value": str(entries[0].value)},
            )
            return 1

        self._make(
            org=record.org, record=record, entry=entries[0], location=record.location,
            reason="VALUE_MISMATCH",
            summary=(
                f"{record.record_id} has {len(entries)} entries in System B ({entry_ids}) "
                f"whose values neither match a single entry nor sum to the System A total "
                f"of {record.total_value}."
            ),
            detail={"record_id": record.record_id, "entry_ids": [e.entry_id for e in entries],
                    "entry_values": [str(v) for v in values], "system_a_total_value": str(record.total_value)},
        )
        return 1

    def _check_single_entry(self, record, entry):
        n = 0
        if entry.value is None:
            self._make(
                org=record.org, record=record, entry=entry, location=record.location,
                reason="MISSING_VALUE",
                summary=f"{entry.entry_id} (System B) has no value recorded for {record.record_id}.",
                detail={"record_id": record.record_id, "entry_id": entry.entry_id,
                        "raw_value": entry.raw_value, "system_a_total_value": str(record.total_value)},
            )
            n += 1
        elif abs(entry.value - record.total_value) >= CENTS:
            self._make(
                org=record.org, record=record, entry=entry, location=record.location,
                reason="VALUE_MISMATCH",
                summary=(
                    f"{record.record_id}: System A total is {record.total_value}, "
                    f"System B ({entry.entry_id}) recorded {entry.value}."
                ),
                detail={"record_id": record.record_id, "entry_id": entry.entry_id,
                        "system_a_total_value": str(record.total_value), "system_b_value": str(entry.value)},
            )
            n += 1

        if entry.location_id and entry.location_id != record.location_id:
            self._make(
                org=record.org, record=record, entry=entry, location=record.location,
                reason="LOCATION_MISMATCH",
                summary=(
                    f"{record.record_id}: System A has location {record.location_id}, "
                    f"System B ({entry.entry_id}) has {entry.location_id}."
                ),
                detail={"record_id": record.record_id, "entry_id": entry.entry_id,
                        "system_a_location_id": record.location_id, "system_b_location_id": entry.location_id,
                        "system_a_org": record.org_id, "system_b_org": entry.org_id},
            )
            n += 1

        if entry.recorded_on and entry.recorded_on != record.event_date:
            self._make(
                org=record.org, record=record, entry=entry, location=record.location,
                reason="DATE_MISMATCH",
                summary=(
                    f"{record.record_id}: System A event_date is {record.event_date}, "
                    f"System B ({entry.entry_id}) recorded_on is {entry.recorded_on}."
                ),
                detail={"record_id": record.record_id, "entry_id": entry.entry_id,
                        "system_a_event_date": str(record.event_date), "system_b_recorded_on": str(entry.recorded_on)},
            )
            n += 1
        return n

    def _check_missing_in_b(self):
        """CONFIRMED records with no Entry pointing at them at all. A
        VOIDED record with no B entry is expected, not an error -- it
        never should have made it to B -- so voided is excluded here.
        """
        n = 0
        matched_ids = set(Entry.objects.filter(record__isnull=False).values_list("record_id", flat=True))
        for record in Record.objects.exclude(record_id__in=matched_ids).filter(state="CONFIRMED"):
            self._make(
                org=record.org, record=record, entry=None, location=record.location,
                reason="MISSING_IN_B",
                summary=f"{record.record_id} is confirmed in System A but has no matching entry in System B.",
                detail={"record_id": record.record_id, "system_a_total_value": str(record.total_value)},
            )
            n += 1
        return n

    def _check_orphan_entries(self):
        """B entries whose (normalized) record_ref does not match any A
        record at all -- e.g. ENT/2026/4901 -> REC-1999, which does not
        exist in system_a.csv.
        """
        n = 0
        for entry in Entry.objects.filter(record__isnull=True).select_related("location"):
            self._make(
                org=entry.org, record=None, entry=entry, location=entry.location,
                reason="UNMATCHED_B_REFERENCE",
                summary=(
                    f"{entry.entry_id} references '{entry.raw_record_ref}', "
                    f"which does not match any record in System A."
                ),
                detail={"entry_id": entry.entry_id, "raw_record_ref": entry.raw_record_ref,
                        "value": str(entry.value) if entry.value is not None else None},
            )
            n += 1
        return n
