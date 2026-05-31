"""
Views for Patient management.
Implements FR-PM-01 through FR-PM-08.
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import Patient
from .serializers import (
    PatientListSerializer,
    PatientDetailSerializer,
    PatientCreateUpdateSerializer
)
from users.permissions import IsAdminOrStaff, IsReadOnly


class PatientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Patient CRUD operations.
    
    List: GET /api/v1/patients/
    Create: POST /api/v1/patients/
    Retrieve: GET /api/v1/patients/{id}/
    Update: PUT /api/v1/patients/{id}/
    Delete: DELETE /api/v1/patients/{id}/
    
    Permissions:
    - Admin & Staff: Full CRUD access
    - Read-Only: View only
    """
    
    queryset = Patient.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['full_name', 'phone_number', 'email']
    ordering_fields = ['full_name', 'created_at', 'date_of_birth']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action == 'list':
            return PatientListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PatientCreateUpdateSerializer
        return PatientDetailSerializer
    
    def get_permissions(self):
        """
        FR-PM-08: Admin and Staff can create/edit, Read-Only can view.
        Allow public access to list/retrieve for calendar/booking system.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminOrStaff]
        elif self.action in ['list', 'retrieve']:
            # Allow public access for calendar/booking
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAdminOrStaff | IsReadOnly]
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """
        Save the user who created the patient record.
        Automatically trigger welcome call for appointment booking.
        """
        patient = serializer.save(created_by=self.request.user)
        
        # Trigger automatic welcome call for new patient
        self._trigger_welcome_call(patient)
    
    def _trigger_welcome_call(self, patient):
        """
        Automatically call new patient IMMEDIATELY to help them book their first appointment.
        Calls within seconds (not minutes)!
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Import here to avoid circular imports
            from calling.tasks import call_patient
            
            logger.info(f"Triggering IMMEDIATE welcome call for new patient: {patient.full_name} ({patient.phone_number})")
            
            # IMMEDIATE CALL - Execute synchronously (not queued)
            # This calls the patient within seconds instead of waiting for Celery
            try:
                # Try immediate call first
                result = call_patient(
                    patient_id=patient.id,
                    appointment_id=None,
                    call_type='GENERAL',
                    attempt=1
                )
                logger.info(f"IMMEDIATE welcome call executed: {result.get('status')}")
            except Exception as e:
                # Fallback to async if immediate fails
                logger.warning(f"Immediate call failed, falling back to async: {e}")
                call_patient.delay(
                    patient_id=patient.id,
                    appointment_id=None,
                    call_type='GENERAL',
                    attempt=1
                )
            
            logger.info(f"Welcome call triggered successfully for patient {patient.id}")
            
        except Exception as e:
            # Don't fail patient creation if call fails
            logger.error(f"Failed to trigger welcome call for patient {patient.id}: {str(e)}")
            # Continue - patient is still created successfully
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='search',
                description='Search by name, phone, or email',
                required=False,
                type=str
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        """
        FR-PM-05: List patients with search support.
        Search by name or phone number with partial match.
        
        Example: GET /api/v1/patients/?search=John
        """
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """
        FR-PM-07: Patient detail with appointment history and call logs.
        """
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'], url_path='welcome-call')
    def welcome_call(self, request, pk=None):
        """
        Manually trigger an IMMEDIATE welcome call for a patient.
        POST /api/v1/patients/{id}/welcome-call/
        
        Calls within SECONDS (not minutes)!
        
        Use this to:
        - Re-send welcome call if patient missed it
        - Call existing patients who haven't booked yet
        - Test the welcome call system
        """
        patient = self.get_object()
        
        try:
            from calling.tasks import call_patient
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(f"Manual IMMEDIATE welcome call triggered for patient: {patient.full_name}")
            
            # IMMEDIATE CALL - Execute synchronously
            result = call_patient(
                patient_id=patient.id,
                appointment_id=None,
                call_type='GENERAL',
                attempt=1
            )
            
            return Response({
                'status': 'success',
                'message': f'Welcome call executed immediately for {patient.full_name}',
                'call_status': result.get('status'),
                'call_log_id': result.get('call_log_id'),
                'patient_id': patient.id,
                'phone_number': patient.phone_number,
                'timing': 'IMMEDIATE (within seconds)'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='import')
    def import_patients(self, request):
        """
        Import patients from CSV file and automatically call them.
        POST /api/v1/patients/import/
        
        Accepts TWO CSV formats:
        
        Format 1 (Import format):
        Full Name,Phone Number,Email,Date of Birth,Gender,Assigned Doctor ID,Address,Medical Notes,Referring Doctor
        
        Format 2 (Export format - for re-importing exported data):
        ID,Name,Phone,Email,Age,Gender,Date of Birth,Assigned Doctor,Registered
        
        Returns:
        - success_count: Number of patients imported successfully
        - error_count: Number of rows that failed
        - errors: List of error messages for failed rows
        - patients: List of imported patient IDs
        """
        import csv
        import io
        import logging
        import re
        from datetime import datetime
        from django.db import transaction
        from doctors.models import Doctor
        
        logger = logging.getLogger(__name__)
        
        # Get uploaded file
        file = request.FILES.get('file')
        if not file:
            return Response({
                'status': 'error',
                'message': 'No file uploaded'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check file extension
        file_ext = file.name.split('.')[-1].lower()
        if file_ext != 'csv':
            return Response({
                'status': 'error',
                'message': 'Invalid file format. Please upload CSV (.csv) file'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Read CSV file
            file_content = file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(file_content))
            
            # Detect CSV format
            fieldnames = csv_reader.fieldnames
            is_export_format = 'Name' in fieldnames and 'Phone' in fieldnames and 'Assigned Doctor' in fieldnames
            is_import_format = 'Full Name' in fieldnames and 'Phone Number' in fieldnames and 'Assigned Doctor ID' in fieldnames
            
            if not is_export_format and not is_import_format:
                return Response({
                    'status': 'error',
                    'message': 'Invalid CSV format. Expected either:\n'
                              '1. Import format: Full Name, Phone Number, Date of Birth, Gender, Assigned Doctor ID\n'
                              '2. Export format: Name, Phone, Date of Birth, Gender, Assigned Doctor'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            success_count = 0
            error_count = 0
            errors = []
            imported_patients = []
            
            # Helper function to parse phone number
            def parse_phone(phone_str):
                """Parse phone number, handling scientific notation from Excel"""
                phone = str(phone_str).strip()
                
                # Handle scientific notation (e.g., 9.19949E+11)
                if 'E+' in phone.upper():
                    try:
                        phone = str(int(float(phone)))
                    except:
                        pass
                
                # Remove all non-digit characters except +
                phone = re.sub(r'[^\d+]', '', phone)
                
                # Add country code if missing
                if not phone.startswith('+'):
                    if len(phone) == 10:
                        phone = '+91' + phone  # India
                    elif len(phone) == 11:
                        phone = '+' + phone
                
                return phone
            
            # Helper function to parse date
            def parse_date(date_str):
                """Parse date in multiple formats"""
                date_str = str(date_str).strip()
                
                # Try YYYY-MM-DD format
                try:
                    return datetime.strptime(date_str, '%Y-%m-%d').date()
                except:
                    pass
                
                # Try DD-MM-YYYY format
                try:
                    return datetime.strptime(date_str, '%d-%m-%Y').date()
                except:
                    pass
                
                # Try MM/DD/YYYY format
                try:
                    return datetime.strptime(date_str, '%m/%d/%Y').date()
                except:
                    pass
                
                raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD, DD-MM-YYYY, or MM/DD/YYYY")
            
            # Helper function to get doctor by name or ID
            def get_doctor(doctor_str):
                """Get doctor by ID or name"""
                doctor_str = str(doctor_str).strip()
                
                # Try as ID first
                try:
                    doctor_id = int(doctor_str)
                    return Doctor.objects.get(id=doctor_id)
                except (ValueError, Doctor.DoesNotExist):
                    pass
                
                # Try as name (e.g., "Dr. Emily Rodriguez")
                doctor_name = doctor_str.replace('Dr. ', '').replace('Dr.', '').strip()
                try:
                    # Try exact match on full_name
                    return Doctor.objects.get(full_name__iexact=doctor_name)
                except Doctor.DoesNotExist:
                    # Try partial match on last name
                    name_parts = doctor_name.split()
                    if name_parts:
                        last_name = name_parts[-1]
                        doctors = Doctor.objects.filter(full_name__icontains=last_name)
                        if doctors.count() == 1:
                            return doctors.first()
                
                raise ValueError(f"Doctor not found: {doctor_str}")
            
            # Process each row
            for index, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
                # Skip empty rows
                if is_export_format:
                    if not row.get('Name') or not row.get('Phone'):
                        continue
                else:
                    if not row.get('Full Name') or not row.get('Phone Number'):
                        continue
                
                try:
                    with transaction.atomic():
                        # Parse fields based on format
                        if is_export_format:
                            full_name = row['Name'].strip()
                            phone_number = parse_phone(row['Phone'])
                            email = row.get('Email', '').strip()
                            date_of_birth = parse_date(row['Date of Birth'])
                            gender = row['Gender'].strip().upper()
                            doctor = get_doctor(row['Assigned Doctor'])
                        else:  # import format
                            full_name = row['Full Name'].strip()
                            phone_number = parse_phone(row['Phone Number'])
                            email = row.get('Email', '').strip()
                            date_of_birth = parse_date(row['Date of Birth'])
                            gender = row['Gender'].strip().upper()
                            doctor = get_doctor(row['Assigned Doctor ID'])
                        
                        # Validate gender
                        if gender not in ['MALE', 'FEMALE', 'OTHER']:
                            raise ValueError(f"Invalid gender: {gender}. Use MALE, FEMALE, or OTHER")
                        
                        # Check if patient already exists (by phone number)
                        existing = Patient.objects.filter(phone_number=phone_number).first()
                        if existing:
                            logger.info(f"Skipping duplicate patient: {full_name} ({phone_number})")
                            errors.append(f"Row {index}: Patient with phone {phone_number} already exists (ID: {existing.id})")
                            error_count += 1
                            continue
                        
                        # Create patient
                        patient_data = {
                            'full_name': full_name,
                            'phone_number': phone_number,
                            'date_of_birth': date_of_birth,
                            'gender': gender,
                            'assigned_doctor': doctor,
                            'created_by': request.user
                        }
                        
                        # Add optional fields
                        if email:
                            patient_data['email'] = email
                        
                        # Import format has additional optional fields
                        if not is_export_format:
                            if row.get('Address') and row['Address'].strip():
                                patient_data['address'] = row['Address'].strip()
                            if row.get('Medical Notes') and row['Medical Notes'].strip():
                                patient_data['medical_notes'] = row['Medical Notes'].strip()
                            if row.get('Referring Doctor') and row['Referring Doctor'].strip():
                                patient_data['referring_doctor'] = row['Referring Doctor'].strip()
                        
                        # Create patient
                        patient = Patient.objects.create(**patient_data)
                        
                        # Trigger welcome call
                        self._trigger_welcome_call(patient)
                        
                        imported_patients.append(patient.id)
                        success_count += 1
                        logger.info(f"Imported patient: {patient.full_name} (ID: {patient.id})")
                        
                except Exception as e:
                    error_count += 1
                    error_msg = f"Row {index}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(f"Failed to import row {index}: {e}")
            
            format_used = "Export format (re-import)" if is_export_format else "Import format"
            
            return Response({
                'status': 'success',
                'message': f'Import completed: {success_count} patients imported, {error_count} errors',
                'success_count': success_count,
                'error_count': error_count,
                'errors': errors,
                'patients': imported_patients,
                'format_detected': format_used
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return Response({
                'status': 'error',
                'message': f'Import failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
