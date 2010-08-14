# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# $Id: models.py 425 2009-07-14 03:43:01Z tobias $
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

from django.db import models
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.contrib.localflavor.us import models as us_models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import curry
from django.template.loader import render_to_string
from django.template.defaultfilters import slugify
from django.core.mail import send_mail

from crm import managers as crm_managers

from contactinfo import models as contactinfo

DEFAULT_ACCOUNT_ACTIVATION_DAYS = 15

CONTACT_TYPES = (
    ('individual', 'Individual'),
    ('business', 'Business'),
)

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


class Contact(models.Model):
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        unique=True,
        related_name='contacts',
    )
    business_types = models.ManyToManyField(
        'BusinessType',
        related_name='businesses',
        blank=True,
    )
    
    # related_names ending in '+' will be ignored/hidden by Django
    contacts = models.ManyToManyField(
        'self',
        through='ContactRelationship',
        symmetrical=False,
        related_name='related_contacts+',
    )
    locations = models.ManyToManyField(contactinfo.Location, blank=True)
    
    type = models.CharField(max_length=32, choices=CONTACT_TYPES)
    name = models.CharField(max_length=255, blank=True)
    first_name = models.CharField(max_length=50, blank=True)
    middle_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    sort_name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    email = models.EmailField(blank=True)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    picture = models.ImageField(null=True, blank=True, max_length=1048576, upload_to="picture/profile/")
    external_id = models.CharField(max_length=32, blank=True)
    
    objects = models.Manager()
    
    def get_full_name(self):
        return "%s %s" % (self.first_name, self.last_name)
    
    def add_accessor_methods(self, *args, **kwargs):
        for contact_type, name in CONTACT_TYPES:
            setattr(
                self,
                '%s_relations' % contact_type,
                curry(self._get_TYPE_relations, contact_type=contact_type)
            )
    
    def is_editable_by(self, user):
        has_membership = False
        try:
            from members.models import Membership
            has_membership = (
                Membership.objects.filter(contact=self).count() > 0
                and self.user == user
            )
        except ImportError:
            pass
        has_perms = user.has_perms((
            'crm.add_contact',
            'crm.change_contact',
        ))
        return (has_membership or has_perms)
    
    def _get_TYPE_relations(self, contact_type):
        return self.contacts.filter(type=contact_type)
    
    def __init__(self, *args, **kwargs):
        super(Contact, self).__init__(*args, **kwargs)
        self.add_accessor_methods()
    
    def _get_exchange_types(self):
        # import here to avoid circular import
        try:
            from minibooks.ledger.models import ExchangeType
            return ExchangeType.objects.filter(
                business_types__businesses=self
            )
        except ImportError:
            return []
    exchange_types = property(_get_exchange_types)
    
    def primary_phone(self):
        for type in ('office', 'mobile', 'home'):
            for location in self.user.locations.all():
                for phone in location.phones.all():
                    if phone.type == type:
                        return phone
        
        return None
    
    def as_text_block(self):
        fields = []
        if self.type == 'individual':
            fields = [
                'First Name: %s\n' % self.first_name,
                'Middle Name: %s\n' % self.middle_name,
                'Last Name: %s\n' % self.last_name,
                'Email: %s\n' % self.email,
            ]
            for location in self.locations.order_by('id'):
                for phone in location.phones.order_by('id'):
                    fields.append('%s Phone: %s\n' % (location.type, phone))
                for address in location.addresses.order_by('id'):
                    fields.append('%s Address: %s\n' % (
                        location.type,
                        unicode(address).replace("\n", " ")
                    ))
        return fields
    
    class Meta:
        permissions = (
            ("access_xmlrpc", "Can access minibooks XML-RPC service"),
            ("view_profile", "Can view contacts"),
            ("view_business", "Can view businesses"),
        )
    
    def __unicode__(self):
        if self.name:
            name = self.name
        else:
            name = "%s %s" % (self.first_name, self.last_name)
        return name


class ContactRelationship(models.Model):
    types = models.ManyToManyField(
        'RelationshipType',
        related_name='contact_relationships',
        blank=True,
    )
    from_contact = models.ForeignKey('Contact', related_name='from_contacts')
    to_contact = models.ForeignKey('Contact', related_name='to_contacts')

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    class Meta:
        unique_together = ('from_contact', 'to_contact')
        
    def save(self, *args, **kwargs):
        create_mirror = kwargs.pop('create_mirror', True)
        super(ContactRelationship, self).save(*args, **kwargs)
        if create_mirror:
            mirror, created = ContactRelationship.objects.get_or_create(
                from_contact=self.to_contact,
                to_contact=self.from_contact,
            )
            mirror.types = self.types.all()
            mirror.start_date = self.start_date
            mirror.end_date = self.end_date
            mirror.save(create_mirror=False)

    def __unicode__(self):
        return "%s's relationship to %s" % (
            self.from_contact,
            self.to_contact,
        )


