"""
Serializers for Doctor and DoctorSlot models.
"""

from rest_framework import serializers
from .models import Doctor, DoctorSlot


class DoctorSerializer(serializers.ModelSerializer):
    """
    Serializer for Doctor model.
    """
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Doctor
        fields = [
            'id', 'full_name', 'specialization', 'phone_number', 'email',
            'status', 'status_display', 'user', 'user_email',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DoctorCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating doctors.
    Admin only for create. Admin or Doctor (own profile) for update.
    """
    
    # Add id to response
    id = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Doctor
        fields = [
            'id', 'full_name', 'specialization', 'phone_number', 'email',
            'status', 'user'
        ]
        read_only_fields = ['id']
    
    def validate_phone_number(self, value):
        """
        Automatically adds +91 prefix if not present.
        """
        # Automatically add +91 if not present
        if value and not value.startswith('+'):
            # Remove any leading zeros or spaces
            value = value.strip().lstrip('0')
            # Add +91 prefix
            value = f'+91{value}'
        
        return value
    
    def validate(self, attrs):
        """
        FR-DM-01: Validate required fields.
        """
        if self.instance is None:  # Creating new doctor
            required_fields = ['full_name', 'specialization', 'phone_number', 'email']
            for field in required_fields:
                if field not in attrs or not attrs[field]:
                    raise serializers.ValidationError({
                        field: f"{field.replace('_', ' ').title()} is required."
                    })
        
        return attrs


class DoctorSlotSerializer(serializers.ModelSerializer):
    """
    Serializer for DoctorSlot model.
    """
    
    doctor_name = serializers.CharField(source='doctor.full_name', read_only=True)
    doctor_specialization = serializers.CharField(source='doctor.specialization', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration_display = serializers.CharField(source='get_duration_display', read_only=True)
    patient_name = serializers.CharField(source='booked_patient.full_name', read_only=True)
    
    class Meta:
        model = DoctorSlot
        fields = [
            'id', 'doctor', 'doctor_name', 'doctor_specialization',
            'slot_date', 'start_time', 'end_time', 'duration', 'duration_display',
            'status', 'status_display', 'booked_patient', 'patient_name',
            'booked_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'booked_at', 'created_at', 'updated_at']


class SlotGenerateSerializer(serializers.Serializer):
    """
    Serializer for slot auto-generation endpoint.
    FR-DS-01, FR-DS-02: Generate slots from date, time range, and duration.
    """
    
    slot_date = serializers.DateField(required=True)
    start_time = serializers.TimeField(required=True)
    end_time = serializers.TimeField(required=True)
    duration = serializers.ChoiceField(
        choices=DoctorSlot.Duration.choices,
        required=True
    )
    
    def validate(self, attrs):
        """
        Validate that end_time is after start_time.
        """
        if attrs['end_time'] <= attrs['start_time']:
            raise serializers.ValidationError({
                'end_time': 'End time must be after start time.'
            })
        
        return attrs
