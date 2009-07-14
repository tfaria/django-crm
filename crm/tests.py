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
from django.test import Client, TestCase
from django.contrib.contenttypes.models import ContentType

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
