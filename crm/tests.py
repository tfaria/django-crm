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
from xml.parsers.expat import ExpatError

from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Permission
from django.test import Client, TestCase, TransactionTestCase
from django.contrib.contenttypes.models import ContentType
from django.core import mail

from crm import models as crm

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
            content_type__in=ContentType.objects.filter(app_label='crm')
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
        self.contact = crm.Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@doe.com',
            slug='john-doe',
            description='',
            sort_name='doe-john',
        )
    
    def testEmailForm(self):
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
            self.client.login(username='john@doe.com', password='abc')
        )
    
    def testAlreadyLoggedInActivation(self):
        user = User.objects.create_user('test', 'test@test.com', 'test')
        self.client.login(username='test@test.com', password='test')
        url = reverse('activate_login', args=[self.registration.activation_key])
        response = self.client.get(url, follow=True)
        self.assertTrue("already logged in" in response.content)
    
    