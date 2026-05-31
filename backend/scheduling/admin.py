"""
Django admin configuration for scheduling app.
"""

from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """
    Admin interface for Appointment model.
    """
    
    list_display = [
        'id', 'patient', 'get_doctor', 'get_appointment_date',
        'get_appointment_time', 'status', 'booked_at'
    ]
    
    list_filter = ['status', 'slot__slot_date', 'booked_at']
    
    search_fields = [
        'patient__full_name',
        'slot__doctor__full_name',
        'notes'
    ]
    
    readonly_fields = [
        'booked_at', 'booked_by', 'cancelled_at',
        'cancelled_by', 'updated_at'
    ]
    
    fieldsets = (
        ('Appointment Details', {
            'fields': ('slot', 'patient', 'status', 'notes')
        }),
        ('Booking Information', {
            'fields': ('booked_by', 'booked_at')
        }),
        ('Cancellation Information', {
            'fields': ('cancelled_by', 'cancelled_at', 'cancellation_reason'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_doctor(self, obj):
        """Get doctor name."""
        return obj.slot.doctor.full_name
    get_doctor.short_description = 'Doctor'
    get_doctor.admin_order_field = 'slot__doctor__full_name'
    
    def get_appointment_date(self, obj):
        """Get appointment date."""
        return obj.slot.slot_date
    get_appointment_date.short_description = 'Date'
    get_appointment_date.admin_order_field = 'slot__slot_date'
    
    def get_appointment_time(self, obj):
        """Get appointment time."""
        return f"{obj.slot.start_time} - {obj.slot.end_time}"
    get_appointment_time.short_description = 'Time'
    
    def has_add_permission(self, request):
        """
        Disable add in admin - appointments should be created via API.
        """
        return False
