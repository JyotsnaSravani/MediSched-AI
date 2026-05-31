"""
Serializers for transcriptions app.
Sprint 3 - Call Transcription System
"""

from rest_framework import serializers
from .models import Transcription


class TranscriptionSerializer(serializers.ModelSerializer):
    """Serializer for Transcription model."""
    
    patient_name = serializers.CharField(source='call_log.patient.full_name', read_only=True)
    patient_phone = serializers.CharField(source='call_log.patient.phone', read_only=True)
    call_log_id = serializers.IntegerField(source='call_log.id', read_only=True)
    appointment_id = serializers.IntegerField(source='appointment.id', read_only=True, allow_null=True)
    call_date = serializers.DateTimeField(source='call_log.initiated_at', read_only=True)
    call_duration = serializers.IntegerField(source='call_log.duration', read_only=True)
    recording_url = serializers.SerializerMethodField()
    last_edited_by_name = serializers.CharField(source='last_edited_by.get_full_name', read_only=True, allow_null=True)
    word_count = serializers.IntegerField(read_only=True)
    
    def get_recording_url(self, obj):
        """Get proxied recording URL."""
        if obj.call_log and obj.call_log.twilio_recording_url:
            # Return relative URL for proxy endpoint (works in both dev and production)
            return f"/api/v1/calling/logs/{obj.call_log.id}/recording/"
        return None
    
    class Meta:
        model = Transcription
        fields = [
            'id',
            'call_log',
            'call_log_id',
            'patient_name',
            'patient_phone',
            'appointment',
            'appointment_id',
            'text',
            'status',
            'whisper_model',
            'confidence_score',
            'is_edited',
            'last_edited_by',
            'last_edited_by_name',
            'last_edited_at',
            'call_date',
            'call_duration',
            'recording_url',
            'word_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
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
        ]


class TranscriptionUpdateSerializer(serializers.Serializer):
    """Serializer for updating transcription text."""
    
    text = serializers.CharField(required=True, allow_blank=False)
    
    def validate_text(self, value):
        """Validate text is not empty."""
        if not value.strip():
            raise serializers.ValidationError("Transcription text cannot be empty")
        return value
