"""
WebSocket URL routing for real-time AI conversations
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Match WebSocket URL with or without query parameters
    re_path(r'ws/realtime-ai/', consumers.RealtimeAIConsumer.as_asgi()),
]
