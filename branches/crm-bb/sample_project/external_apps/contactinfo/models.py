from django.db import models
from django.conf import settings

from countries import models as countries


class LocationType(models.Model):
    name = models.CharField(max_length=30)
    slug = models.CharField(max_length=30)

    def __unicode__(self):
        return self.name


def get_default_locationtype():
    default_slug = getattr(settings, 'DEFAULT_LOCATIONTYPE_SLUG', 'office')
    return LocationType.objects.get(slug=default_slug)


def get_default_country():
    default_iso = getattr(settings, 'DEFAULT_COUNTRY_ISO', 'US')
    return countries.Country.objects.get(iso=default_iso)


class Location(models.Model):
    type = models.ForeignKey(LocationType, default=get_default_locationtype)
    country = models.ForeignKey(countries.Country, default=get_default_country)

    def __unicode__(self):
        return '%s (%s)' % (self.country, self.type)


class Address(models.Model):
    location = models.ForeignKey(Location, related_name='addresses')
    
    street = models.TextField(blank=True)
    city = models.CharField(max_length=255, blank=True)
    state_province = models.CharField(max_length=255, blank=True)
    postal_code = models.CharField(max_length=255, blank=True)
    
    class Meta:
        verbose_name_plural = 'addresses'
    
    def __unicode__(self):
        return "%s\n%s, %s %s" % \
            (self.street, self.city, self.state_province, self.postal_code)


class Phone(models.Model):
    PHONE_TYPES = (
        ('landline', 'Land Line'),
        ('mobile', 'Mobile'),
        ('fax', 'Fax')
    )
    
    location = models.ForeignKey(Location, related_name='phones')
    number = models.CharField(max_length=30)
    type = models.CharField(
        max_length=15, 
        choices=PHONE_TYPES, 
        default='landline',
    )
    
    def __unicode__(self):
        return self.number