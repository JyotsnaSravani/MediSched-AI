"""
URL configuration for reminders app.
Sprint 4 - Automated Reminder System
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'reminders'

router = DefaultRouter()
router.register(r'', views.ReminderLogViewSet, basename='reminder')

urlpatterns = [
    path('', include(router.urls)),
]
