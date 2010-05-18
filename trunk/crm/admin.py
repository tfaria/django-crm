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
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from crm import models as crm


class BusinessTypeAdmin(admin.ModelAdmin):
    pass
admin.site.register(crm.BusinessType, BusinessTypeAdmin)


class RelationshipType(admin.ModelAdmin):
    list_display = ('name', 'slug',)
admin.site.register(crm.RelationshipType, RelationshipType)


class InteractionAdmin(admin.ModelAdmin):
    pass
admin.site.register(crm.Interaction, InteractionAdmin)


def send_account_activation_email(modeladmin, request, queryset):
    selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
    selected = ["ids=%d" % pk for pk in selected]
    url = reverse('create_registration')
    return HttpResponseRedirect("%s?%s" % (
        url,
        "&".join(selected)
    ))


class ContactAdmin(admin.ModelAdmin):
    search_fields = ('first_name', 'last_name', 'name', 'email')
    raw_id_fields = ('user', 'locations')
    list_display = ('id', 'type', 'name', 'first_name', 'last_name', 'email', 'external_id')
    list_filter = ('type',)
    order_by = ('sortname',)
    actions = [send_account_activation_email]
admin.site.register(crm.Contact, ContactAdmin)


class LoginRegistrationAdmin(admin.ModelAdmin):
    list_display = ('contact', 'date', 'activation_key', 'activated')
    raw_id_fields = ('contact',)
    list_filter = ('activated', 'date',)
    order_by = ('date',)
admin.site.register(crm.LoginRegistration, LoginRegistrationAdmin)


class ContactRelationshipAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_contact', 'to_contact', 'start_date',
                    'end_date')
    raw_id_fields = ('from_contact', 'to_contact')
    list_filter = ('start_date', 'end_date',)
    order_by = ('start_date',)
admin.site.register(crm.ContactRelationship, ContactRelationshipAdmin)

