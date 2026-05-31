from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SMSLogViewSet

app_name = 'sms'

router = DefaultRouter()
router.register(r'', SMSLogViewSet, basename='sms')

urlpatterns = [
    path('', include(router.urls)),
]
