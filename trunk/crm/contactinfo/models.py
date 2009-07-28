from django.db import models

from countries import models as countries


class LocationType(models.Model):
    name = models.CharField(max_length=30)
    slug = models.CharField(max_length=30)

    def __unicode__(self):
        return self.name


class Location(models.Model):
    type = models.ForeignKey(LocationType)
    country = models.ForeignKey(countries.Country)

    def __unicode__(self):
        return '%s (%s)' % (self.country, self.type)


class Address(models.Model):
    location = models.ForeignKey(Location, related_name='addresses')
    
    street = models.TextField()
    city = models.CharField(max_length=255)
    state_province = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=255)
    
    class Meta:
        verbose_name_plural = 'addresses'
    
    def __unicode__(self):
        return "%s, %s, %s %i" % \
            (self.street, self.city, self.state_province, self.postal_code)


class Phone(models.Model):
    TYPE_CHOICES = (
        ('landline', 'Land Line'),
        ('mobile', 'Mobile'),
        ('fax', 'Fax')
    )
    
    location = models.ForeignKey(Location, related_name='phones')
    type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    number = models.CharField(max_length=30)
    
    def __unicode__(self):
        return self.number