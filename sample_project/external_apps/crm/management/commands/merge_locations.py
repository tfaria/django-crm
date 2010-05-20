from django.core.management.base import NoArgsCommand
from django.db import transaction
from django.db.models import Count

from crm import models as crm


class Command(NoArgsCommand):
    help = "Merge location data"
    
    @transaction.commit_on_success
    def handle_noargs(self, **options):
        contacts = crm.Contact.objects.annotate(
            locs=Count('locations')
        ).filter(locs__gt=1)
        for contact in contacts:
            print contact
            locations = contact.locations.order_by('id')
            primary = locations[0]
            for location in locations[1:]:
                print "Location %d" % location.id
                for address in location.addresses.all():
                    address.location = primary
                    address.save()
                for phone in location.phones.all():
                    phone.location = primary
                    phone.save()
                location.delete()
