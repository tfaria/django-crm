from django.core.management.base import NoArgsCommand
from django.db import transaction
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify

from crm import models as crm
from crm.models import slugify_uniquely

class Command(NoArgsCommand):
    help = "Regenerate contact slugs in django-crm"
    
    @transaction.commit_on_success
    def handle_noargs(self, **options):
        for contact in crm.Contact.objects.all():
            if contact.type == 'business':
                contact.slug = slugify_uniquely(
                    contact.name,
                    crm.Contact.objects.exclude(pk=contact.pk),
                )
                contact.sort_name = slugify(contact.name)
            elif contact.type == 'individual':
                name = '%s %s' % (contact.first_name, contact.last_name)
                contact.slug = slugify_uniquely(
                    name,
                    crm.Contact.objects.exclude(pk=contact.pk),
                )
                contact.sort_name = slugify(
                    '%s %s' % (contact.last_name, contact.first_name),
                )
            contact.save()
