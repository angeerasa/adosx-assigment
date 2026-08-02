from rest_framework import serializers

from recon.models import Discrepancy


class DiscrepancySerializer(serializers.ModelSerializer):
    class Meta:
        model = Discrepancy
        fields = ["id", "reason_code", "summary", "detail",
            "record_id", "entry_id", "location_id",]
