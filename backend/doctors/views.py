"""
Views for Doctor and DoctorSlot management.
Implements FR-DM-01 through FR-DM-03 and FR-DS-01 through FR-DS-08.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from django.utils import timezone

from .models import Doctor, DoctorSlot
from .serializers import (
    DoctorSerializer,
    DoctorCreateUpdateSerializer,
    DoctorSlotSerializer,
    SlotGenerateSerializer
)
from users.permissions import IsAdmin, IsAdminOrOwner


class DoctorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Doctor CRUD operations.
    
    List: GET /api/v1/doctors/ (Public access for calendar)
    Create: POST /api/v1/doctors/ (Admin only)
    Retrieve: GET /api/v1/doctors/{id}/ (Public access for calendar)
    Update: PUT /api/v1/doctors/{id}/ (Admin or Doctor own profile)
    Delete: DELETE /api/v1/doctors/{id}/ (Admin only)
    """
    
    queryset = Doctor.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'specialization']
    search_fields = ['full_name', 'specialization', 'email']
    ordering_fields = ['full_name', 'specialization', 'created_at']
    ordering = ['full_name']
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action in ['create', 'update', 'partial_update']:
            return DoctorCreateUpdateSerializer
        return DoctorSerializer
    
    def get_permissions(self):
        """
        FR-DM-02: Admin can create/delete. Admin or Doctor (own) can update.
        FR-DM-03: Doctor can edit own profile.
        Public can view doctors list and details for calendar/booking.
        """
        if self.action in ['create', 'destroy']:
            permission_classes = [IsAdmin]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsAdminOrOwner]
        elif self.action in ['list', 'retrieve']:
            # Allow public access to view doctors for calendar
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAdmin | IsAdminOrOwner]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        Return all doctors for all users.
        Doctor role can view all doctors but cannot edit others.
        """
        # All users can see all doctors
        return Doctor.objects.all()


class DoctorSlotViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DoctorSlot CRUD operations.
    
    List: GET /api/v1/doctors/{doctor_id}/slots/ (Public access for calendar)
    Create: POST /api/v1/doctors/{doctor_id}/slots/ (Admin/Staff only)
    Generate: POST /api/v1/doctors/{doctor_id}/slots/generate/ (Admin/Staff only)
    Block: PATCH /api/v1/doctors/{doctor_id}/slots/{id}/block/ (Admin/Staff only)
    """
    
    queryset = DoctorSlot.objects.select_related('doctor', 'booked_patient')
    serializer_class = DoctorSlotSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['slot_date', 'status', 'duration']
    ordering_fields = ['slot_date', 'start_time']
    ordering = ['slot_date', 'start_time']
    
    def get_permissions(self):
        """
        Allow public access to view slots for calendar.
        Require authentication for create/update/delete operations.
        """
        if self.action in ['list', 'retrieve']:
            # Allow public access to view slots for calendar
            permission_classes = [AllowAny]
        else:
            # Require authentication for modifications
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        Filter slots by doctor_id from URL.
        """
        doctor_id = self.kwargs.get('doctor_pk')
        if doctor_id:
            return self.queryset.filter(doctor_id=doctor_id)
        return self.queryset
    
    def perform_create(self, serializer):
        """
        Auto-fill doctor from URL when creating a slot.
        """
        doctor_id = self.kwargs.get('doctor_pk')
        serializer.save(doctor_id=doctor_id)
    
    @extend_schema(
        request=SlotGenerateSerializer,
        responses={201: DoctorSlotSerializer(many=True)}
    )
    @action(detail=False, methods=['post'], url_path='generate')
    def generate_slots(self, request, doctor_pk=None):
        """
        FR-DS-01, FR-DS-02: Auto-generate slots from date, time range, and duration.
        
        POST /api/v1/doctors/{doctor_id}/slots/generate/
        Body: {
            "slot_date": "2026-04-10",
            "start_time": "09:00:00",
            "end_time": "12:00:00",
            "duration": 30
        }
        """
        serializer = SlotGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        doctor = Doctor.objects.get(pk=doctor_pk)
        slot_date = serializer.validated_data['slot_date']
        start_time = serializer.validated_data['start_time']
        end_time = serializer.validated_data['end_time']
        duration = serializer.validated_data['duration']
        
        # Generate slots
        from .services import generate_doctor_slots
        
        try:
            slots = generate_doctor_slots(doctor, slot_date, start_time, end_time, duration)
            response_serializer = DoctorSlotSerializer(slots, many=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response(
                {
                    'error': 'SLOT_GENERATION_FAILED',
                    'message': str(e),
                    'status_code': 400
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        request=None,
        responses={200: DoctorSlotSerializer}
    )
    @action(detail=True, methods=['patch'], url_path='block')
    def block_slot(self, request, pk=None, doctor_pk=None):
        """
        Block a slot to prevent booking.
        
        PATCH /api/v1/doctors/{doctor_id}/slots/{id}/block/
        """
        slot = self.get_object()
        
        if slot.status == DoctorSlot.Status.BOOKED:
            return Response(
                {
                    'error': 'SLOT_ALREADY_BOOKED',
                    'message': 'Cannot block a booked slot',
                    'status_code': 400
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        slot.status = DoctorSlot.Status.BLOCKED
        slot.save()
        
        serializer = DoctorSlotSerializer(slot)
        return Response(serializer.data)
    
    @extend_schema(
        request=None,
        responses={200: DoctorSlotSerializer}
    )
    @action(detail=True, methods=['patch'], url_path='unblock')
    def unblock_slot(self, request, pk=None, doctor_pk=None):
        """
        Unblock a slot to make it available.
        
        PATCH /api/v1/doctors/{doctor_id}/slots/{id}/unblock/
        """
        slot = self.get_object()
        
        if slot.status != DoctorSlot.Status.BLOCKED:
            return Response(
                {
                    'error': 'SLOT_NOT_BLOCKED',
                    'message': 'Slot is not blocked',
                    'status_code': 400
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        slot.status = DoctorSlot.Status.AVAILABLE
        slot.save()
        
        serializer = DoctorSlotSerializer(slot)
        return Response(serializer.data)
    
    @extend_schema(
        request=None,
        responses={200: DoctorSlotSerializer}
    )
    @action(detail=True, methods=['post'], url_path='book')
    def book_slot(self, request, pk=None, doctor_pk=None):
        """
        Book a slot for a patient with concurrent booking prevention.
        
        POST /api/v1/doctors/{doctor_id}/slots/{id}/book/
        Body: {
            "patient": 1,
            "notes": "Regular checkup"
        }
        """
        from scheduling.serializers import BookSlotSerializer
        from scheduling.models import Appointment
        from patients.models import Patient
        from django.db import transaction
        
        serializer = BookSlotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        patient_id = serializer.validated_data['patient']
        notes = serializer.validated_data.get('notes', '')
        
        try:
            patient = Patient.objects.get(pk=patient_id)
        except Patient.DoesNotExist:
            return Response(
                {
                    'error': 'PATIENT_NOT_FOUND',
                    'message': 'Patient does not exist',
                    'status_code': 404
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Use select_for_update to prevent concurrent bookings
        with transaction.atomic():
            slot = DoctorSlot.objects.select_for_update().get(pk=pk)
            
            if slot.status != DoctorSlot.Status.AVAILABLE:
                return Response(
                    {
                        'error': 'SLOT_NOT_AVAILABLE',
                        'message': f'Slot is {slot.get_status_display()}',
                        'status_code': 409
                    },
                    status=status.HTTP_409_CONFLICT
                )
            
            # Update slot
            slot.status = DoctorSlot.Status.BOOKED
            slot.booked_patient = patient
            slot.booked_at = timezone.now()
            slot.save()
            
            # Create appointment
            appointment = Appointment.objects.create(
                slot=slot,
                patient=patient,
                notes=notes,
                booked_by=request.user,
                status=Appointment.Status.CONFIRMED
            )
        
        # Return updated slot
        response_serializer = DoctorSlotSerializer(slot)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
