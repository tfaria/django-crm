from django.shortcuts import render_to_response
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import permission_required

from contactinfo.forms import AddressFormSet
from countries.models import Country
from contactinfo import models as contactinfo
from contactinfo import helpers

@permission_required('contactinfo.change_location')
def create_edit_location(request, location_id=None):
    """ 
    This is an example of how to use the create_edit_location helper in your
    own view.  Substitute your own template and action to perform once
    the object is saved.
    """
    if location_id:
        location = get_object_or_404(contactinfo.Location, pk=location_id)
    else:
        location = None
    location, saved, context = helpers.create_edit_location(
        request, 
        location, 
        True,
    )
    if saved:
        if 'next' in request.GET:
            return HttpResponseRedirect(request.GET['next'])
        else:
            edit_url = reverse('edit_location', args=(location.id,))
            return HttpResponseRedirect(edit_url)
    else:
        return render_to_response(
            'contactinfo/create_edit_location.html',
            context,
            context_instance=RequestContext(request)
        )


@permission_required('contactinfo.change_location')
def get_address_formset_html(request):
    default_iso = getattr(settings, 'DEFAULT_COUNTRY_ISO', 'US')
    country_iso = request.GET.get('country', default_iso)
    country = get_object_or_404(Country, iso=country_iso.upper())
    if 'location_id' in request.GET:
        location_id = request.GET['location_id']
        location = get_object_or_404(contactinfo.Location, pk=location_id)
    else:
        location = contactinfo.Location()
    location.country = country
    address_formset = AddressFormSet(
        instance=location, 
        prefix=helpers.ADDRESSES_PREFIX,
    )
    return render_to_response(
        'contactinfo/_address_formset.html',
        {'address_formset': address_formset},
        context_instance=RequestContext(request)
    )
    
    