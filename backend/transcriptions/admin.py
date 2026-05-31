"""
Django admin configuration for transcriptions app.
Sprint 3 - Call Transcription System
"""

from django.contrib import admin
from .models import Transcription


@admin.register(Transcription)
class TranscriptionAdmin(admin.ModelAdmin):
    """Admin interface for Transcription model."""
    
    list_display = [
        'id',
        'get_patient_name',
        'status',
        'word_count',
        'is_edited',
        'last_edited_by',
        'created_at'
    ]
    
    list_filter = [
        'status',
        'is_edited',
        'whisper_model',
        'created_at',
        'last_edited_at'
    ]
    
    search_fields = [
        'text',
        'call_log__patient__first_name',
        'call_log__patient__last_name',
        'call_log__twilio_call_sid'
    ]
    
    readonly_fields = [
        'id',
        'call_log',
        'status',
        'whisper_model',
        'confidence_score',
        'is_edited',
        'last_edited_by',
        'last_edited_at',
        'created_at',
        'updated_at',
        'word_count'
    ]
    
    fieldsets = (
        ('Call Information', {
            'fields': (
                'call_log',
                'appointment'
            )
        }),
        ('Transcription Content', {
            'fields': (
                'text',
                'status',
                'word_count'
            )
        }),
        ('Whisper API Details', {
            'fields': (
                'whisper_model',
                'confidence_score'
            )
        }),
        ('Editing History', {
            'fields': (
                'is_edited',
                'last_edited_by',
                'last_edited_at'
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
    
    def get_patient_name(self, obj):
        """Get patient name from call log."""
        return obj.call_log.patient.full_name
    get_patient_name.short_description = 'Patient'
    get_patient_name.admin_order_field = 'call_log__patient__last_name'
