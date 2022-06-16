from django.contrib import admin
from .models import AvailableBuses, PassengerBookings, Payment, Transfers

# Register your models here.

admin.site.register(AvailableBuses)
admin.site.register(PassengerBookings)
admin.site.register(Payment)
admin.site.register(Transfers)
