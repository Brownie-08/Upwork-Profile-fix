from django.urls import path
from . import views

app_name = 'transport'
urlpatterns = [
    path('transport/create/', views.TransportRequestCreateView.as_view(), name='create_job'),
    path('transport/<int:pk>/', views.TransportRequestDetailView.as_view(), name='job_detail'),
    path('transport/', views.TransportRequestDashboardView.as_view(), name='transport_dashboard'),
    path('transport/<int:job_id>/submit-bid/', views.submit_bid, name='submit_bid'),
    path('bid/<int:bid_id>/accept/', views.accept_bid, name='accept_bid'),
    path('contract/<int:contract_id>/confirm/', views.confirm_contract, name='confirm_contract'),
    path('contract-template/create/', views.TransportContractTemplateCreateView.as_view(), name='contract_template_create'),
]