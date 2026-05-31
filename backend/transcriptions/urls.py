"""
URL configuration for transcriptions app.
Sprint 3 - Call Transcription System
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'transcriptions'

router = DefaultRouter()
router.register(r'', views.TranscriptionViewSet, basename='transcription')

urlpatterns = [
    path('', include(router.urls)),
]
