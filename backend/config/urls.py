"""
URL configuration for MediSched AI project.
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API v1 Endpoints
    path('api/v1/auth/', include('users.urls')),
    path('api/v1/patients/', include('patients.urls')),
    path('api/v1/doctors/', include('doctors.urls')),
    
    # Sprint 2+ endpoints
    path('api/v1/', include('scheduling.urls')),
    path('api/v1/calling/', include('calling.urls')),
    path('api/v1/transcriptions/', include('transcriptions.urls')),
    path('api/v1/reminders/', include('reminders.urls')),
    path('api/v1/analytics/', include('analytics.urls')),
    path('api/v1/sms/', include('sms.urls')),  # SMS messaging
]

# Customize admin site
admin.site.site_header = "Medshield AI Administration"
admin.site.site_title = "Medshield AI Admin"
admin.site.index_title = "Welcome to Medshield AI Administration"
