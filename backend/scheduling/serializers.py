"""
Serializers for scheduling app.
"""

from rest_framework import serializers
from .models import Appointment
from doctors.serializers import DoctorSlotSerializer
from patients.serializers import PatientListSerializer


class AppointmentSerializer(serializers.ModelSerializer):
    """
    Serializer for Appointment model.
    """
    
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_phone = serializers.CharField(source='patient.phone_number', read_only=True)
    doctor_name = serializers.CharField(source='slot.doctor.full_name', read_only=True)
    doctor_specialization = serializers.CharField(source='slot.doctor.specialization', read_only=True)
    appointment_date = serializers.DateField(source='slot.slot_date', read_only=True)
    appointment_time = serializers.TimeField(source='slot.start_time', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    booked_by_name = serializers.CharField(source='booked_by.get_full_name', read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'slot', 'patient', 'patient_name', 'patient_phone',
            'doctor_name', 'doctor_specialization', 'appointment_date', 
            'appointment_time', 'status', 'status_display', 'notes',
            'booked_by', 'booked_by_name', 'booked_at', 'cancelled_at',
            'cancelled_by', 'cancellation_reason', 'updated_at'
        ]
        read_only_fields = ['id', 'booked_at', 'updated_at']


class AppointmentDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer with nested slot and patient info.
    """
    
    slot = DoctorSlotSerializer(read_only=True)
    patient = PatientListSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    booked_by_name = serializers.CharField(source='booked_by.get_full_name', read_only=True)
    cancelled_by_name = serializers.CharField(source='cancelled_by.get_full_name', read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'slot', 'patient', 'status', 'status_display', 'notes',
            'booked_by', 'booked_by_name', 'booked_at', 'cancelled_at',
            'cancelled_by', 'cancelled_by_name', 'cancellation_reason', 'updated_at'
        ]
        read_only_fields = ['id', 'booked_at', 'updated_at']


class BookSlotSerializer(serializers.Serializer):
    """
    Serializer for booking a slot.
    """
    
    patient = serializers.IntegerField(required=True, help_text="Patient ID")
    notes = serializers.CharField(required=False, allow_blank=True, help_text="Appointment notes")


class CancelAppointmentSerializer(serializers.Serializer):
    """
    Serializer for cancelling an appointment.
    """
    
    reason = serializers.CharField(required=False, allow_blank=True, help_text="Cancellation reason")
