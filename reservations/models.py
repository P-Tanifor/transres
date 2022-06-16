from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse


class AvailableBuses(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    registration_number = models.CharField(max_length=10)
    current_city = models.CharField(max_length=20)
    destination = models.CharField(max_length=20)
    fare = models.IntegerField()
    departure_time = models.CharField(max_length=30)
    number_of_seats_available = models.IntegerField()
    departure_date = models.DateField()
    company_Info = models.TextField(max_length=500)

    def __str__(self):
        return self.registration_number

    def get_absolute_url(self):
        return reverse('available_buses_detail', kwargs={'pk': self.pk})


class PassengerBookings(models.Model):
    bus_registration_number = models.CharField(max_length=10)
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    take_off_city = models.CharField(max_length=20)
    destination = models.CharField(max_length=20)
    fare = models.IntegerField()
    departure_date = models.DateField()

    def __str__(self):
        return self.first_name


class Payment(models.Model):
    Enter_Your_MOMO_Number = models.CharField(max_length=15)


class LoadedBusInfo(models.Model):
    bus_registration_number = models.CharField(max_length=10)
    take_off_city = models.CharField(max_length=20)
    destination = models.CharField(max_length=20)
    departure_date = models.DateField()
    #departure_time = models.CharField(max_length=10)


class Transfers(models.Model):
    payee_company_name = models.CharField(max_length=50)
    payee_account_number = models.CharField(max_length=50)
    transfer_date_time = models.DateTimeField()
    transfer_amount = models.IntegerField()

    def __str__(self):
        return self.payee_company_name