class BusinessType(models.Model):
    name = models.CharField(max_length=255)
    can_view_all_projects = models.BooleanField(
        default=False,
        help_text='Allow billable expenses to projects not associated with a business of this type.  For example, a billable expense for staying at a hotel, but will be billed to a client project.  When creating an exchange, this value specifies whether or not all projects show up under the Project drop down menu.'
    )
    
    def __unicode__(self):
        return self.name


class RelationshipType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.CharField(max_length=255, unique=True, editable=False)
    
    def save(self):
        queryset = RelationshipType.objects.all()
        if self.id:
            queryset = queryset.exclude(id__exact=self.id)
        self.slug = slugify_uniquely(self.name, queryset, 'slug')
        super(RelationshipType, self).save()
    
    def __unicode__(self):
        return self.name


class Interaction(models.Model):
    """ Communication log """
    
    INTERACTION_TYPES = (
        ('email', 'Email'),
        ('meeting', 'Meeting'),
        ('phone', 'Phone'),
        ('business', 'Business'),
        ('exchange', 'Exchange'),
    )

    date = models.DateTimeField()
    type = models.CharField(max_length=15, choices=INTERACTION_TYPES)
    completed = models.BooleanField(default=False)
    memo = models.TextField(blank=True)
    cdr_id = models.TextField(null=True)
    
    contacts = models.ManyToManyField(Contact, related_name='interactions')
    
    def src(self):
        if self.cdr:
            return self.cdr.src
    src.short_description = 'Source'

    def dst(self):
        if self.cdr:
            return self.cdr.dst
    dst.short_description = 'Destination'

    def duration(self):
        if self.cdr:
            time = self.cdr.duration / 60.0
            return "%.2f minutes" % time
    duration.short_description = 'Duration'
    
    class Meta:
        ordering = ['-date']
        permissions = (
            ('view_interaction', 'Can view interaction'),
            ('view_todo_list', 'Can view to do list'),
        )
    
    def __unicode__(self):
        return "%s: %s" % ( self.date.strftime("%m/%d/%y"), self.type )


class LoginRegistration(models.Model):
    contact = models.ForeignKey(Contact)
    date = models.DateTimeField()
    activation_key = models.CharField(max_length=40)
    activated = models.BooleanField(default=False)
    groups = models.ManyToManyField(Group, blank=True)
    
    objects = crm_managers.RegistrationManager()
    
    def activate(self, password):
        username = slugify_uniquely(
            self.contact.get_full_name(),
            User.objects.all(),
            'username',
        )
        user = User.objects.create_user(
            username,
            self.contact.email,
            password,
        )
        user.first_name = self.contact.first_name
        user.last_name = self.contact.last_name
        user.is_active = True
        user.save()
        self.contact.user = user
        self.contact.save()
        self.activated = True
        self.save()
        return self.contact.user
    
    def prepare_email(self, send=True):
        expiration = getattr(
            settings, 
            'ACCOUNT_ACTIVATION_DAYS', 
            DEFAULT_ACCOUNT_ACTIVATION_DAYS,
        )
        current_site = Site.objects.get_current()
        subject = render_to_string(
            'crm/login_registration/registration_email_subject.txt', {
                'site': current_site,
            }
        )
        subject = ''.join(subject.splitlines())
        message = render_to_string(
            'crm/login_registration/registration_email.txt', {
                'activation_key': self.activation_key,
                'expiration_days': expiration,
                'site': current_site,
                'contact': self.contact,
            },
        )
        if send:
            return send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [self.contact.email],
                fail_silently=True,
            )
        else:
            return (
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [self.contact.email],
            )
    
    def has_expired(self):
        expiration = getattr(
            settings, 
            'ACCOUNT_ACTIVATION_DAYS', 
            DEFAULT_ACCOUNT_ACTIVATION_DAYS,
        )
        expiration_date = datetime.timedelta(
            days=expiration,
        )
        return (self.date + expiration_date) <= datetime.datetime.now()
    
    def __unicode__(self):
        return "Registration for %s" % self.contact


def install():
    group, created = Group.objects.get_or_create(name='CRM Admin')
    if created:
        perms = Permission.objects.filter(
            content_type__in=ContentType.objects.filter(
                models.Q(app_label='crm') | models.Q(app_label='auth')
            ),
        )
        for perm in perms:
            group.permissions.add(perm)
    
    group, created = Group.objects.get_or_create(name='Pagelet Admin')
    if created:
        for perm in Permission.objects.filter(codename__icontains='pagelet'):
            group.permissions.add(perm)
