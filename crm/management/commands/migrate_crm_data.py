from django.core.management.base import NoArgsCommand
from django.db import transaction

from crm import models as crm
from django.contrib.auth.models import User

class Command(NoArgsCommand):
    help = "Migrate legacy django-crm contact info to the new django-contactinfo model"

    @transaction.commit_on_success
    def handle_noargs(self, **options):
        for profile in crm.Profile.objects.all():
            contact = crm.Contact.objects.create(
                first_name=profile.user.first_name,
                last_name=profile.user.last_name,
                email=profile.user.email,
                user=profile.user,
                type='individual',
                sort_name=profile.user.last_name+profile.user.first_name,
                notes=profile.notes,
                picture=profile.picture,
            )
            for location in profile.locations.all():
                contact.locations.add(location)
        for business in crm.Business.objects.all():
            contact = crm.Contact.objects.create(
                name=business.name,
                type='business',
                description=business.description,
                notes=business.notes,
                sort_name=business.name,
                business_id=business.id,
                picture=business.logo,
            )
            for location in business.locations.all():
                contact.locations.add(location)
            for user in business.related_people.all():
                contact_a = crm.Contact.objects.get(user=user)
                crm.ContactRelationship.objects.create(
                    from_contact=contact,
                    to_contact=contact_a,
                )
                crm.ContactRelationship.objects.create(
                    from_contact=contact_a,
                    to_contact=contact,
                )
            for business_type in business.business_types.all():
                contact.business_types.add(business_type)
