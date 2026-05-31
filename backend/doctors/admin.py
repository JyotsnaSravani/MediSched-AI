"""
Django admin configuration for Doctor and DoctorSlot models.
"""

from django.contrib import admin
from .models import Doctor, DoctorSlot


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    """
    Admin interface for Doctor model.
    """
    
    list_display = [
        'full_name', 'specialization', 'phone_number', 'email',
        'status', 'user', 'created_at'
    ]
    list_filter = ['status', 'specialization', 'created_at']
    search_fields = ['full_name', 'specialization', 'email', 'phone_number']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['full_name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('full_name', 'specialization', 'phone_number', 'email')
        }),
        ('Status & Access', {
            'fields': ('status', 'user')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DoctorSlot)
class DoctorSlotAdmin(admin.ModelAdmin):
    """
    Admin interface for DoctorSlot model.
    """
    
    list_display = [
        'doctor', 'slot_date', 'start_time', 'end_time', 'duration',
        'status', 'booked_patient', 'booked_at'
    ]
    list_filter = ['status', 'slot_date', 'duration', 'doctor']
    search_fields = ['doctor__full_name', 'booked_patient__full_name']
    readonly_fields = ['booked_at', 'created_at', 'updated_at']
    ordering = ['slot_date', 'start_time']
    
    fieldsets = (
        ('Slot Information', {
            'fields': ('doctor', 'slot_date', 'start_time', 'end_time', 'duration')
        }),
        ('Status & Booking', {
            'fields': ('status', 'booked_patient', 'booked_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
