from django.urls import path
from .admin_views import financial_overview
from . import views

app_name = "wallets"  # Optional namespace for URL resolution

urlpatterns = [
    path(
        "admin/financial-overview/", financial_overview, name="admin_financial_overview"
    ),
    path(
        "wallet/", views.wallet_dashboard, name="wallet_dashboard"
    ),  # Aligned name with hyphen
    path("wallet/deposit/", views.deposit_funds, name="momo_deposit"),
    path("wallet/withdraw/", views.withdraw_funds, name="momo_withdrawal"),
    path(
        "wallet/transaction/<str:transaction_id>/",
        views.transaction_status_view,
        name="transaction_status",
    ),
    path("momo/callback/", views.momo_callback, name="momo_callback"),
]
