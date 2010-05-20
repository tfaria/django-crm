# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# $Id: tests.py 429 2009-07-14 03:48:49Z tobias $
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

import cStringIO
import xmlrpclib
import unittest
import string
import random
from xml.parsers.expat import ExpatError

from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Permission, Group
from django.test import Client, TestCase
from django.contrib.contenttypes.models import ContentType
from django.template.defaultfilters import slugify
from django.template import RequestContext
from django import forms
from django.core import mail

from crm import models as crm
from contactinfo import models as contactinfo


class CrmDataTestCase(TestCase):
    def random_string(self, length=255, extra_chars=''):
        chars = string.letters + extra_chars
        return ''.join([random.choice(chars) for i in range(length)])
    
    def find_forms(self, o, depth=0, max_depth=5):
        """
        Recursively search through a context for all the forms in that context,
        up to max_depth and return a distinct set of those forms.
        """
        # use a set to avoid duplicate results
        result = set()
        if depth > max_depth:
            return result
        if isinstance(o, (list, tuple, set, RequestContext)):
            for item in o:
                result.update(self.find_forms(item, depth=depth+1))
        elif isinstance(o, dict):
            for k, v in o.iteritems():
                result.update(self.find_forms(v, depth=depth+1))
        elif isinstance(o, forms.Form):
            result.add(o)
        return result
    
    def assertNoFormErrors(self, response):
        """
        Make sure no form errors appear in the response.
        """
        forms = self.find_forms(response.context)
        errors = [form.errors for form in forms if form.errors]
        self.assertEqual(len(errors), 0, 'Form errors: %s' % errors)
    
    def assertFormErrors(self, response):
        """
        Make sure one or more form errors appear in the response.
        """
        forms = self.find_forms(response.context)
        errors = [form.errors for form in forms if form.errors]
        self.assertTrue(len(errors) > 0)

    def create_relationship(self, data={}):
        defaults = {}
        defaults.update(data)
        return crm.ContactRelationship.objects.create(**defaults)
        
    def create_person(self, data={}):
        first_name = self.random_string(20)
        last_name = self.random_string(20)
        defaults = {
            'type': 'individual',
            'first_name': first_name,
            'last_name': last_name,
            'sort_name': '-'.join([last_name, first_name]),
            'slug': slugify(' '.join([first_name, last_name])),
        }
        defaults.update(data)
        return crm.Contact.objects.create(**defaults)
    
    def create_business(self, data={}):
        name = self.random_string(30, extra_chars=' ')
        defaults = {
            'type': 'business',
            'name': name,
            'sort_name': name,
            'slug': slugify(name),
        }
        defaults.update(data)
        return crm.Contact.objects.create(**defaults)


class TestTransport(xmlrpclib.Transport):
    """ Handles connections to XML-RPC server through Django test client."""
    
    def __init__(self, *args, **kwargs):
        self._use_datetime = True
        self.client = Client()
        self.client.login(
            username=kwargs.pop('username'),
            password=kwargs.pop('password'),
        )
    
    def request(self, host, handler, request_body, verbose=0):
        self.verbose = verbose
        response = self.client.post(
            handler,
            request_body,
            content_type='text/xml',
            follow=True,
        )
        res = cStringIO.StringIO(response.content)
        res.seek(0)
        return self.parse_response(res)


class XMLRPCTestCase(TestCase):
    def setUp(self):
        super(XMLRPCTestCase, self).setUp()
        self.admin = User.objects.create_user(
            'admin',
            'test@test.com',
            'abc123',
        )
        self.admin.user_permissions = Permission.objects.filter(
            content_type__in=ContentType.objects.filter(app_label='crm'),
            codename='access_xmlrpc',
        )
        self.rpc_client = xmlrpclib.ServerProxy(
            'http://localhost:8000/xml-rpc/',
            transport=TestTransport(username='admin', password='abc123'),
        )
    
    def testAuthenticate(self):
        username = 'joe'
        password = 'moo000'
        User.objects.create_user(username, 'a@b.com', password)
        self.assertTrue(
            self.rpc_client.authenticate(username, password),
            'user %s failed to authenticate with %s' % (username, password,)
        )


