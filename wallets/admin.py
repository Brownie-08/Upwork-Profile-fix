from django.contrib import admin
from django.urls import path
from .admin_views import financial_overview


class CustomAdminSite(admin.AdminSite):
    def get_urls(self):
        urls = super().get_urls()
        urls += [
            path("financial-overview/", financial_overview, name="financial_overview"),
        ]
        return urls


admin_site = CustomAdminSite(name="custom_admin")
