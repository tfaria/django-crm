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

from django.db import models
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.contrib.localflavor.us import models as us_models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from caktus.django.db.util import slugify_uniquely

from contactinfo import models as contactinfo


class Profile(models.Model):
    user = models.ForeignKey(User, unique=True)
    notes = models.TextField(null=True, blank=True)
    picture = models.ImageField(null=True, blank=True, max_length=1048576, upload_to="picture/profile/")
    
    locations = models.ManyToManyField(contactinfo.Location)
    
    def primary_phone(self):
        for type in ('office', 'mobile', 'home'):
            for location in self.user.locations.all():
                for phone in location.phones.all():
                    if phone.type == type:
                        return phone
        
        return None
    
    class Admin:
        ordering = ('user__last_name', 'user__first_name',)
        list_display = ['user', 'notes']
    
    class Meta:
        permissions = (
            ('view_profile', 'Can view profile'),
            ('access_xmlrpc', 'Can access XML-RPC service')
        )
    
    def __unicode__(self):
        return self.user.get_full_name()


class BusinessType(models.Model):
    name = models.CharField(max_length=255)
    can_view_all_projects = models.BooleanField(
        default=False,
        help_text='Allow billable expenses to projects not associated with a business of this type.  For example, a billable expense for staying at a hotel, but will be billed to a client project.  When creating an exchange, this value specifies whether or not all projects show up under the Project drop down menu.'
    )
    
    def __unicode__(self):
        return self.name


class BusinessManager(models.Manager):
    def __init__(self, business_type):
        super(BusinessManager, self).__init__()
        self.business_type = business_type
        
    def get_query_set(self):
        return super(BusinessManager, self).get_query_set().filter(
            business_types__name__iexact=self.business_type
        )


class Business(models.Model):
    name = models.CharField(max_length=255)
    logo = models.ImageField(
        null=True,
        blank=True,
        max_length=1048576,
        upload_to='picture/logo/',
    )
    
    description = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    business_types = models.ManyToManyField(
        BusinessType,
        blank=True,
        related_name='businesses',
    )
    locations = models.ManyToManyField(
        contactinfo.Location, 
        related_name='businesses',
    )
    contacts = models.ManyToManyField(
        User,
        blank=True,
        related_name='businesses',
    )
    related_businesses = models.ManyToManyField(
        'self',
        blank=True,
    )
    objects = models.Manager()
    clients = BusinessManager('client')
    vendors = BusinessManager('vendor')
    creditors = BusinessManager('creditor')
    members = BusinessManager('member')
    
    def _get_exchange_types(self):
        # import here to avoid circular import
        try:
            from ledger.models import ExchangeType
            return ExchangeType.objects.filter(
                business_types__businesses=self
            )
        except ImportError:
            return []
    exchange_types = property(_get_exchange_types)
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = _('businesses')
        verbose_name = _('business')
        ordering = ('name',)
        permissions = (
            ('view_business', 'Can view business'),
        )


class Project(models.Model):
    PROJECT_STATUSES = (
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        ('finished', 'Finished'),
    )
    
    PROJECT_TYPES = (
        ('consultation', 'Consultation'),
        ('software', 'Software Project'),
    )
    
    name = models.CharField(max_length = 255)
    trac_environment = models.CharField(max_length = 255, blank=True, null=True)
    business = models.ForeignKey(Business, related_name='projects')
    point_person = models.ForeignKey(User, limit_choices_to= {'is_staff':True})
    contacts = models.ManyToManyField(
        User,
        related_name='projects',
        through='ProjectRelationship',
    )
    
    type = models.CharField(max_length=15, choices=PROJECT_TYPES)
    status = models.CharField(max_length=15, choices=PROJECT_STATUSES)
    description = models.TextField()
    
    class Meta:
        ordering = ('name', 'status', 'type',)
        permissions = (
            ('view_project', 'Can view project'),
            ('email_project_report', 'Can email project report'),
        )
    
    def __unicode__(self):
        return self.name
    
    def trac_url(self):
        return settings.TRAC_URL % self.trac_environment


class ProjectRelationship(models.Model):
    types = models.ManyToManyField(
        'ProjectRelationshipType',
        related_name='project_relationships',
        blank=True,
    )
    user = models.ForeignKey(User)
    project = models.ForeignKey(Project)
    
    class Meta:
        unique_together = ('user', 'project',)
    
    def __unicode__(self):
        return "%s's relationship to %s" % (
            self.project.name,
            self.user.get_full_name(),
        )


class ProjectRelationshipType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.CharField(max_length=255, unique=True, editable=False)
    
    def save(self):
        queryset = ProjectRelationshipType.objects.all()
        if self.id:
            queryset = queryset.exclude(id__exact=self.id)
        self.slug = slugify_uniquely(self.name, queryset, 'slug')
        super(ProjectRelationshipType, self).save()
    
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
    project = models.ForeignKey(Project, null=True, blank=True)
    memo = models.TextField(null=True)
    cdr_id = models.TextField(null=True)
    
    contacts = models.ManyToManyField(User, related_name='interactions')
    
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
