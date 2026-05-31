"""
Django admin configuration for reminders app.
Sprint 4 - Automated Reminder System
"""

from django.contrib import admin
from .models import ReminderLog


@admin.register(ReminderLog)
class ReminderLogAdmin(admin.ModelAdmin):
    """Admin interface for ReminderLog model."""
    
    list_display = [
        'id',
        'patient',
        'reminder_type',
        'channel',
        'delivery_status',
        'retry_count',
        'sent_at',
        'created_at'
    ]
    
    list_filter = [
        'reminder_type',
        'channel',
        'delivery_status',
        'created_at',
        'sent_at'
    ]
    
    search_fields = [
        'patient__first_name',
        'patient__last_name',
        'patient__phone',
        'message_text',
        'twilio_message_sid',
        'email_message_id'
    ]
    
    readonly_fields = [
        'id',
        'sent_at',
        'delivered_at',
        'twilio_message_sid',
        'email_message_id',
        'retry_count',
        'last_retry_at',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Reminder Information', {
            'fields': (
                'appointment',
                'patient',
                'reminder_type',
                'channel'
            )
        }),
        ('Message', {
            'fields': (
                'message_text',
            )
        }),
        ('Delivery Status', {
            'fields': (
                'delivery_status',
                'sent_at',
                'delivered_at'
            )
        }),
        ('External Services', {
            'fields': (
                'twilio_message_sid',
                'email_message_id'
            )
        }),
        ('Retry Information', {
            'fields': (
                'retry_count',
                'last_retry_at',
                'error_message'
            )
        }),
        ('Metadata', {
            'fields': (
                'created_at',
                'updated_at'
            )
        }),
    )
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
