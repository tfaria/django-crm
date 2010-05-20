from django.conf.urls.defaults import *
from django.contrib.auth import views as auth_views

import contactinfo.views as views

urlpatterns = patterns('',
# sample URLs for create_edit_location view:
#    url(
#        r'^location/create/$', 
#        views.create_edit_location, 
#        name='create_location',
#    ),
#    url(
#        r'^location/(?P<location_id>\d+)/edit/$', 
#        views.create_edit_location, 
#        name='edit_location'
#    ),
    url(
        r'^address_formset_html/$', 
        views.get_address_formset_html, 
        name='get_address_formset_html',
    ),
)
