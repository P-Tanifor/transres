from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from datetime import date
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.views.generic.edit import FormMixin
from django.urls import reverse
from .forms import BusDetailsForm, PaymentForm, LoadedBusInfoForm, TransfersForm
from .models import AvailableBuses, PassengerBookings, Transfers
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.core.exceptions import PermissionDenied
from TransportReservations import settings
import uuid
from http.client import HTTPSConnection
import urllib.parse
import urllib.request
import base64
import json
import time


#def home(request):
#   context = {
#        'available_buses': AvailableBuses.objects.all(),
#        'title': 'Home'
#    }
#    return render(request, 'reservations/home.html', context=context)


class AvailableBusesListView(ListView):
   model = AvailableBuses
   template_name = 'reservations/available_buses.html'
   context_object_name = 'available_buses'
   ordering = ['departure_date']
   paginate_by = 5

   for bus in AvailableBuses.objects.all():
       if bus.departure_date < date.today():
           bus.delete()


class IndividualCompanyAvailableBusesListView(ListView):
    model = AvailableBuses
    template_name = 'reservations/individual_comp_available_buses.html'
    context_object_name = 'available_buses'
    paginate_by = 5

    def get_queryset(self):
        company_name = get_object_or_404(User, username=self.kwargs.get('username'))
        return AvailableBuses.objects.filter(author=company_name).order_by('departure_date')


