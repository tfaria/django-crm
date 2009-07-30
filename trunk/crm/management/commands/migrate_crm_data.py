from django.core.management.base import NoArgsCommand
from django.db import transaction

from crm import models as crm
from contactinfo import models as contactinfo
from countries.models import Country

class Command(NoArgsCommand):
    help = "Migrate legacy django-crm contact info to the new django-contactinfo model"

    @transaction.commit_on_success
    def handle_noargs(self, **options):
        office = contactinfo.LocationType.objects.get(slug='office')
        mobile = contactinfo.LocationType.objects.get(slug='mobile')
        home = contactinfo.LocationType.objects.get(slug='home')
        US = Country.objects.get(iso='US')
        
        for business in crm.Business.objects.all():
            if business.address:
                location = business.locations.create(type=office, country=US)
                location.addresses.create(
                    street=business.address.street,
                    city=business.address.city,
                    state_province=business.address.state,
                    postal_code=business.address.zip,
                )
        
        for profile in crm.Profile.objects.all():
            qs = profile.phones.filter(type__in=('fax', 'office'))
            if qs.count() > 0:
                location = profile.locations.create(type=office, country=US)
                for phone in qs:
                    location.phones.create(type=phone.type, number=phone.number)
            qs = profile.phones.filter(type='mobile')
            if qs.count() > 0:
                location = profile.locations.create(type=mobile, country=US)
                for phone in qs:
                    location.phones.create(type=phone.type, number=phone.number)
            qs = profile.phones.filter(type='home')
            if qs.count() > 0:
                location = profile.locations.create(type=home, country=US)
                for phone in qs:
                    location.phones.create(type=phone.type, number=phone.number)
                