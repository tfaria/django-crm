import datetime

from django import forms


class DateInput(forms.TextInput):
    def __init__(self, *args, **kwargs):
        self.date_format = kwargs.pop('date_format', '%m/%d/%Y')
        super(DateInput, self).__init__(*args, **kwargs)
    
    
    def render(self, name, value, attrs=None):
        attrs['class'] = 'crm-date-field'
        if isinstance(value, datetime.date) or \
          isinstance(value, datetime.datetime):
            value = value.strftime(self.date_format)
        return super(DateInput, self).render(name, value, attrs)
