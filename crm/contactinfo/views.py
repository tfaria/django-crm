from django.shortcuts import render_to_response
from django.template import RequestContext

from contactinfo.forms import AddressForm
from countries.models import Country
from contactinfo import models as contactinfo

def create_edit_location(request, location_id=None):
    
    us = Country.objects.get(iso='FR')
    location = contactinfo.Location(country=us)
    if request.POST:
        address_form = AddressForm(request.POST, location=location)
    else:
        address_form = AddressForm(location=location)
    return render_to_response(
        'contactinfo/create_edit_location.html',
        {'address_form': address_form,},
        context_instance=RequestContext(request)
    )