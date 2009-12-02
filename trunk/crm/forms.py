# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# $Id: forms.py 425 2009-07-14 03:43:01Z tobias $
# ----------------------------------------------------------------------------
#
#    Copyright (C) 2008-2009 Caktus Consulting Group, LLC
#
#    This file is part of django-crm and was originally extracted from minibooks.
#
#    django-crm is published under a BSD-style license.
#    
#    You should have received a copy of the BSD License along with django-crm.  
#    If not, see <http://www.opensource.org/licenses/bsd-license.php>.
#

import datetime

from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.localflavor.us import forms as us_forms
from django.db import transaction
from django.db.models import Q
from django.template.defaultfilters import slugify
from django.conf import settings
from django.core.mail import EmailMessage, send_mail, send_mass_mail
from django.template.loader import render_to_string
from django.template import RequestContext
from django.core.urlresolvers import reverse

from ajax_select.fields import AutoCompleteSelectMultipleField, \
                               AutoCompleteSelectField, \
                               AutoCompleteSelectWidget

from crm import models as crm
from crm.models import slugify_uniquely
from crm.widgets import DateInput

def send_user_email(request, user, email_dict):
    context = {
        'user': user,
    }
    context.update(email_dict.get('extra_context', {}))
    email = EmailMessage(subject=email_dict['subject'])
    if request:
        email.body = render_to_string(
            email_dict['template'],
            context,
            context_instance=RequestContext(request),
        )
    else:
        email.body = render_to_string(email_dict['template'], context)
    default_from = 'no-reply@example.com'
    default_from = getattr(settings, 'DEFAULT_EMAIL_FROM', default_from)
    default_from = getattr(settings, 'DEFAULT_FROM_EMAIL', default_from)
    email.from_email = email_dict.get('from', default_from)
    email.to = ["%s %s <%s>" % (user.first_name, user.last_name, user.email)]
    email.send()


class PersonForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
    
    def __init__(self, *args, **kwargs):
        super(PersonForm, self).__init__(*args, **kwargs)
        # default to required for email field.  Override this in your view if you need to.
        self.fields['email'].required = True
    
    def clean_email(self):
        if not self.instance.id and \
          User.objects.filter(email=self.cleaned_data['email']).count() > 0:
            raise forms.ValidationError('A user with that e-mail address already exists.')
        return self.cleaned_data['email']
    
    def save(self, email_dict=None, request=None):
        email_enabled = getattr(settings, 'CAKTUS_EMAIL_ENABLED', True)
        if self.instance.id:
            user = super(PersonForm, self).save()
            created = False
        else:
            try:
                user = User.objects.get(email=self.cleaned_data['email'])
                created = False
            except User.DoesNotExist:
                user = super(PersonForm, self).save(commit=False)
                created = True
                if not email_enabled:
                    user.set_password(settings.CAKTUS_DEBUG_PASSWORD)
                username_base = "%s%s" % (user.first_name, user.last_name)
                if username_base == '': username_base = user.email
                user.username = slugify_uniquely(
                    username_base[:20], 
                    queryset=User.objects.all(), 
                    field='username',
                )
                user.save()
                self.save_m2m()
        if email_dict and email_enabled:
            if 'extra_context' not in email_dict:
                email_dict['extra_context'] = {}
            email_dict['extra_context']['user_is_new'] = created
            if created:
                password = User.objects.make_random_password(length=8)
                user.set_password(password)
                user.save()
                email_dict['extra_context']['password'] = password
            send_user_email(request, user, email_dict)
        return user, created


class ProfileForm(forms.ModelForm):
    """
    Model form for user profiles.
    """

    class Meta:
        model = crm.Contact
        fields = ('first_name', 'last_name', 'email', 'notes', 'picture')
    
    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request')
        super(ProfileForm, self).__init__(*args, **kwargs)
        if not request.user.has_perm('crm.change_contact'):
            self.fields.pop('notes')
    
    def clean_email(self):
        if self.cleaned_data['email'] != '':
            emails = crm.Contact.objects.filter(
                email=self.cleaned_data['email']
            )
            if self.instance.pk:
                emails = emails.exclude(pk=self.instance.pk)
            if emails.count() > 0:
                raise forms.ValidationError('A user with that e-mail address already exists.')
        return self.cleaned_data['email']
    
    @transaction.commit_on_success
    def save(self, commit=True):
        instance = super(ProfileForm, self).save(commit=False)
        qs = crm.Contact.objects.all()
        if instance.pk:
            qs = qs.exclude(pk=instance.pk)
        instance.slug = slugify_uniquely(instance.get_full_name(), qs)
        if instance.user:
            instance.user.first_name = instance.first_name
            instance.user.last_name = instance.last_name
            instance.user.email = instance.email
            instance.user.save()
        if instance.description is None:
            instance.description = ''
        instance.type = 'individual'
        sort_name = "%s %s" % (instance.last_name, instance.first_name)
        instance.sort_name = slugify(sort_name)
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class BusinessForm(forms.ModelForm):
    class Meta:
        model = crm.Contact
        fields = ('name', 'description', 'notes', 'business_types')

    def __init__(self, *args, **kwargs):
        super(BusinessForm, self).__init__(*args, **kwargs)

        self.fields['business_types'].choices = \
            list(self.fields['business_types'].choices)
        if len(self.fields['business_types'].choices) == 0:
            self.fields.pop('business_types')
        else:
            self.fields['business_types'].label = 'Type(s)'
            self.fields['business_types'].widget = \
              forms.CheckboxSelectMultiple(
                choices = self.fields['business_types'].choices
            )
            self.fields['business_types'].help_text = ''

    def save(self, commit=True):
        instance = super(BusinessForm, self).save(commit=False)
        qs = crm.Contact.objects.all()
        if instance.pk:
            qs = qs.exclude(pk=instance.pk)
        instance.slug = slugify_uniquely(instance.name, qs)
        instance.sort_name = slugify(instance.name)
        instance.type = 'business'
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class AssociateContactForm(forms.Form):
    contact = AutoCompleteSelectField('contact')
    
    def save(self):
        return self.cleaned_data['contact']


