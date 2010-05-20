from django.db import transaction

from contactinfo.forms import LocationForm, AddressFormSet, PhoneFormSet
from contactinfo import models as contactinfo

ADDRESSES_PREFIX = 'location_addresses'
PHONES_PREFIX = 'location_phones'

@transaction.commit_on_success
def create_edit_location(request, location=None, save=False):
    saved = False
    if request.POST:
        location_form = LocationForm(request.POST, instance=location)
        if location_form.is_valid():
            location = location_form.save(commit=False)
            address_formset = AddressFormSet(
                request.POST, 
                instance=location, 
                prefix=ADDRESSES_PREFIX,
            )
            phone_formset = PhoneFormSet(
                request.POST, 
                instance=location, 
                prefix=PHONES_PREFIX,
            )
            if address_formset.is_valid() and phone_formset.is_valid() and save:
                location.save()
                addresses = address_formset.save(commit=False)
                for address in addresses:
                    address.location = location
                    address.save()
                phones = phone_formset.save(commit=False)
                for phone in phones:
                    phone.location = location
                    phone.save()
                saved = True
        else:
            address_formset = AddressFormSet(
                request.POST, 
                prefix=ADDRESSES_PREFIX,
                instance=location or contactinfo.Location(),
            )
            phone_formset = PhoneFormSet(
                request.POST,
                prefix=PHONES_PREFIX,
                instance=location or contactinfo.Location(),
            )
    else:
        location_form = LocationForm(instance=location)
        address_formset = AddressFormSet(
            prefix=ADDRESSES_PREFIX,
            instance=location or contactinfo.Location(),
        )
        phone_formset = PhoneFormSet(
            prefix=PHONES_PREFIX,
            instance=location or contactinfo.Location(),
        )
    context = {
        'location': location,
        'location_form': location_form,
        'address_formset': address_formset,
        'phone_formset': phone_formset,
    }
    return location, saved, context