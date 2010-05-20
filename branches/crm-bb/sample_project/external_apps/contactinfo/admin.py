from django.contrib import admin

from contactinfo import models as contactinfo

class LocationTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug',)
    prepopulated_fields = {'slug': ('name',)}
admin.site.register(contactinfo.LocationType, LocationTypeAdmin)


class PhoneAdmin(admin.TabularInline):
    model = contactinfo.Phone
    extra = 3


class AddressAdmin(admin.StackedInline):
    model = contactinfo.Address
    extra = 1


class LocationAdmin(admin.ModelAdmin):
    list_display = ('type', 'country',)
    filter_fields = ('type',)
    inlines = (AddressAdmin, PhoneAdmin, )
admin.site.register(contactinfo.Location, LocationAdmin)