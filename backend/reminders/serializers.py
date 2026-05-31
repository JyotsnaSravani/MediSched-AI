"""
Serializers for reminders app.
Sprint 4 - Automated Reminder System
"""

from rest_framework import serializers
from .models import ReminderLog


class ReminderLogSerializer(serializers.ModelSerializer):
    """Serializer for ReminderLog model."""
    
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_phone = serializers.CharField(source='patient.phone', read_only=True)
    patient_email = serializers.CharField(source='patient.email', read_only=True)
    appointment_id = serializers.IntegerField(source='appointment.id', read_only=True)
    appointment_date = serializers.DateField(source='appointment.slot.slot_date', read_only=True)
    appointment_time = serializers.TimeField(source='appointment.slot.start_time', read_only=True)
    doctor_name = serializers.CharField(source='appointment.slot.doctor.full_name', read_only=True)
    
    class Meta:
        model = ReminderLog
        fields = [
            'id',
            'appointment',
            'appointment_id',
            'appointment_date',
            'appointment_time',
            'patient',
            'patient_name',
            'patient_phone',
            'patient_email',
            'doctor_name',
            'reminder_type',
            'channel',
            'delivery_status',
            'message_text',
            'sent_at',
            'delivered_at',
            'twilio_message_sid',
            'email_message_id',
            'retry_count',
            'last_retry_at',
            'error_message',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'delivery_status',
            'sent_at',
            'delivered_at',
            'twilio_message_sid',
            'email_message_id',
            'retry_count',
            'last_retry_at',
            'error_message',
            'created_at',
            'updated_at',
        ]
