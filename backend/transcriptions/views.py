"""
Views for transcriptions app.
Sprint 3 - Implements FR-CD-02 through FR-CD-06
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Transcription
from .serializers import TranscriptionSerializer, TranscriptionUpdateSerializer
from users.permissions import IsAdminOrStaff

import logging

logger = logging.getLogger(__name__)


class TranscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing transcriptions.
    Staff can view all transcriptions and edit text.
    Implements FR-CD-02 (staff editing) and FR-CD-03 (view transcriptions).
    
    Permissions:
    - List/Retrieve: Public access (AllowAny)
    - Create/Update/Delete: Staff only (IsAuthenticated + IsAdminOrStaff)
    """
    queryset = Transcription.objects.select_related(
        'call_log',
        'call_log__patient',
        'appointment',
        'last_edited_by'
    ).all()
    serializer_class = TranscriptionSerializer
    permission_classes = [IsAuthenticated, IsAdminOrStaff]  # Default for write operations
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'appointment', 'is_edited']
    search_fields = ['text', 'call_log__patient__first_name', 'call_log__patient__last_name']
    ordering_fields = ['created_at', 'updated_at', 'last_edited_at']
    ordering = ['-created_at']
    
    def get_permissions(self):
        """
        Allow public access for read operations (list, retrieve).
        Require authentication and staff permissions for write operations.
        """
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated(), IsAdminOrStaff()]
    
    def get_queryset(self):
        """Filter transcriptions with optional query params."""
        queryset = super().get_queryset()
        
        # Filter by patient
        patient_id = self.request.query_params.get('patient')
        if patient_id:
            queryset = queryset.filter(call_log__patient_id=patient_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset
    
    @action(detail=True, methods=['patch'], url_path='update-text')
    def update_text(self, request, pk=None):
        """
        Update transcription text.
        PATCH /api/v1/transcriptions/{id}/update-text/
        Implements FR-CD-02 (staff editing with tracking).
        """
        transcription = self.get_object()
        
        serializer = TranscriptionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        new_text = serializer.validated_data['text']
        
        # Update text with tracking
        transcription.update_text(new_text, request.user)
        
        logger.info(f"Transcription {pk} updated by {request.user.email}")
        
        # Return updated transcription
        response_serializer = self.get_serializer(transcription)
        return Response(response_serializer.data)
    
    def partial_update(self, request, *args, **kwargs):
        """
        Override partial_update to handle text updates with tracking.
        """
        instance = self.get_object()
        
        # If text is being updated, use update_text method
        if 'text' in request.data:
            new_text = request.data['text']
            instance.update_text(new_text, request.user)
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        
        # Otherwise, use default behavior
        return super().partial_update(request, *args, **kwargs)
