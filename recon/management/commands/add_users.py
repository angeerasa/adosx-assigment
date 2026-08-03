from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from tenancy.models import Org, UserOrgMembership

# Per the brief: "Authentication depth [is not being tested]. A
# hardcoded pair of users with an org each is fine." One user per org,
# fixed credentials, documented here rather than hidden -- there is no
# security reason to obscure a take-home fixture.
USERS = [
    ("alice", "alice-pw", "ORG-A"),
    ("bob", "bob-pw", "ORG-B"),
]


class Command(BaseCommand):
    help = "Create the two hardcoded demo users, one per org."

    def handle(self, *args, **options):
        for username, password, org_id in USERS:
            org = Org.objects.get(org_id=org_id)
            user, _ = User.objects.get_or_create(username=username)
            user.set_password(password)
            user.save()
            UserOrgMembership.objects.update_or_create(user=user, defaults={"org": org})
            self.stdout.write(f"{username} -> {org_id}")
        print(User.objects.all())
