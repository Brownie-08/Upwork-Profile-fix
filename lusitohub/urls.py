"""lusitohub URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from wallets import admin_views
from core import media_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("", include("chat.urls")),
    path("", include("wallets.urls")),
    path("", include("profiles.urls")),
    path("", include("projects.urls")),
    path("", include("transport.urls")),
    path("", include("notifications.urls")),
    path(
        "admin/financial-overview/",
        admin_views.financial_overview,
        name="admin-financial-overview",
    ),
    # Favicon redirect to prevent 404 errors
    path(
        "favicon.ico",
        RedirectView.as_view(url=settings.STATIC_URL + "favicon.ico", permanent=True),
        name="favicon",
    ),
    # Default avatar endpoint
    path(
        "default-avatar/",
        media_views.serve_default_avatar,
        name="default-avatar",
    ),
    # Handle default.jpg requests
    path(
        "media/default.jpg",
        media_views.serve_default_jpg,
        name="default-jpg",
    ),
    # Fix for malformed Railway media URLs
    re_path(
        r'^web-production-\d+\.up\.railway\.app/media/(?P<path>.*)$',
        media_views.debug_media_request,
        name="railway-media-debug",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
