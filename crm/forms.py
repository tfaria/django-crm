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
from django.contrib.auth.models import User
from django.contrib.localflavor.us import forms as us_forms
from django.db import transaction
from django.db.models import Q
from django.template.defaultfilters import slugify
from django.conf import settings
from django.core.mail import send_mail, send_mass_mail
from django.template.loader import render_to_string

from caktus.django.forms import SimpleUserForm, RequestForm, RequestModelForm
from caktus.django.widgets import CheckboxSelectMultipleWithJS
from caktus.decorators import requires_kwarg
from caktus.django import widgets as caktus_widgets
from caktus.django.db.util import slugify_uniquely

import crm.models as crm


class PersonForm(SimpleUserForm):
    def clean_email(self):
        if not self.instance.id and \
          User.objects.filter(email=self.cleaned_data['email']).count() > 0:
            raise forms.ValidationError('A user with that e-mail address already exists.')
        return self.cleaned_data['email']


class ProfileForm(forms.ModelForm):
    """
    Model form for user profiles.
    """

    class Meta:
        model = crm.Contact
        fields = ('first_name', 'last_name', 'email', 'notes', 'picture')
    
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
    def save(self):
        instance = super(ProfileForm, self).save(commit=False)
        qs = crm.Contact.objects.filter(type='individual')
        new_instance = not instance.id
        if instance.user:
            instance.user.first_name = instance.first_name
            instance.user.last_name = instance.last_name
            instance.user.email = instance.email
            instance.user.save()
        if new_instance:
            instance.description = ''
            instance.type = 'individual'
        else:
            qs = qs.exclude(pk=instance.pk)
        instance.slug = slugify_uniquely(
            '%s %s' % (instance.first_name, instance.last_name),
            qs,
        )
        instance.sort_name = slugify(
            '%s %s' % (instance.last_name, instance.first_name),
        )
        instance.save()
        self.save_m2m()
        return instance


class BusinessForm(forms.ModelForm):
    class Meta:
        model = crm.Contact
        fields = ('name', 'description', 'notes', 'business_types')

    def __init__(self, *args, **kwargs):
        super(BusinessForm, self).__init__(*args, **kwargs)

        self.fields['business_types'].label = 'Type(s)'
        self.fields['business_types'].widget = \
          caktus_widgets.CheckboxSelectMultipleWithJS(
            choices = self.fields['business_types'].choices
        )
        self.fields['business_types'].help_text = ''

    def save(self, commit=True):
        instance = super(BusinessForm, self).save(commit=False)
        qs = crm.Contact.objects.filter(type='business')
        if not instance.pk:
            instance.type = 'business'
        else:
            qs = qs.exclude(pk=instance.pk)
        instance.slug = slugify_uniquely(instance.name, qs)
        instance.sort_name = slugify(instance.name)
        if commit:
            instance.save()
        return instance


class EmailForm(forms.Form):
    to = forms.ChoiceField()
    memo = forms.CharField(max_length=4096, widget=forms.Textarea)
    
    def clean_to(self):
        try:
            return User.objects.get(pk=self.cleaned_data['to'])
        except User.DoesNotExist:
            raise forms.ValidationError(_(u'This username is already taken. Please choose another.'))
        
        return self.cleaned_data['to']
    
    def __init__(self, *args, **kwargs):
        search = None
        
        business = kwargs.pop('business', None)
        project = kwargs.pop('project', None)
        
        if project:
            # ignore business contacts if a project is set
            search = Q(projects=project)
        elif business:
            search = Q(businesses=business)
        
        forms.Form.__init__(self, *args, **kwargs)
        
        if search:
            self.fields['to'].choices = []
            for user in User.objects.filter(search):
                choice = (user.id, "%s (%s)" % (user.get_full_name(), user.email))
                self.fields['to'].choices.append(choice)


class UserModelChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name()


