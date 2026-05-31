"""
Views for scheduling app - Appointment management.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from .models import Appointment
from .serializers import (
    AppointmentSerializer,
    AppointmentDetailSerializer,
    CancelAppointmentSerializer
)
from users.permissions import IsAdmin, IsStaff


class AppointmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Appointment CRUD operations.
    
    List: GET /api/v1/appointments/
    Retrieve: GET /api/v1/appointments/{id}/
    Cancel: POST /api/v1/appointments/{id}/cancel/
    """
    
    queryset = Appointment.objects.select_related(
        'slot__doctor', 'patient', 'booked_by', 'cancelled_by'
    ).all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'patient', 'slot__doctor']
    search_fields = ['patient__full_name', 'slot__doctor__full_name']
    ordering_fields = ['booked_at', 'slot__slot_date']
    ordering = ['-booked_at']
    permission_classes = [IsStaff | IsAdmin]
    
    def get_serializer_class(self):
        """
        Return detailed serializer for retrieve action.
        """
        if self.action == 'retrieve':
            return AppointmentDetailSerializer
        return AppointmentSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Appointments are created via slot booking endpoint.
        """
        return Response(
            {
                'error': 'USE_SLOT_BOOKING',
                'message': 'Use POST /api/v1/doctors/{doctor_id}/slots/{slot_id}/book/ to create appointments',
                'status_code': 400
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @extend_schema(
        request=CancelAppointmentSerializer,
        responses={200: AppointmentSerializer}
    )
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_appointment(self, request, pk=None):
        """
        Cancel an appointment and revert slot to available.
        
        POST /api/v1/appointments/{id}/cancel/
        Body: {
            "reason": "Patient requested cancellation"
        }
        """
        appointment = self.get_object()
        
        if appointment.status == Appointment.Status.CANCELLED:
            return Response(
                {
                    'error': 'ALREADY_CANCELLED',
                    'message': 'Appointment is already cancelled',
                    'status_code': 400
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = CancelAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        reason = serializer.validated_data.get('reason', '')
        appointment.cancel(user=request.user, reason=reason)
        
        response_serializer = AppointmentSerializer(appointment)
        return Response(response_serializer.data)
