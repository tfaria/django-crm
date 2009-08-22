# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# $Id: admin.py 433 2009-07-14 04:10:28Z tobias $
# ----------------------------------------------------------------------------
#
#    Copyright (C) 2008 Caktus Consulting Group, LLC
#
#    This file is part of minibooks.
#
#    minibooks is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of 
#    the License, or (at your option) any later version.
#    
#    minibooks is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#    
#    You should have received a copy of the GNU Affero General Public License
#    along with minibooks.  If not, see <http://www.gnu.org/licenses/>.
#


from django import forms
from django.contrib import admin
from django.contrib.auth.models import User, Group

from crm import models as crm


class BusinessTypeAdmin(admin.ModelAdmin):
    pass
admin.site.register(crm.BusinessType, BusinessTypeAdmin)


class RelationshipType(admin.ModelAdmin):
    list_display = ('name', 'slug',)
admin.site.register(crm.RelationshipType, RelationshipType)


class ContactAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('id', 'type', 'name', 'first_name', 'last_name', 'email')
    list_filter = ('type',)
    order_by = ('sortname',)
admin.site.register(crm.Contact, ContactAdmin)
