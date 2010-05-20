from django.conf.urls.defaults import *
from django.conf import settings

from crm.xmlrpc import rpc_handler

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # crm and contactinfo URLs (required)
    (r'^crm/', include('crm.urls')),
    (r'^contactinfo/', include('contactinfo.urls')),
    (r'^ajax/', include('ajax_select.urls')),
    
    url(r'^xml-rpc/', rpc_handler, name='xml_rpc'),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/(.*)', admin.site.root),
    
    # use the contrib.auth login/logout views for authentication (optional)
    url(
        r'^accounts/login/$', 'django.contrib.auth.views.login', 
        name='auth_login',
    ),
    url(
        r'^accounts/logout/$', 'django.contrib.auth.views.logout', 
        name='auth_logout',
    ),
    # redirect '/' to the CRM dashboard (optional)
    url(
        '^$', 
        'django.views.generic.simple.redirect_to', 
        {'url': '/crm/dashboard/'},
    ),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        ( r'^%s(?P<path>.*)' % settings.MEDIA_URL.lstrip('/'),
          'django.views.static.serve',
          { 'document_root' : settings.MEDIA_ROOT, 'show_indexes': True }
        ),
    )
