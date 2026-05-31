"""
Serializers for Patient model.
"""

from rest_framework import serializers
from .models import Patient


class PatientListSerializer(serializers.ModelSerializer):
    """
    Serializer for patient list view (summary).
    Used in GET /api/v1/patients/
    """
    
    age = serializers.ReadOnlyField()
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)
    assigned_doctor_name = serializers.CharField(source='assigned_doctor.full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Patient
        fields = [
            'id', 'full_name', 'phone_number', 'date_of_birth', 'age',
            'gender', 'gender_display', 'email', 'assigned_doctor', 'assigned_doctor_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PatientDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for patient detail view with full information.
    Includes nested appointment history and call logs (Sprint 2+).
    Used in GET /api/v1/patients/{id}/
    """
    
    age = serializers.ReadOnlyField()
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    assigned_doctor_name = serializers.CharField(source='assigned_doctor.full_name', read_only=True, allow_null=True)
    
    # Nested relationships (will be populated in Sprint 2+)
    # appointments = serializers.SerializerMethodField()
    # call_logs = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = [
            'id', 'full_name', 'phone_number', 'date_of_birth', 'age',
            'gender', 'gender_display', 'email', 'address',
            'medical_notes', 'referring_doctor', 'assigned_doctor', 'assigned_doctor_name',
            'created_at', 'updated_at', 'created_by_name'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    # def get_appointments(self, obj):
    #     """Get patient's appointment history (Sprint 2)."""
    #     # Will be implemented in Sprint 2
    #     return []
    
    # def get_call_logs(self, obj):
    #     """Get patient's call interaction history (Sprint 3)."""
    #     # Will be implemented in Sprint 3
    #     return []


class PatientCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating patients.
    Validates required fields and duplicate phone numbers.
    """
    
    # Add id to response
    id = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Patient
        fields = [
            'id', 'full_name', 'phone_number', 'date_of_birth', 'gender',
            'email', 'address', 'medical_notes', 'referring_doctor', 'assigned_doctor'
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'assigned_doctor': {'required': True, 'allow_null': False}
        }
    
    def validate_phone_number(self, value):
        """
        FR-PM-04: Check for duplicate phone numbers.
        Automatically adds +91 prefix if not present.
        """
        # Automatically add +91 if not present
        if value and not value.startswith('+'):
            # Remove any leading zeros or spaces
            value = value.strip().lstrip('0')
            # Add +91 prefix
            value = f'+91{value}'
        
        # Get the instance being updated (if any)
        instance = self.instance
        
        # Check if another patient with this phone number exists
        existing = Patient.objects.filter(phone_number=value)
        
        # Exclude the current instance if updating
        if instance:
            existing = existing.exclude(pk=instance.pk)
        
        if existing.exists():
            existing_patient = existing.first()
            raise serializers.ValidationError(
                f"A patient with this phone number already exists: "
                f"{existing_patient.full_name} (ID: {existing_patient.id})"
            )
        
        return value
    
    def validate(self, attrs):
        """
        FR-PM-03: Validate required fields.
        Only validate required fields on creation, not on update.
        """
        # Only validate required fields if creating (not updating)
        if not self.instance:
            required_fields = ['full_name', 'phone_number', 'date_of_birth', 'gender', 'assigned_doctor']
            
            for field in required_fields:
                if field not in attrs or not attrs[field]:
                    raise serializers.ValidationError({
                        field: f"{field.replace('_', ' ').title()} is required."
                    })
        
        return attrs
