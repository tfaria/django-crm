from django.conf import settings

def crm_settings(request):
    default_famfamfam_url = settings.MEDIA_URL + 'images/icons/'
    famfamfam_url = getattr(settings, 'FAMFAMFAM_URL', default_famfamfam_url)
    context = {
        'FAMFAMFAM_URL': famfamfam_url,
    }
    return context
