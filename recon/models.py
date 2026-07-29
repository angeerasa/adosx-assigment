from django.db import models
from tenancy.models import Location, Org

# Create your models here.


class Record(models.Model):

    record_id = models.CharField(max_length=32, primary_key=True)
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="records")
    org = models.ForeignKey(Org, on_delete=models.PROTECT, related_name="records")
    event_date = models.DateField()
    category_code = models.CharField(max_length=16)
    actor_id = models.CharField(max_length=32, blank=True)
    base_value = models.DecimalField(max_digits=14, decimal_places=2)
    adjustment = models.DecimalField(max_digits=14, decimal_places=2)
    total_value = models.DecimalField(max_digits=14, decimal_places=2)
    state = models.CharField(max_length=16)  # CONFIRMED / VOIDED

    def __str__(self):
        return self.record_id


class Entry(models.Model):

    entry_id = models.CharField(max_length=32, primary_key=True)

    raw_record_ref = models.CharField(max_length=64)
    record = models.ForeignKey(
        Record, null=True, blank=True, on_delete=models.SET_NULL, related_name="entries"
    )
    location = models.ForeignKey(
        Location, null=True, blank=True, on_delete=models.PROTECT, related_name="entries"
    )
    
    org = models.ForeignKey(Org, null=True, blank=True, on_delete=models.PROTECT, related_name="entries")
    recorded_on = models.DateField(null=True, blank=True)
    
    value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    raw_value = models.CharField(max_length=32, blank=True)
    label = models.CharField(max_length=128, blank=True)

    def __str__(self):
        return self.entry_id


class Discrepancy(models.Model):
    REASON_CHOICES = [
        ("MISSING_IN_B", "Confirmed in System A, no entry in System B"),
        ("UNMATCHED_B_REFERENCE", "System B entry references a record System A does not have"),
        ("DUPLICATE_ENTRY", "Same entry duplicated in System B"),
        ("VALUE_MISMATCH", "Recorded value disagrees between the two systems"),
        ("MISSING_VALUE", "System B entry has no value recorded"),
        ("LOCATION_MISMATCH", "The two systems disagree on which location this belongs to"),
        ("DATE_MISMATCH", "The two systems disagree on the date"),
        ("VOIDED_BUT_PRESENT", "System A voided this record but System B still carries it as live"),
    ]

    class Meta:
        db_table = "recon_exception"

    org = models.ForeignKey(Org, on_delete=models.PROTECT, related_name="exceptions")
    record = models.ForeignKey(Record, null=True, blank=True, on_delete=models.CASCADE, related_name="exceptions")
    entry = models.ForeignKey(Entry, null=True, blank=True, on_delete=models.CASCADE, related_name="exceptions")
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.PROTECT, related_name="exceptions")
    reason_code = models.CharField(max_length=32, choices=REASON_CHOICES)

    summary = models.TextField()
    detail = models.JSONField(default=dict)
    # created_at = models.DateTimeField(auto_now_add=True) #Angeerasa: not-necessary

    def __str__(self):
        return f"{self.reason_code}:{self.record_id or self.entry_id}"