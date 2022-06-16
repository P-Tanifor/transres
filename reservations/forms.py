from django import forms
from .models import AvailableBuses, Payment, LoadedBusInfo, Transfers


class BusDetailsForm(forms.ModelForm):
    class Meta:
        model = AvailableBuses
        fields = ['registration_number', 'current_city', 'destination', 'fare', 'departure_time',
                  'number_of_seats_available', 'departure_date', 'company_Info']


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['Enter_Your_MOMO_Number']


class LoadedBusInfoForm(forms.ModelForm):
    class Meta:
        model = LoadedBusInfo
        fields = ['bus_registration_number', 'take_off_city', 'destination', 'departure_date']


class TransfersForm(forms.ModelForm):
    class Meta:
        model = Transfers
        fields = ['payee_company_name', 'payee_account_number', 'transfer_amount']

