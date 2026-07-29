from django.db import models
from django.conf import settings

# Create your models here.
class Org(models.Model):
    """A tenant. 'org_id' in the source CSVs (e.g. ORG-A) is kept as the
    primary key string rather than swapped for a surrogate integer id,
    because every other file in this project (locations.csv, and the
    reconciliation exceptions we build later) refers to orgs by this
    exact string. Keeping it as the PK avoids a join just to resolve a
    human-meaningless integer back to the id everyone actually uses.
    """

    org_id = models.CharField(max_length=32, primary_key=True)
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.org_id



class Location(models.Model):
    """Every location belongs to exactly one org. This table is the only
    place that mapping exists (per the brief) -- Record and Entry do NOT
    look up org membership themselves; they copy org_id from here at
    ingest time. See reconciliation/models.py for why it's copied rather
    than looked up via a join.
    """

    location_id = models.CharField(max_length=32, primary_key=True)
    org = models.ForeignKey(Org, on_delete=models.PROTECT, related_name="locations")
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.location_id

class UserOrgMembership(models.Model):
    """Ties a Django auth User to exactly one org. The brief explicitly
    says auth depth is not being evaluated ('a hardcoded pair of users
    with an org each is fine'), so this is deliberately the simplest
    thing that could work: one row per user, one org each, no roles,
    no multi-org support. This table is what the login view and the
    tenant middleware both read to answer "which org is this request
    allowed to see?".
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="org_membership"
    )
    org = models.ForeignKey(Org, on_delete=models.PROTECT, related_name="members")

    def __str__(self):
        return f"{self.user.username} -> {self.org_id}"