class AvailableBusesDetailView(FormMixin, LoginRequiredMixin, DetailView):
    model = AvailableBuses
    template_name = 'reservations/availableBuses_detail.html'
    form_class = BusDetailsForm

    def get_success_url(self):
        return reverse('available_buses_detail', kwargs={'pk': self.object.id})

    def get_context_data(self, **kwargs):
        context = super(AvailableBusesDetailView, self).get_context_data(**kwargs)
        context['detail_form'] = BusDetailsForm(instance=self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        detail_form = self.get_form()
        if detail_form.is_valid():
            return self.form_valid(detail_form)
        else:
            return self.form_invalid(detail_form)

    def form_valid(self, form):
        # form.instance.author = self.object.author
        # form.save()
        return super(AvailableBusesDetailView, self).form_valid(form)


def jwt_token():
    api_user = settings.config.get('api_user').encode('utf_8')
    api_key = settings.config.get('api_key').encode('utf_8')
    api_user_and_key = api_user + b':' + api_key
    encoded = base64.b64encode(api_user_and_key)
    headers = {
        # Request headers
        'Authorization': b'Basic ' + encoded,
        'Ocp-Apim-Subscription-Key': settings.config.get('Ocp-Apim-Subscription-Key'),
	}
    params = urllib.parse.urlencode({})
    try:
        conn = HTTPSConnection('sandbox.momodeveloper.mtn.com')
        conn.request("POST", "/collection/token/?%s" % params, "{body}", headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()
        return data

    except Exception as e:
        print(e)


class Payment(AvailableBusesDetailView):

    def get(self, request, *args, **kwargs):
        context = {
            'payment_form': PaymentForm()
        }
        return render(request, 'reservations/payment_form.html', context=context)

    def post(self, request, *args, **kwargs):
        obj = super().get_object()
        if request.method == 'POST':
            form = PaymentForm(request.POST)
            if form.is_valid():
                token = json.loads(jwt_token().decode())['access_token']
                reference_id = str(uuid.uuid4())
                amount = obj.fare
                party_id = request.POST.get('Enter_Your_MOMO_Number')
                headers = {
                    # Request headers
                    'Authorization': 'Bearer ' + token,
                    'X-Callback-Url': 'http://transresnetwork.com/momoapi/callback',
                    'X-Reference-Id': reference_id,
                    'X-Target-Environment': 'sandbox',
                    'Content-Type': 'application/json',
                    'Ocp-Apim-Subscription-Key': settings.config.get('Ocp-Apim-Subscription-Key')
                    }
                params = urllib.parse.urlencode({})
                body = json.dumps({
                    "amount": str(amount),
                    "currency": "EUR",
                    "externalId": str(party_id),
                    "payer": {
                        "partyIdType": "MSISDN",
                        "partyId": party_id
                    },
                    "payerMessage": f"You have made payment for a seat on bus {obj.registration_number}. Thank you!",
                    "payeeNote": "Payment Received. Thank you!"
                })
                try:
                    conn = HTTPSConnection('sandbox.momodeveloper.mtn.com')
                    conn.request("POST", "/collection/v1_0/requesttopay?%s" % params, body, headers)
                    response = conn.getresponse()
                    status = response.status
                    reason = response.reason
                    conn.close()
                    if status == 202 and reason == 'Accepted':
                        trans_status = booking_success(reference_id, params, body, headers)
                        if trans_status == 'SUCCESSFUL':
                            obj.number_of_seats_available -= 1
                            if obj.number_of_seats_available == 0:
                                obj.delete()
                                PassengerBookings.objects.create(bus_registration_number=obj.registration_number,
                                                                 first_name=self.request.user.first_name,
                                                                 last_name=self.request.user.last_name,
                                                                 take_off_city=obj.current_city,
                                                                 destination=obj.destination,
                                                                 fare=obj.fare,
                                                                 departure_date=obj.departure_date.strftime('%Y-%m-%d'))
                                context = {'payer_info': {'bus': obj.registration_number,
                                                          'f_name': self.request.user.first_name,
                                                          'l_name': self.request.user.last_name,
                                                          'd_date': obj.departure_date,
                                                          'take_off': obj.current_city, 'destination': obj.destination}}
                                return render(request, 'reservations/about.html', context=context)
                            else:
                                AvailableBuses.objects.filter(registration_number=obj.registration_number,
                                                              departure_date=obj.departure_date,
                                                              departure_time=obj.departure_time).update(
                                    number_of_seats_available=obj.number_of_seats_available)
                                PassengerBookings.objects.create(bus_registration_number=obj.registration_number,
                                                                 first_name=self.request.user.first_name,
                                                                 last_name=self.request.user.last_name,
                                                                 take_off_city=obj.current_city,
                                                                 destination=obj.destination,
                                                                 fare=obj.fare,
                                                                 departure_date=obj.departure_date.strftime('%Y-%m-%d'))
                                context = {'payer_info': {'bus': obj.registration_number,
                                                          'f_name': self.request.user.first_name,
                                                          'l_name': self.request.user.last_name,
                                                          'd_date': obj.departure_date,
                                                          'take_off': obj.current_city, 'destination': obj.destination}}

                                return render(request, 'reservations/about.html', context=context)
                        else:
                            return render(request, 'reservations/invalid_number.html')
                    else:
                        return HttpResponse('REQUEST DENIED')
                except Exception as e:
                    print(e)
            else:
                return HttpResponse('form invalid')


class CompleteTransfers(View):
    #customers = ['147258369', '123456789', '789456123']

    def get(self, request, *args, **kwargs):
        context = {
            'transfers_form': TransfersForm()
        }
        return render(request, 'reservations/transfers_form.html', context=context)

    def post(self, request, *args, **kwargs):
        if request.method == 'POST':
            form = TransfersForm(request.POST)
            if form.is_valid():
                if request.POST.get('payee_account_number') in settings.config.get('customers'):
                    token = json.loads(disbursement_jwt().decode()).get('access_token')
                    reference_id = str(uuid.uuid4())
                    account_number = request.POST.get('payee_account_number')
                    amount = request.POST.get('transfer_amount')
                    headers = {
                        # Request headers
                        'Authorization': 'Bearer ' + token,
                        'X-Callback-Url': 'http://transresnetwork.com/momoapi/callback',
                        'X-Reference-Id': reference_id,
                        'X-Target-Environment': 'sandbox',
                        'Content-Type': 'application/json',
                        'Ocp-Apim-Subscription-Key': settings.config.get('d-Ocp-Apim-Subscription-Key'),
                    }
                    params = urllib.parse.urlencode({})
                    body = json.dumps({
                        "amount": amount,
                        "currency": "EUR",
                        "externalId": account_number,
                        "payee": {
                            "partyIdType": "MSISDN",
                            "partyId": account_number
                        },
                        "payerMessage": "Payment for today.",
                        "payeeNote": "Thanks for trusting us."
                    })
                    try:
                        conn = HTTPSConnection('sandbox.momodeveloper.mtn.com')
                        conn.request("POST", "/disbursement/v1_0/transfer?%s" % params, body, headers)
                        response = conn.getresponse()
                        if response.status == 202 and response.reason == 'Accepted':
                            trans_status = validate_transfer(reference_id, params, body, headers)
                            if trans_status == 'SUCCESSFUL':
                                Transfers.objects.create(payee_company_name=request.POST.get('payee_company_name'),
                                                         payee_account_number=request.POST.get('payee_account_number'),
                                                         transfer_date_time=timezone.now(),
                                                         transfer_amount=request.POST.get('transfer_amount'))
                                return render(request, 'reservations/transfer_success.html')
                            else:
                                return HttpResponse('TRANSACTION FAILED')
                        else:
                            return HttpResponse('REQUEST DENIED')
                    except Exception as e:
                        print(e)
                else:
                    return HttpResponse('INVALID RECIPIENT')
            else:
                return HttpResponse('Form Invalid')


def validate_transfer(ref, params, body, headers):
    conn = HTTPSConnection('sandbox.momodeveloper.mtn.com')
    conn.request("GET", f"/disbursement/v1_0/transfer/{ref}?%s" % params, body, headers)
    response = conn.getresponse()
    response_data = response.read()
    response_data = json.loads(response_data.decode()).get('status')
    conn.close()
    while (response_data != 'SUCCESSFUL') and (response_data != 'FAILED'):
        time.sleep(1)
        booking_success(ref, params, body, headers)
    return response_data


def disbursement_jwt():
    api_user = settings.config.get('d_api_user').encode('utf_8')
    api_key = settings.config.get('d_api_key').encode('utf_8')
    api_user_and_key = api_user + b':' + api_key
    encoded = base64.b64encode(api_user_and_key)
    headers = {
        # Request headers
        'Authorization': b'Basic ' + encoded,
        'Ocp-Apim-Subscription-Key': settings.config.get('d-Ocp-Apim-Subscription-Key'),
    }
    params = urllib.parse.urlencode({})
    try:
        conn = HTTPSConnection('sandbox.momodeveloper.mtn.com')
        conn.request("POST", "/disbursement/token/?%s" % params, "{body}", headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()
        return data
    except Exception as e:
        print(e)










                    
#if status == 202 and reason == 'Accepted':
#                        trans_status = booking_success(reference_id, params, body, headers)
#                        if trans_status == 'SUCCESSFUL':
#                            obj.number_of_seats_available -= 1
#                            if obj.number_of_seats_available == 0:
#                                obj.delete()
#                                PassengerBookings.objects.create(bus_registration_number=obj.registration_number,
#                                                                 first_name=self.request.user.first_name,
#                                                                 last_name=self.request.user.last_name,
#                                                                 take_off_city=obj.current_city,
#                                                                 destination=obj.destination,
#                                                                 fare=obj.fare,
#                                                                 departure_date=obj.departure_date.strftime('%Y-%m-%d'))
#                                context = {'payer_info': {'bus': obj.registration_number,
#                                                          'f_name': self.request.user.first_name,
#                                                          'l_name': self.request.user.last_name,
#                                                          'd_date': obj.departure_date,
#                                                          'take_off': obj.current_city, 'destination': obj.destination}}
#                                return render(request, 'reservations/about.html', context=context)
#                            else:
#                                AvailableBuses.objects.filter(registration_number=obj.registration_number,
#                                                              departure_date=obj.departure_date,
#                                                              departure_time=obj.departure_time).update(
#                                    number_of_seats_available=obj.number_of_seats_available)
#                                PassengerBookings.objects.create(bus_registration_number=obj.registration_number,
#                                                                 first_name=self.request.user.first_name,
#                                                                 last_name=self.request.user.last_name,
#                                                                 take_off_city=obj.current_city,
#                                                                 destination=obj.destination,
#                                                                 fare=obj.fare,
#                                                                 departure_date=obj.departure_date.strftime('%Y-%m-%d'))
#                                context = {'payer_info': {'bus': obj.registration_number,
#                                                          'f_name': self.request.user.first_name,
#                                                          'l_name': self.request.user.last_name,
#                                                          'd_date': obj.departure_date,
#                                                          'take_off': obj.current_city, 'destination': obj.destination}}

#                                return render(request, 'reservations/about.html', context=context)
#                        return render(request, 'reservations/invalid_number.html')
#                except Exception as e:
#                    print(e)



#if status == 202 and reason == 'Accepted':
#                        obj.number_of_seats_available -= 1
#                        if obj.number_of_seats_available == 0:
#                            obj.delete()
#                            PassengerBookings.objects.create(bus_registration_number=obj.registration_number,
#                                                             first_name=self.request.user.first_name,
#                                                             last_name=self.request.user.last_name,
#                                                             take_off_city=obj.current_city,
#                                                             destination=obj.destination,
#                                                             fare=obj.fare,
#                                                             departure_date=obj.departure_date.strftime('%Y-%m-%d'))
#                            context = {'payer_info': {'bus': obj.registration_number,
#                                                      'f_name': self.request.user.first_name,
#                                                      'l_name': self.request.user.last_name,
#                                                      'd_date': obj.departure_date,
#                                                      'take_off': obj.current_city,
#                                                      'destination': obj.destination}}
#                            return render(request, 'reservations/about.html', context=context)
#                        else:
#                            AvailableBuses.objects.filter(registration_number=obj.registration_number,
#                                                          departure_date=obj.departure_date,
#                                                          departure_time=obj.departure_time).update(
#                                number_of_seats_available=obj.number_of_seats_available)
#                            PassengerBookings.objects.create(bus_registration_number=obj.registration_number,
#                                                             first_name=self.request.user.first_name,
#                                                             last_name=self.request.user.last_name,
#                                                             take_off_city=obj.current_city,
#                                                             destination=obj.destination,
#                                                             fare=obj.fare,
#                                                             departure_date=obj.departure_date.strftime('%Y-%m-%d'))
#                            context = {'payer_info': {'bus': obj.registration_number,
#                                                      'f_name': self.request.user.first_name,
#                                                      'l_name': self.request.user.last_name,
#                                                      'd_date': obj.departure_date,
#                                                      'take_off': obj.current_city,
#                                                      'destination': obj.destination}}
#                            return render(request, 'reservations/about.html', context=context)
#                    return render(request, 'reservations/invalid_number.html')
#                except Exception as e:
#                    print(e)


def booking_success(ref, params, body, headers):
    conn = HTTPSConnection('sandbox.momodeveloper.mtn.com')
    conn.request("GET", f"/collection/v1_0/requesttopay/{ref}?%s" % params, body, headers)
    response = conn.getresponse()
    response_data = response.read()
    response_data = json.loads(response_data.decode()).get('status')
    # reason1 = response.reason
    # status1 = response.status
    conn.close()
    while (response_data != 'SUCCESSFUL') and (response_data != 'FAILED'):
        time.sleep(1)
        booking_success(ref, params, body, headers)
    return response_data



class AvailableBusesCreateView(LoginRequiredMixin, CreateView):

    model = AvailableBuses
    fields = ['registration_number', 'current_city', 'destination', 'fare', 'departure_time',
              'number_of_seats_available', 'departure_date', 'company_Info']

    def get(self, request, *args, **kwargs):
        if self.request.user.is_staff:
            return super().get(request)
        else:
            raise PermissionDenied

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

class AvailableBusesUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = AvailableBuses
    fields = ['registration_number', 'current_city', 'destination', 'fare', 'departure_time',
              'number_of_seats_available', 'departure_date']

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def test_func(self):
        bus = self.get_object()
        if self.request.user == bus.author:
            return True
        return False


class AvailableBusesDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = AvailableBuses
    success_url = '/available_buses'

    def test_func(self):
        bus = self.get_object()
        if self.request.user == bus.author:
            return True
        return False


class LoadedBusInfoView(PassengerBookings, View):
    def get(self, request, *args, **kwargs):
        context = {
            'loaded_bus_info_form': LoadedBusInfoForm()
        }
        return render(request, 'reservations/loaded_bus_info_form.html', context=context)

    def post(self, request, *args, **kwargs):
        form = LoadedBusInfoForm(request.POST)
        if form.is_valid():
            loaded_bus_info = PassengerBookings.objects.filter(
                                             bus_registration_number=request.POST.get('bus_registration_number'),
                                             take_off_city=request.POST.get('take_off_city'),
                                             destination=request.POST.get('destination'),
                                             departure_date=request.POST.get('departure_date'))
            context ={
                'loaded_bus_info': loaded_bus_info
            }
            return render(request, 'reservations/loaded_bus_info.html', context=context)


def about(request):
    return render(request, 'reservations/about.html', {'title': 'about'})


def feedback(request):
    return render(request, 'reservations/feedback.html')


