"""
ASGI config for lusitohub project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from chat.routing import websocket_urlpatterns as chat_websocket_urlpatterns
from notifications.routing import (
    websocket_urlpatterns as notifications_websocket_urlpatterns,
)
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lusitohub.settings")

# Combine WebSocket URL patterns from different apps
websocket_urlpatterns = chat_websocket_urlpatterns + notifications_websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
