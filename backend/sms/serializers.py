from rest_framework import serializers
from .models import SMSLog


class SMSLogSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    patient_phone = serializers.CharField(source='patient.phone_number', read_only=True)
    
    class Meta:
        model = SMSLog
        fields = [
            'id', 'patient', 'patient_name', 'patient_phone',
            'appointment', 'message_type', 'message_body',
            'status', 'twilio_sid', 'sent_at', 'delivered_at',
            'error_message'
        ]
        read_only_fields = ['id', 'sent_at', 'delivered_at', 'twilio_sid', 'status']


class SendSMSSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField(required=True)
    message_body = serializers.CharField(required=True, max_length=1600)
    message_type = serializers.ChoiceField(
        choices=SMSLog.MessageType.choices,
        default='GENERAL'
    )
    appointment_id = serializers.IntegerField(required=False, allow_null=True)
