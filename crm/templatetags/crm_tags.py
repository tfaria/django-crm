# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# $Id: crm_tags.py 430 2009-07-14 03:49:10Z tobias $
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

from django import template

register = template.Library()

@register.filter(name='project_relationship')
def project_relationship(user, project):
    label = user.projectrelationship_set.get(project=project).get_label()
    if label:
        label = '(%s)' % label
    return label
project_relationship.is_safe = True
