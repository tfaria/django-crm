from django.db.models import Q
from django.core.urlresolvers import reverse

from crm import models as crm

try:
    from timepiece import models as timepiece
except ImportError:
    timepiece = None


class ContactLookup(object):

    def get_query(self,q,request):
        """ return a query set.  you also have access to request.user if needed """
        return crm.Contact.objects.filter(
            type='individual'
        ).filter(
            Q(first_name__icontains=q) | 
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        ).select_related().order_by('sort_name')[:10]
        
    def format_item(self,contact):
        """ simple display of an object when it is displayed in the list of selected objects """
        return unicode(contact)

    def format_result(self,contact):
        """ a more verbose display, used in the search results display.  may contain html and multi-lines """
        return u"<span class='%s'>%s %s</span>" % (contact.type, contact.first_name, contact.last_name)

    def get_objects(self,ids):
        """ given a list of ids, return the objects ordered as you would like them on the admin page.
            this is for displaying the currently selected items (in the case of a ManyToMany field)
        """
        return crm.Contact.objects.filter(pk__in=ids)


### not a view
def compare_by(fieldname):
    def compare_two_dicts(a, b):
        return cmp(a[fieldname], b[fieldname])
    return compare_two_dicts


class SearchResult(object):
    def __init__(self, pk, type, name):
        self.pk = "%s-%d" % (type, pk)
        self.type = type
        self.name = name


class QuickLookup(object):

    def get_query(self,q,request):
        """ return a query set (or a fake one).  you also have access to request.user if needed """
        results = []
        individuals = Q(type='individual') & (
            Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )
        businesses =  Q(type='business') & Q(name__icontains=q)
        contacts = crm.Contact.objects.filter(
            individuals | businesses | Q(email__icontains=q)
        )
        for contact in contacts:
            if contact.type == 'individual':
                name = contact.get_full_name()
            else:
                name = contact.name
            results.append(
                SearchResult(contact.pk, contact.type, name)
            )
        if timepiece:
            for project in timepiece.Project.objects.filter(
                name__icontains=q,
            ).select_related():
                results.append(
                    SearchResult(project.pk, 'project', project.name)
                )
        results.sort(lambda a,b: cmp(a.name, b.name))
        return results
        
    def format_item(self, item):
        """ simple display of an object when it is displayed in the list of selected objects """
        return item.name

    def format_result(self, item):
        """ a more verbose display, used in the search results display.  may contain html and multi-lines """
        return u"<span class='%s'>%s</span>" % (item.type, item.name)

    def get_objects(self, ids):
        """ given a list of ids, return the objects ordered as you would like them on the admin page.
            this is for displaying the currently selected items (in the case of a ManyToMany field)
        """
        results = []
        for id in ids:
            type, pk = id.split('-')
            if timepiece and type == 'project':
                results.append(timepiece.Project.objects.get(pk=pk))
            else:
                results.append(crm.Contact.objects.get(pk=pk))
        return results
