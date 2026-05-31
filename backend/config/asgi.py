"""
ASGI config for MediSched AI project.
Supports both HTTP and WebSocket protocols via Django Channels.
Enhanced with GPT-Realtime-2 support for real-time voice conversations.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Import WebSocket routing for GPT-Realtime-2
from calling.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    # WebSocket routing for real-time AI conversations (no auth required for Twilio)
    "websocket": URLRouter(websocket_urlpatterns),
})
