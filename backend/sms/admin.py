from django.contrib import admin
from .models import SMSLog


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'message_type', 'status', 'sent_at']
    list_filter = ['message_type', 'status', 'sent_at']
    search_fields = ['patient__full_name', 'message_body']
    readonly_fields = ['sent_at', 'delivered_at', 'twilio_sid']
    
    fieldsets = (
        ('Patient Info', {
            'fields': ('patient', 'appointment')
        }),
        ('Message', {
            'fields': ('message_type', 'message_body')
        }),
        ('Status', {
            'fields': ('status', 'twilio_sid', 'sent_at', 'delivered_at', 'error_message')
        }),
    )
