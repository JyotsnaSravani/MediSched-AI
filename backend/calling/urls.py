"""
URL configuration for calling app.
Sprint 3 - AI Calling System
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'calling'

router = DefaultRouter()
router.register(r'logs', views.CallLogViewSet, basename='call-log')
router.register(r'manual-tasks', views.ManualCallbackTaskViewSet, basename='manual-task')

urlpatterns = [
    # REST API endpoints
    path('', include(router.urls)),
    
    # TwiML webhook endpoints (called by Twilio)
    path('twiml-conversational/', views.twiml_conversational, name='twiml-conversational'),
    path('twiml/greeting/', views.twiml_greeting, name='twiml-greeting'),
    path('twiml/handle-input/', views.twiml_handle_input, name='twiml-handle-input'),
    path('twiml/offer-slots/', views.twiml_offer_slots, name='twiml-offer-slots'),
    
    # Callback endpoints
    path('status-callback/', views.status_callback, name='status-callback'),
    path('recording-callback/', views.recording_callback, name='recording-callback'),
]
