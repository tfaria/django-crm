import sys

from django import forms
from django.db import transaction
from django.utils.translation import ugettext_lazy as _

from django.core.urlresolvers import reverse
from django.forms import widgets
from django.forms.models import inlineformset_factory, BaseInlineFormSet
from django.utils.safestring import mark_safe

from contactinfo import models as contactinfo
from countries.models import Country


class CountrySelect(widgets.Select):
    def _javascript(self, name):
        return mark_safe("""
<script type="text/javascript">
jQuery(function ($) {
    $('select[name=%s]').change(function (e) {
        var country = $(e.target).val();
        var url = '%s';
        var location_id = $('.address_formset .field.location.existing-object input').val();
        get_data = {'country': country};
        if (location_id != undefined) {
            get_data['location_id'] = location_id;
        }
        $.get(url, get_data, function(data) {
            var saved_values = {};
            $('tbody.address_formset input,textarea,select').each(function (i, input) {
                saved_values[$(input).attr('id')] = $(input).val();
            });
            $('tbody.address_formset').html(data);
            $.each(saved_values, function (id, value) {
                $('#'+id).val(value);
            });
            $('tbody.address_formset').change();
        });
    });
    //$('select[name=%s]').change();
});
</script>""" % (name, reverse('get_address_formset_html'), name))

    def render(self, name, value, attrs=None, choices=()):
        return super(CountrySelect, self).render(
            name, value, attrs, choices,
        ) + self._javascript(name)


class LocationForm(forms.ModelForm):
    class Meta:
        model = contactinfo.Location
        fields = ('type', 'country',)

    def __init__(self, *args, **kwargs):
        super(LocationForm, self).__init__(*args, **kwargs)
        self.fields['country'].queryset = \
          Country.objects.order_by('printable_name')
        self.fields['country'].widget = \
          CountrySelect(choices=self.fields['country'].choices)
        self.fields['type'].widget = \
          forms.RadioSelect(choices=self.fields['type'].choices)
        self.fields['type'].label = _('Location Type')


LOCALFLAVOR_IMPORT_BASE = 'django.contrib.localflavor.%s.forms'
def get_localflavor_fieldclass(iso, class_name):
        # workaround for http://code.djangoproject.com/ticket/8323
        if iso.upper() == 'GB':
            iso = 'UK'
        path = LOCALFLAVOR_IMPORT_BASE % iso.lower()
        try:
            __import__(path)
        except ImportError:
            return None
        module = sys.modules[path]
        try:
            return getattr(module, iso.upper() + class_name)
        except AttributeError:
            return None


class BaseAddressFormSet(BaseInlineFormSet):  
    def _get_state_province_field(self, iso, old_field=None):
        field_names = (
            (_('State'), 'StateField', 'StateSelect'),
            (_('Province'), 'ProvinceField', 'ProvinceSelect'),
            (_('Department'), 'DepartmentField', 'DepartmentSelect'),
            (_('County'), 'CountyField', 'CountySelect'),
        )
        widget = None
        field = None
        for label, field_name, widget_name in field_names:
            Field = get_localflavor_fieldclass(iso, field_name)
            widget = get_localflavor_fieldclass(iso, widget_name)
            if field or widget:
                break
        if not Field and not widget:
            label = _('State or Province')
        if not Field:
            Field = forms.CharField
        if widget:
            field_instance = Field(label=label, widget=widget)
        else:
            field_instance = Field(label=label)
        if old_field:
            field_instance.required = old_field.required
        return field_instance
        
    def _get_postal_code_field(self, iso, old_field=None):
        field_names = (
            (_('Zip Code'), 'ZipCodeField'),
            (_('Postcode'), 'PostcodeField'),
            (_('Post Code'), 'PostCodeField'),
            (_('Postal Code'), 'PostalCodeField'),
        )
        for label, field_name in field_names:
            Field = get_localflavor_fieldclass(iso, field_name)
            if Field:
                break
        if not Field:
            Field = forms.CharField
            label = _('Postal Code')
        field_instance = Field(label=label)
        if old_field:
            field_instance.required = old_field.required
        return field_instance
        
    def add_fields(self, form, index):
        super(BaseAddressFormSet, self).add_fields(form, index)
        
        if self.instance.country and self.instance.country.iso:
            country_iso = self.instance.country.iso
            form.fields['postal_code'] = self._get_postal_code_field(
                country_iso, 
                old_field=form.fields['postal_code'],
            )
            form.fields['state_province'] = \
              self._get_state_province_field(
                country_iso, 
                old_field=form.fields['state_province'],
            )
        else:
            form.fields['postal_code'].label = _('Postal Code')
            form.fields['state_province'].label = _('State or Province')
        form.fields['city'].label = _('City or Town')
        form.fields['street'].label = _('Street')
        
        if isinstance(form.fields['state_province'].widget, forms.Select):
            empty_choice = ('', '------')
            form.fields['state_province'].widget.choices.insert(0, empty_choice)


AddressFormSet = inlineformset_factory(
    contactinfo.Location, 
    contactinfo.Address,
    formset=BaseAddressFormSet,
    extra=1,
)


class BasePhoneFormSet(BaseInlineFormSet):
    def _get_phone_field(self, iso):
        PhoneField = get_localflavor_fieldclass(iso, 'PhoneNumberField')
        
        if PhoneField:
            field = PhoneField()
        else:
            field = forms.CharField()
        field.label = _('Number')
        return field
        
    def add_fields(self, form, index):
        super(BasePhoneFormSet, self).add_fields(form, index)
        
        if self.instance.country and self.instance.country.iso:
            country_iso = self.instance.country.iso
            form.fields['number'] = self._get_phone_field(country_iso)
            
        form.fields['type'].widget = \
          forms.RadioSelect(choices=form.fields['type'].choices)
        
PhoneFormSet = inlineformset_factory(
    contactinfo.Location, 
    contactinfo.Phone,
    formset=BasePhoneFormSet,
    extra=2,
)
