from django.urls import path
from .views import AvailableBusesListView, AvailableBusesDetailView, AvailableBusesCreateView, AvailableBusesUpdateView, \
    AvailableBusesDeleteView, Payment, IndividualCompanyAvailableBusesListView, LoadedBusInfoView, CompleteTransfers
from . import views

urlpatterns = [
#    path('', views.home, name='reservations_home'),
    path('', AvailableBusesListView.as_view(), name='available_buses'),
    path('available_buses/', AvailableBusesListView.as_view(), name='available_buses'),
    path('company/<str:username>/', IndividualCompanyAvailableBusesListView.as_view(), name='individual_company_buses'),
    path('available_buses/<int:pk>/', AvailableBusesDetailView.as_view(), name='available_buses_detail'),
    path('available_buses/int:<pk>/pay/', Payment.as_view(), name='available_buses_pay'),
    path('available_buses/new/', AvailableBusesCreateView.as_view(), name='available_buses_create'),
    path('available_buses/loaded/', LoadedBusInfoView.as_view(), name='available_buses_loaded'),
    path('available_buses/<int:pk>/update/', AvailableBusesUpdateView.as_view(), name='available_buses_update'),
    path('available_buses/<int:pk>/delete/', AvailableBusesDeleteView.as_view(), name='available_buses_delete'),
    path('transfer/', CompleteTransfers.as_view()),
    path('about/', views.about, name='reservations_about'),
    path('feedback/', views.feedback, name='feedback'),
]
