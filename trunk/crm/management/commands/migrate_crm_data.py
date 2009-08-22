from django.core.management.base import NoArgsCommand
from django.db import transaction
from django.contrib.auth.models import User

from crm import models as crm


class Command(NoArgsCommand):
    help = "Migrate legacy django-crm contact"

    @transaction.commit_on_success
    def handle_noargs(self, **options):
        print """
        The models necessary to run this migration are no longer available.  Please
        revert to revision 18 (e.g., run `svn up -r18`) and try this command again.
        """
