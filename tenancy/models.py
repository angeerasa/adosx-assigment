from django.db import models
from django.conf import settings

# Create your models here.
class Org(models.Model):

    org_id = models.CharField(max_length=32, primary_key=True)
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.org_id



class Location(models.Model):

    location_id = models.CharField(max_length=32, primary_key=True)
    org = models.ForeignKey(Org, on_delete=models.PROTECT, related_name="locations")
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.location_id

class UserOrgMembership(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="org_membership"
    )
    org = models.ForeignKey(Org, on_delete=models.PROTECT, related_name="members")

    def __str__(self):
        return f"{self.user.username} -> {self.org_id}"