class CharAutoCompleteSelectWidget(AutoCompleteSelectWidget):
    def value_from_datadict(self, data, files, name):
        return data.get(name, None)


class QuickSearchForm(forms.Form):
    quick_search = AutoCompleteSelectField(
        'quick_search',
        widget=CharAutoCompleteSelectWidget('quick_search'),
    )
    
    def clean_quick_search(self):
        item = self.cleaned_data['quick_search']
        try:
            from timepiece import models as timepiece
        except ImportError:
            timepiece = None
        if timepiece and isinstance(item, timepiece.Project):
            return reverse('view_project', kwargs={
                'business_id': item.business.id,
                'project_id': item.id,
            })
        elif isinstance(item, crm.Contact) and item.type == 'individual':
            return reverse('view_person', kwargs={
                'person_id': item.id,
            })
        elif isinstance(item, crm.Contact) and item.type == 'business':
            return reverse('view_business', kwargs={
                'business_id': item.id,
            })
        raise forms.ValidationError('Must be a Contact or Project')
    
    def save(self):
        return self.cleaned_data['quick_search']


class UserModelChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name()


class InteractionForm(forms.ModelForm):
    class Meta:
        model = crm.Interaction
        fields = ('date', 'type', 'completed', 'contacts', 'memo',)
    
    def __init__(self, *args, **kwargs):    
        self.person = kwargs.pop('person')
        self.crm_user = kwargs.pop('crm_user')
        super(InteractionForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = \
            ('date', 'type', 'completed', 'contacts', 'memo',)
        
        self.fields['contacts'] = AutoCompleteSelectMultipleField('contact')
        
        if not self.is_bound:
            if self.instance.id:
                initial_choices = \
                    self.instance.contacts.values_list('id', flat=True)
            else:
                initial_choices = [self.person.id]
                if self.crm_user:
                    initial_choices.append(self.crm_user.id)
            self.fields['contacts'].widget.initial_choices = \
                [unicode(choice) for choice in initial_choices]
        
        # if not self.instance.id and self.person:
        #     projects = crm.Project.objects.filter(contacts=self.person)
        # elif self.instance.id:
        #     # show only client projects
        #     client_contacts = self.instance.contacts.filter(
        #         contacts__type='business',
        #         contacts__business_types__name__iexact='client',
        #     )
        #     projects = crm.Project.objects.filter(
        #         contacts__in=client_contacts
        #     ).distinct()
        # else:
        #     projects = crm.Project.objects.none()
        # 
        # self.fields['project'].queryset = projects
        
        self.fields['date'].widget = DateInput(date_format='%m/%d/%Y')
        self.fields['date'].input_formats = ('%m/%d/%Y',)
        self.fields['date'].initial = \
            datetime.datetime.now().strftime('%m/%d/%Y')
        
    def save(self):
        created = not self.instance.id
        instance = super(InteractionForm, self).save()
        if created:
            if self.person:
                instance.contacts.add(self.person)
            if self.crm_user:
                instance.contacts.add(self.crm_user)
        return instance


class SearchForm(forms.Form):
    search = forms.CharField(required=False)


class ContactRelationshipForm(forms.ModelForm):
    class Meta:
        model = crm.ContactRelationship
        fields = ('types',)

    def __init__(self, *args, **kwargs):
        super(ContactRelationshipForm, self).__init__(*args, **kwargs)
        self.fields['types'].widget = forms.CheckboxSelectMultiple(
            choices=self.fields['types'].choices
        )
        self.fields['types'].help_text = ''


class EmailContactForm(forms.Form):
    name = forms.CharField()
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea)
    
    def __init__(self, *args, **kwargs):
        self.recipients = kwargs.pop('recipients') 
        super(EmailContactForm, self).__init__(*args, **kwargs)
    
    def save(self):
        name = self.cleaned_data['name']
        email = self.cleaned_data['email']
        message = self.cleaned_data['message']
        subject = 'IAS Individual Contact Form'
        messages = []
        messages.append((
            subject,
            render_to_string(
                'crm/contact/contact_form.txt',
                self.cleaned_data,
            ),
            settings.DEFAULT_FROM_EMAIL,
            self.recipients,
        ))
        messages.append((
            subject,
            render_to_string(
                'crm/contact/contact_form_confirmation.txt',
                self.cleaned_data,
            ),
            settings.DEFAULT_FROM_EMAIL,
            [email],
        ))
        send_mass_mail(messages, fail_silently=True)


class LoginRegistrationForm(forms.Form):
    password1 = forms.CharField(
        widget=forms.PasswordInput,
        label='New Password',
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput,
        label='New Password (again)',
    )
    
    def clean(self):
        if self.cleaned_data['password1'] != self.cleaned_data['password2']:
            raise forms.ValidationError('Passwords must match')
        return self.cleaned_data


class RegistrationGroupForm(forms.Form):
    groups = forms.ModelMultipleChoiceField(
        Group.objects.all(),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
    )