class InteractionForm(RequestModelForm):
    class Meta:
        model = crm.Interaction
        fields = ('date', 'type', 'completed', 'project', 'contacts', 'memo',)
    
    def __init__(self, *args, **kwargs):    
        self.url = kwargs.pop('url')
        self.person = kwargs.pop('person')
        self.crm_user = kwargs.pop('crm_user')
        super(InteractionForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = \
            ('date', 'type', 'completed', 'contacts', 'project', 'memo',)
        
        self.fields['contacts'] = UserModelChoiceField(
            widget=caktus_widgets.AjaxSelectMultiWidget(url=self.url),
            queryset=crm.Contact.objects.filter(type='individual'),
        )
        if not self.request.POST:
            if self.instance.id:
                initial_choices = \
                    self.instance.contacts.values_list('id', flat=True)
            else:
                initial_choices = [self.person.id]
                if self.crm_user:
                    initial_choices.append(self.crm_user.id)
            self.fields['contacts'].widget.initial_choices = \
                [unicode(choice) for choice in initial_choices]
        
        if not self.instance.id and self.person:
            projects = crm.Project.objects.filter(contacts=self.person)
        elif self.instance.id:
            # show only client projects
            client_contacts = self.instance.contacts.filter(
                contacts__type='business',
                contacts__business_types__name__iexact='client',
            )
            projects = crm.Project.objects.filter(
                contacts__in=client_contacts
            ).distinct()
        else:
            projects = crm.Project.objects.none()
        
        self.fields['project'].queryset = projects
        
        self.fields['date'].widget = caktus_widgets.MooDate()
        self.fields['date'].initial = datetime.datetime.now()
        
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


class ContactRelationshipForm(RequestModelForm):
    class Meta:
        model = crm.ContactRelationship
        fields = ('types',)

    def __init__(self, *args, **kwargs):
        super(ContactRelationshipForm, self).__init__(*args, **kwargs)
        self.fields['types'].widget = forms.CheckboxSelectMultiple(
            choices=self.fields['types'].choices
        )
        self.fields['types'].help_text = ''
    
    def save(self):
        instance = super(ContactRelationshipForm, self).save(commit=True)
        mirror, created = crm.ContactRelationship.objects.get_or_create(
            from_contact=instance.to_contact,
            to_contact=instance.from_contact,
        )
        mirror.types = instance.types.all()
        mirror.save()
        return instance


class ProjectForm(forms.ModelForm):
    class Meta:
        model = crm.Project
        fields = (
            'name',
            'business',
            'trac_environment',
            'point_person',
            'type',
            'status',
            'description',
        )

    @requires_kwarg('business')
    def __init__(self, *args, **kwargs):
        self.business = kwargs.pop('business')
        super(ProjectForm, self).__init__(*args, **kwargs)
        
        if self.business:
            self.fields.pop('business')
        else:
            self.fields['business'].queryset = crm.Contact.objects.filter(
                type='business',
                business_types__name='client',
            )
    
    def save(self):
        instance = super(ProjectForm, self).save(commit=False)
        if self.business:
            instance.business = self.business
        instance.save()
        return instance


class ProjectRelationshipForm(RequestModelForm):
    class Meta:
        model = crm.ProjectRelationship
        fields = ('types',)
    
    def __init__(self, *args, **kwargs):
        super(ProjectRelationshipForm, self).__init__(*args, **kwargs)
        self.fields['types'].widget = forms.CheckboxSelectMultiple(
            choices=self.fields['types'].choices
        )
        self.fields['types'].help_text = ''


class EmailContactForm(RequestForm):
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


class LoginRegistrationForm(RequestForm):
    password1 = forms.CharField(
        widget=forms.PasswordInput,
        label='Password',
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput,
        label='Password (again)',
    )
    
    def clean(self):
        if self.cleaned_data['password1'] != self.cleaned_data['password2']:
            raise forms.ValidationError('Passwords must match')
        return self.cleaned_data
