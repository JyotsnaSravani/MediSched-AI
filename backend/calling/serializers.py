"""
Serializers for calling app.
Sprint 3 - AI Calling System
"""

from rest_framework import serializers
from .models import CallLog, ManualCallbackTask


class CallLogSerializer(serializers.ModelSerializer):
    """Serializer for CallLog model."""
    
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_phone = serializers.CharField(source='patient.phone_number', read_only=True)
    appointment_id = serializers.IntegerField(source='appointment.id', read_only=True, allow_null=True)
    has_transcription = serializers.SerializerMethodField()
    transcription_id = serializers.SerializerMethodField()
    
    class Meta:
        model = CallLog
        fields = [
            'id',
            'patient',
            'patient_name',
            'patient_phone',
            'appointment',
            'appointment_id',
            'call_type',
            'attempt_number',
            'outcome',
            'twilio_call_sid',
            'twilio_recording_url',
            'duration',
            'transcription_status',
            'has_transcription',
            'transcription_id',
            'initiated_at',
            'completed_at',
            'notes',
        ]
        read_only_fields = [
            'id',
            'twilio_call_sid',
            'twilio_recording_url',
            'duration',
            'transcription_status',
            'initiated_at',
            'completed_at',
        ]
    
    def get_has_transcription(self, obj) -> bool:
        """Check if transcription exists."""
        try:
            return obj.transcription is not None
        except Exception:
            return False
    
    def get_transcription_id(self, obj):
        """Get transcription ID if exists."""
        try:
            return obj.transcription.id if obj.transcription else None
        except Exception:
            return None


class InitiateCallSerializer(serializers.Serializer):
    """Serializer for initiating AI call."""
    
    patient_id = serializers.IntegerField(required=True)
    appointment_id = serializers.IntegerField(required=False, allow_null=True)
    call_type = serializers.ChoiceField(
        choices=CallLog.CallType.choices,
        default=CallLog.CallType.GENERAL
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_patient_id(self, value):
        """Validate patient exists."""
        from patients.models import Patient
        if not Patient.objects.filter(id=value).exists():
            raise serializers.ValidationError("Patient not found")
        return value
    
    def validate_appointment_id(self, value):
        """Validate appointment exists if provided."""
        if value is not None:
            from scheduling.models import Appointment
            if not Appointment.objects.filter(id=value).exists():
                raise serializers.ValidationError("Appointment not found")
        return value


class ManualCallbackTaskSerializer(serializers.ModelSerializer):
    """Serializer for ManualCallbackTask model."""
    
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_phone = serializers.CharField(source='patient.phone_number', read_only=True)
    appointment_id = serializers.IntegerField(source='appointment.id', read_only=True, allow_null=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True, allow_null=True)
    completed_by_name = serializers.CharField(source='completed_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = ManualCallbackTask
        fields = [
            'id',
            'patient',
            'patient_name',
            'patient_phone',
            'appointment',
            'appointment_id',
            'status',
            'reason',
            'notes',
            'assigned_to',
            'assigned_to_name',
            'created_at',
            'completed_at',
            'completed_by',
            'completed_by_name',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'completed_at',
            'completed_by',
        ]


class CompleteCallbackTaskSerializer(serializers.Serializer):
    """Serializer for completing manual callback task."""
    
    notes = serializers.CharField(required=False, allow_blank=True)