class ContactTestCase(TestCase):
    def setUp(self):
        self.super_user = User.objects.create_user(
            'admin',
            'admin@abc.com',
            'abc123'
        )
        self.super_user.first_name = 'Super'
        self.super_user.last_name = 'User'
        self.super_user.is_superuser = True
        self.super_user.save()
        self.contact_user = User.objects.create_user(
            'john',
            'john@doe.com',
            'abc123',
        )
        g = Group.objects.create(name='Contact Notifications')
        g.user_set.add(self.contact_user)
        self.contact = crm.Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@doe.com',
            slug='john-doe',
            description='',
            sort_name='doe-john',
            type='individual',
            user=self.contact_user,
        )
        self.location = contactinfo.Location.objects.create()
        self.contact.locations.add(self.location)
        self.address = self.location.addresses.create(
            street='100 Generic St.',
            city='Chapel Hill',
            state_province='NC',
            postal_code=27516,
        )
        self.phone = self.location.phones.create(number='999-999-9999')
        self.post = {
            u'first_name': [u'John'],
            u'last_name': [u'Doe'],
            u'type': [u'2'],
            u'email': [u'john@doe.com'],
            u'submit': [u'Update \u2192'],
            u'picture': [u''],
            u'notes': [u''],
            u'country': [u'US'],
            u'initial-country': [u'US'],
            u'initial-type': [u'2'],
            u'location_phones-INITIAL_FORMS': [u'1'],
            u'location_addresses-INITIAL_FORMS': [u'1'],
            u'location_phones-TOTAL_FORMS': [u'3'],
            u'location_phones-0-id': self.phone.id,
            u'location_phones-0-type': [u'landline'],
            u'location_phones-0-location': self.location.id,
            u'location_phones-0-number': self.phone.number,
            u'location_addresses-0-street': self.address.street,
            u'location_addresses-0-postal_code': self.address.postal_code,
            u'location_addresses-0-location': self.location.id,
            u'location_addresses-0-id': self.address.id,
            u'location_addresses-0-city': self.address.city,
            u'location_addresses-0-state_province': self.address.state_province,
            u'location_phones-1-id': [u''],
            u'location_addresses-1-postal_code': [u''],
            u'location_addresses-1-id': [u''],
            u'location_phones-2-location': self.location.id,
            u'location_phones-2-type': [u'landline'],
            u'location_phones-1-type': [u'landline'],
            u'location_addresses-1-state_province': [u''],
            u'location_addresses-TOTAL_FORMS': [u'2'],
            u'location_phones-2-id': [u''],
            u'location_addresses-1-street': [u''],
            u'location_addresses-1-city': [u''],
            u'location_addresses-1-location': self.location.id,
            u'location_phones-1-number': [u''],
            u'location_phones-1-location': self.location.id,
            u'location_phones-2-number': [u'']
        }
    
    def testEmailContactForm(self):
        url = reverse('email_contact', args=[self.contact.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = {
            'name': 'Jane Doe',
            'email': 'jane@doe.com',
            'message': 'This is a test of the emergency broadcast system.',
        }
        response = self.client.post(
            url,
            data,
            follow=True,
        )
        self.assertEqual(len(mail.outbox), 2)
        message = mail.outbox[0]
        receipt = mail.outbox[1]
        self.assertEqual(message.subject, 'IAS Individual Contact Form')
        self.assertTrue(
            "You've received a message from Jane Doe" in message.body
        )
        self.assertTrue(self.contact.email in message.to)
        self.assertTrue(data['email'] in receipt.to)
    
    def testContactEdit(self):
        self.client.login(username='admin', password='abc123')
        response = self.client.get(
            reverse('edit_person', args=[self.contact.pk]),
            follow=True,
        )
        self.assertEquals(response.status_code, 200)
        
        data = {
            u'first_name': [u'John'],
            u'last_name': [u'Doe'],
            u'type': [u'2'],
            u'email': [u'john@doe.com'],
            u'submit': [u'Update \u2192'],
            u'picture': [u''],
            u'notes': [u''],
            u'country': [u'US'],
            u'initial-country': [u'US'],
            u'initial-type': [u'2'],
            u'location_phones-INITIAL_FORMS': [u'1'],
            u'location_addresses-INITIAL_FORMS': [u'1'],
            u'location_phones-TOTAL_FORMS': [u'3'],
            u'location_phones-0-id': self.phone.id,
            u'location_phones-0-type': [u'landline'],
            u'location_phones-0-location': self.location.id,
            u'location_phones-0-number': self.phone.number,
            u'location_addresses-0-street': self.address.street,
            u'location_addresses-0-postal_code': self.address.postal_code,
            u'location_addresses-0-location': self.location.id,
            u'location_addresses-0-id': self.address.id,
            u'location_addresses-0-city': self.address.city,
            u'location_addresses-0-state_province': self.address.state_province,
            u'location_phones-1-id': [u''],
            u'location_addresses-1-postal_code': [u''],
            u'location_addresses-1-id': [u''],
            u'location_phones-2-location': self.location.id,
            u'location_phones-2-type': [u'landline'],
            u'location_phones-1-type': [u'landline'],
            u'location_addresses-1-state_province': [u''],
            u'location_addresses-TOTAL_FORMS': [u'2'],
            u'location_phones-2-id': [u''],
            u'location_addresses-1-street': [u''],
            u'location_addresses-1-city': [u''],
            u'location_addresses-1-location': self.location.id,
            u'location_phones-1-number': [u''],
            u'location_phones-1-location': self.location.id,
            u'location_phones-2-number': [u'']
        }
        response = self.client.post(
            reverse('edit_person', args=[self.contact.pk]),
            data
        )
        self.assertEqual(len(mail.outbox), 0)
        
        data = {
            u'first_name': [u'John'],
            u'last_name': [u'Doe'],
            u'type': [u'2'],
            u'email': [u'john@doe.com'],
            u'submit': [u'Update \u2192'],
            u'picture': [u''],
            u'notes': [u''],
            u'country': [u'US'],
            u'initial-country': [u'US'],
            u'initial-type': [u'2'],
            u'location_phones-INITIAL_FORMS': [u'1'],
            u'location_addresses-INITIAL_FORMS': [u'1'],
            u'location_phones-TOTAL_FORMS': [u'3'],
            u'location_phones-0-id': self.phone.id,
            u'location_phones-0-type': [u'landline'],
            u'location_phones-0-location': self.location.id,
            u'location_phones-0-number': [u'888-888-8888'],
            u'location_addresses-0-street': self.address.street,
            u'location_addresses-0-postal_code': self.address.postal_code,
            u'location_addresses-0-location': self.location.id,
            u'location_addresses-0-id': self.address.id,
            u'location_addresses-0-city': self.address.city,
            u'location_addresses-0-state_province': self.address.state_province,
            u'location_phones-1-id': [u''],
            u'location_addresses-1-postal_code': [u''],
            u'location_addresses-1-id': [u''],
            u'location_phones-2-location': self.location.id,
            u'location_phones-2-type': [u'landline'],
            u'location_phones-1-type': [u'landline'],
            u'location_addresses-1-state_province': [u''],
            u'location_addresses-TOTAL_FORMS': [u'2'],
            u'location_phones-2-id': [u''],
            u'location_addresses-1-street': [u''],
            u'location_addresses-1-city': [u''],
            u'location_addresses-1-location': self.location.id,
            u'location_phones-1-number': [u''],
            u'location_phones-1-location': self.location.id,
            u'location_phones-2-number': [u'']
        }
        response = self.client.post(
            reverse('edit_person', args=[self.contact.pk]),
            data
        )
        self.assertEqual(len(mail.outbox), 1)
    
    def testContactSlugs(self):
        self.client.login(username='admin', password='abc123')
        response = self.client.post(
            reverse('edit_person', args=[self.contact.pk]),
            self.post,
            follow=True,
        )
        self.assertEquals(response.status_code, 200)
        contact = crm.Contact.objects.get(user=self.contact_user)
        self.assertEqual(contact.slug, self.contact.slug)
        self.assertEqual(contact.sort_name, self.contact.sort_name)


class LoginRegistrationTestCase(TestCase):
    def setUp(self):
        self.contact = crm.Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@doe.com',
            slug='john-doe',
            description='',
            sort_name='doe-john',
        )
        self.registration = \
            crm.LoginRegistration.objects.create_pending_login(self.contact)
    
    def testPendingLoginCreation(self):
        self.registration.prepare_email(send=True)
        self.assertEqual(len(mail.outbox), 1)
        url = reverse('activate_login', args=[self.registration.activation_key])
        self.assertTrue(url in mail.outbox[0].body)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url, {
            'password1': 'abc',
            'password2': 'abc',
        }, follow=True)
        self.assertTrue(
            self.client.login(
                username=User.objects.get(email='john@doe.com').username, 
                password='abc',
            )
        )
    
    def testAlreadyLoggedInActivation(self):
        user = User.objects.create_user('test', 'test@test.com', 'test')
        self.client.login(username='test', password='test')
        url = reverse('activate_login', args=[self.registration.activation_key])
        response = self.client.get(url, follow=True)
        self.assertContains(response, "already logged in")
    
    
