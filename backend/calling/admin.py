"""
Django admin configuration for calling app.
Sprint 3 - AI Calling System
"""

from django.contrib import admin
from .models import CallLog, ManualCallbackTask


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    """Admin interface for CallLog model."""
    
    list_display = [
        'id',
        'patient',
        'call_type',
        'attempt_number',
        'outcome',
        'transcription_status',
        'initiated_at',
        'duration'
    ]
    
    list_filter = [
        'call_type',
        'outcome',
        'transcription_status',
        'attempt_number',
        'initiated_at'
    ]
    
    search_fields = [
        'patient__first_name',
        'patient__last_name',
        'patient__phone',
        'twilio_call_sid',
        'notes'
    ]
    
    readonly_fields = [
        'id',
        'twilio_call_sid',
        'twilio_recording_url',
        'duration',
        'transcription_status',
        'initiated_at',
        'completed_at'
    ]
    
    fieldsets = (
        ('Call Information', {
            'fields': (
                'patient',
                'appointment',
                'call_type',
                'attempt_number',
                'outcome'
            )
        }),
        ('Twilio Details', {
            'fields': (
                'twilio_call_sid',
                'twilio_recording_url',
                'duration'
            )
        }),
        ('Transcription', {
            'fields': (
                'transcription_status',
            )
        }),
        ('Metadata', {
            'fields': (
                'initiated_at',
                'completed_at',
                'notes'
            )
        }),
    )
    
    date_hierarchy = 'initiated_at'
    ordering = ['-initiated_at']


@admin.register(ManualCallbackTask)
class ManualCallbackTaskAdmin(admin.ModelAdmin):
    """Admin interface for ManualCallbackTask model."""
    
    list_display = [
        'id',
        'patient',
        'status',
        'assigned_to',
        'created_at',
        'completed_at'
    ]
    
    list_filter = [
        'status',
        'assigned_to',
        'created_at',
        'completed_at'
    ]
    
    search_fields = [
        'patient__first_name',
        'patient__last_name',
        'reason',
        'notes'
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'completed_at',
        'completed_by'
    ]
    
    fieldsets = (
        ('Task Information', {
            'fields': (
                'patient',
                'appointment',
                'status',
                'reason',
                'notes'
            )
        }),
        ('Assignment', {
            'fields': (
                'assigned_to',
            )
        }),
        ('Completion', {
            'fields': (
                'completed_at',
                'completed_by'
            )
        }),
        ('Metadata', {
            'fields': (
                'created_at',
            )
        }),
    )
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
