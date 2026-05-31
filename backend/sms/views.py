from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import SMSLog
from .serializers import SMSLogSerializer, SendSMSSerializer
from .tasks import send_sms
from users.permissions import IsAdminOrStaff

import logging

logger = logging.getLogger(__name__)


class SMSLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing SMS logs"""
    queryset = SMSLog.objects.all()
    serializer_class = SMSLogSerializer
    permission_classes = [IsAuthenticated, IsAdminOrStaff]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['patient', 'message_type', 'status']
    search_fields = ['patient__full_name', 'message_body']
    ordering_fields = ['sent_at']
    ordering = ['-sent_at']
    
    @action(detail=False, methods=['post'], url_path='send')
    def send_sms(self, request):
        """
        Send SMS message to patient
        POST /api/v1/sms/send/
        """
        serializer = SendSMSSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        patient_id = serializer.validated_data['patient_id']
        message_body = serializer.validated_data['message_body']
        message_type = serializer.validated_data.get('message_type', 'GENERAL')
        appointment_id = serializer.validated_data.get('appointment_id')
        
        try:
            # Send SMS synchronously for now
            result = send_sms(
                patient_id=patient_id,
                message_body=message_body,
                message_type=message_type,
                appointment_id=appointment_id
            )
            
            if result['status'] == 'success':
                return Response({
                    'status': 'success',
                    'message': 'SMS sent successfully',
                    'sms_log_id': result.get('sms_log_id'),
                    'twilio_sid': result.get('twilio_sid')
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'error',
                    'message': result.get('message', 'Failed to send SMS')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
