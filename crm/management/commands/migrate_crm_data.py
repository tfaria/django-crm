from django.core.management.base import NoArgsCommand
from django.db import transaction

from crm import models as crm
from contactinfo import models as contactinfo
from countries.models import Country

class Command(NoArgsCommand):
    help = "Migrate legacy django-crm contact info to the new django-contactinfo model"

    @transaction.commit_on_success
    def handle_noargs(self, **options):
        print """
The models necessary to run this migration are no longer available.  Please
revert to revision 11 (e.g., run `svn up -r11`) and try this command again.
"""
                