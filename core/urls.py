from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("trust-safety/", views.trust_safety_view, name="trust_safety"),
    path("pricing/", views.pricing_view, name="pricing"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="core/login.html"),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(template_name="core/logout.html"),
        name="logout",
    ),
    path("terms/", views.terms_view, name="terms"),
    path("cookie/", views.cookie_view, name="cookie"),
    path("privacy/", views.privacy_view, name="privacy"),
    path("support/", views.support_view, name="support"),
    path("api/csrf-token/", views.refresh_csrf_token, name="refresh_csrf_token"),
]
