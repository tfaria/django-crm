# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# $Id: xmlrpc.py 428 2009-07-14 03:48:07Z tobias $
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

import re

from SimpleXMLRPCServer import SimpleXMLRPCDispatcher

from django.conf import settings
from django.http import HttpResponse
from django.contrib import auth
from django.forms.fields import email_re
from django.contrib.auth.models import User

from timepiece import models as timepiece
from crm import models as crm
from crm.decorators import has_perm_or_basicauth

try:
    # Python 2.5
    dispatcher = SimpleXMLRPCDispatcher(allow_none=False, encoding=None)
except:
    # Python 2.4
    dispatcher = SimpleXMLRPCDispatcher()


@has_perm_or_basicauth('crm.access_xmlrpc', realm='django-crm XML-RPC Service')
def rpc_handler(request):
    response = HttpResponse()
    
    if len(request.POST):
        response.write(dispatcher._marshaled_dispatch(request.raw_post_data))
    else:
        response.write("<b>This is the django-crm XML-RPC Service.</b><br>")
        response.write("You need to invoke it using an XML-RPC Client!<br>")
        response.write("The following methods are available:<ul>")
        for method in dispatcher.system_listMethods():
            sig = dispatcher.system_methodSignature(method)
            help = dispatcher.system_methodHelp(method)
            response.write("<li><b>%s</b>: [%s] %s" % (method, sig, help))
        response.write("</ul>")
    
    response['Content-length'] = str(len(response.content))
    return response


def _get_user(username):
    if email_re.search(username):
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            user = None
    else:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
    return user


def authenticate(username, password):
    return bool(auth.authenticate(username=username, password=password))
dispatcher.register_function(authenticate, 'authenticate')


def trac_groups_for_user(environment, username):
    groups = []
    user = _get_user(username)
    try:
        project = timepiece.Project.objects.get(
            trac_environment=environment,
            contacts=user,
        )
    except timepiece.Project.DoesNotExist:
        project = None
    if user and project:
        groups = crm.ProjectRelationshipType.objects.filter(
            project_relationships__user=user,
            project_relationships__project=project,
        ).values_list('slug', flat=True)
        # snip 'trac-' off the front of the slug
        groups = [str(group[5:]) for group in groups]
    if user:
        global_groups = user.groups.filter(
            name__istartswith='trac-',
        ).values_list('name', flat=True)
        global_groups = [str(group[5:]) for group in global_groups]
        groups.extend(global_groups)
    return list(set(groups))
dispatcher.register_function(trac_groups_for_user, 'trac_groups_for_user')


def callerid(number):
    number = re.sub('[^0-9]', '', number)
    if number.startswith('1'):
        number = number[1:]
    parts = (number[0:3], number[3:6], number[6:10])
    number = '-'.join(parts)
    
    try:
        user = User.objects.get(profile__locations__phones__number=number)
        return user.get_full_name()
    except User.DoesNotExist:
        try:
            business = \
              crm.Business.objects.get(locations__phones__number=number)
            return business.name
        except crm.Business.DoesNotExist:
            return number
dispatcher.register_function(callerid, 'callerid')
