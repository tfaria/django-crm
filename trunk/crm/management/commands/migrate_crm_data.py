from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):
    help = "Migrate legacy django-crm contacts"
    
    def handle_noargs(self, **options):
        raise Exception('The models necessary to run this command are no longer available.  Please see http://code.google.com/p/django-crm/wiki/Upgrading')
