from django.core.management.base import NoArgsCommand
from django.db import transaction
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify

from crm import models as crm


def slugify_uniquely(s, queryset=None, field='slug'):
    """
    Returns a slug based on 's' that is unique for all instances of the given
    field in the given queryset.
    
    If no string is given or the given string contains no slugify-able
    characters, default to the given field name + N where N is the number of
    default slugs already in the database.
    """
    new_slug = new_slug_base = slugify(s)
    if queryset:
        queryset = queryset.filter(**{'%s__startswith' % field: new_slug_base})
        similar_slugs = [value[0] for value in queryset.values_list(field)]
        i = 1
        while new_slug in similar_slugs:
            new_slug = "%s%d" % (new_slug_base, i)
            i += 1
    return new_slug


class Command(NoArgsCommand):
    help = "Migrate legacy django-crm contact"
    
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
