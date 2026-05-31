"""
URL configuration for patients app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'patients'

router = DefaultRouter()
router.register(r'', views.PatientViewSet, basename='patient')

urlpatterns = [
    path('', include(router.urls)),
]
