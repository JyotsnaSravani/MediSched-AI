"""
Views for reminders app.
Sprint 4 - Automated Reminder System
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import ReminderLog
from .serializers import ReminderLogSerializer
from users.permissions import IsAdminOrStaff

import logging

logger = logging.getLogger(__name__)


class ReminderLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing reminder logs.
    Staff can view all reminders with filtering.
    """
    queryset = ReminderLog.objects.select_related(
        'patient',
        'appointment',
        'appointment__slot',
        'appointment__slot__doctor'
    ).all()
    serializer_class = ReminderLogSerializer
    permission_classes = [IsAuthenticated, IsAdminOrStaff]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        'patient',
        'appointment',
        'reminder_type',
        'channel',
        'delivery_status'
    ]
    search_fields = [
        'patient__first_name',
        'patient__last_name',
        'patient__phone',
        'message_text'
    ]
    ordering_fields = ['created_at', 'sent_at', 'delivered_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter reminders with optional query params."""
        queryset = super().get_queryset()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset
    
    @action(detail=False, methods=['get'], url_path='stats')
    def get_stats(self, request):
        """
        Get reminder statistics.
        GET /api/v1/reminders/stats/
        """
        from django.db.models import Count, Q
        
        stats = ReminderLog.objects.aggregate(
            total=Count('id'),
            sent=Count('id', filter=Q(delivery_status=ReminderLog.DeliveryStatus.SENT)),
            delivered=Count('id', filter=Q(delivery_status=ReminderLog.DeliveryStatus.DELIVERED)),
            failed=Count('id', filter=Q(delivery_status=ReminderLog.DeliveryStatus.FAILED)),
            pending=Count('id', filter=Q(delivery_status=ReminderLog.DeliveryStatus.PENDING)),
            # Count SMS: includes SMS channel + BOTH channel (sends SMS)
            sms=Count('id', filter=Q(channel=ReminderLog.Channel.SMS) | Q(channel=ReminderLog.Channel.BOTH)),
            # Count Email: includes EMAIL channel + BOTH channel (sends Email)
            email=Count('id', filter=Q(channel=ReminderLog.Channel.EMAIL) | Q(channel=ReminderLog.Channel.BOTH)),
        )
        
        return Response(stats)
