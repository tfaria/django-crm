# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# $Id: urls.py 425 2009-07-14 03:43:01Z tobias $
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

from django.conf.urls.defaults import *
from django.contrib.auth import views as auth_views

import crm.views as views

urlpatterns = patterns('',
    
    url(r'^dashboard/$', views.dashboard, name='crm_dashboard'),
    
    url(r'^search/$', views.quick_search, name='quick_search'),
    
    url(r'^interaction/$', views.list_interactions, name='list_interactions'),
    url(r'^(?:person/(?P<person_id>\d+)/)?interaction/create/$', views.create_edit_interaction, name='create_interaction'),
    url(r'^interaction/(?P<interaction_id>\d+)/edit/$', views.create_edit_interaction, name='edit_interaction'),
    url(r'^interaction/(?P<interaction_id>\d+)/remove/$', views.remove_interaction, name='remove_interaction'),
    
    url(r'^person/list/$', views.list_people, name='list_people'),
    url(r'^person/create/$', views.create_edit_person, name='create_person'),
    url(r'^person/register/$', views.register_person, name='register_person'),
    url(r'^person/(?P<person_id>\d+)/$', views.view_person, name='view_person'),
    url(r'^person/(?P<person_id>\d+)/edit/$', views.create_edit_person, name='edit_person'),
    
    url(
        r'^contact/(?P<contact_slug>[-\w]+)/email/$',
        views.email_contact,
        name='email_contact',
    ),
    
    # businesses
    url(r'^business/list/$', views.list_businesses, name='list_businesses'),
    url(
        r'^business/(?P<business_id>\d+)/$',
        views.view_business,
        name='view_business',
    ),
    url(
        r'^business/create/$',
        views.create_edit_business,
        name='create_business',
    ),
    url(
        r'^business/(?P<business_id>\d+)/edit/$',
        views.create_edit_business,
        name='edit_business',
    ),
    url(
        r'^business/(?P<business_id>\d+)/contact/(?P<user_id>\d+)/edit/$',
        views.edit_business_relationship,
        name='edit_business_relationship',
    ),
    
    # projects
    url(
        r'^business/(?P<business_id>\d+)/(?:project/(?P<project_id>\d+)/)?(?:contact/(?P<user_id>\w+)/)?(?P<action>remove|add)/$',
        views.associate_contact,
        name='associate_contact',
    ),
    
    url(r'^book/(?P<file_name>[\w.]+)$', views.address_book, name='address_book'),
    
    url(
        r'^registration/activate/(?P<activation_key>\w+)/$',
        views.activate_login,
        name='activate_login',
    ),
    url(
        r'^registration/contact/$',
        views.create_registration,
        name='create_registration',
    )
)
