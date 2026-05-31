"""
URL configuration for analytics app.
Sprint 4 - Analytics & Reporting
"""

from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('dashboard/', views.dashboard_stats, name='dashboard-stats'),
    path('trends/', views.trends_data, name='trends'),
    path('export/appointments/', views.export_appointments_csv, name='export-appointments'),
    path('export/call-logs/', views.export_call_logs_csv, name='export-call-logs'),
    path('export/patients/', views.export_patients_csv, name='export-patients'),
    path('export/doctors/', views.export_doctors_csv, name='export-doctors'),
    path('export/all/', views.export_all_data_csv, name='export-all'),
]
