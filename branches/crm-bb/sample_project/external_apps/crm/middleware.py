# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# $Id: middleware.py 425 2009-07-14 03:43:01Z tobias $
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

from django.http import Http404
from django.shortcuts import get_object_or_404
from crm import models as crm

try:
    from timepiece import models as timepiece
except ImportError:
    timepiece = None

class StandardViewKwargsMiddleware(object):
    """
    """
    
    def process_request(self, request):
        """
        Set a few attributes on the request so that we are absolutely
        certain they exist in all places in the code.
        """
        request.business = None
        request.project = None
        request.contact = None
        
    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.user.is_authenticated():
            try:
                request.contact = crm.Contact.objects.get(user=request.user)
            except crm.Contact.DoesNotExist:
                pass
        
        if 'business_id' in view_kwargs:
            args = {
                'pk': view_kwargs.pop('business_id'),
                'type': 'business',
            }
            if args['pk']:
                try:
                    request.business = crm.Contact.objects.get(**args)
                except crm.Contact.DoesNotExist:
                    raise Http404
            view_kwargs['business'] = request.business
        
        if 'project_id' in view_kwargs and timepiece:
            args = {
                'pk': view_kwargs.pop('project_id'),
            }
            if request.business:
                args['business'] = request.business
            if args['pk']:
                request.project = get_object_or_404(
                    timepiece.Project, 
                    **args
                )
            view_kwargs['project'] = request.project
