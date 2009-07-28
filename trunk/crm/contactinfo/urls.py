from django.conf.urls.defaults import *
from django.contrib.auth import views as auth_views

import contactinfo.views as views

urlpatterns = patterns('',
    
    url(r'^location/create/$', views.create_edit_location, name='create_location'),

)
