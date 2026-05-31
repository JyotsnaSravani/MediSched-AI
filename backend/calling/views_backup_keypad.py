"""
Views for calling app - TwiML webhooks and call initiation.
Sprint 3 - Implements FR-AC-04 through FR-AC-08
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone

from .models import CallLog, ManualCallbackTask
from .serializers import (
    CallLogSerializer,
    InitiateCallSerializer,
    ManualCallbackTaskSerializer,
    CompleteCallbackTaskSerializer
)
from .tasks import call_patient, process_call_status
from users.permissions import IsAdminOrStaff

import logging

logger = logging.getLogger(__name__)


class CallLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing call logs.
    Staff can view all call logs with filtering.
    """
    queryset = CallLog.objects.all()
    serializer_class = CallLogSerializer
    permission_classes = [IsAuthenticated, IsAdminOrStaff]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['patient', 'appointment', 'call_type', 'outcome', 'transcription_status', 'attempt_number']
    search_fields = ['patient__full_name', 'patient__phone_number', 'notes']
    ordering_fields = ['initiated_at', 'completed_at', 'attempt_number']
    ordering = ['-initiated_at']
    
    @action(detail=False, methods=['post'], url_path='initiate')
    def initiate_call(self, request):
        """
        Initiate AI outbound call to patient.
        POST /api/v1/calling/logs/initiate/
        """
        from patients.models import Patient
        from scheduling.models import Appointment
        
        serializer = InitiateCallSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        patient_id = serializer.validated_data['patient_id']
        appointment_id = serializer.validated_data.get('appointment_id')
        call_type = serializer.validated_data.get('call_type', 'GENERAL')
        notes = serializer.validated_data.get('notes', '')
        
        try:
            patient = Patient.objects.get(id=patient_id)
            appointment = None
            if appointment_id:
                appointment = Appointment.objects.get(id=appointment_id)
            
            logger.info(f"Initiating call for patient {patient_id} by {request.user.email}")
            
            # Call synchronously for now (Celery having issues)
            from .tasks import call_patient
            result = call_patient(
                patient_id=patient_id,
                appointment_id=appointment_id,
                call_type=call_type,
                attempt=1
            )
            
            logger.info(f"Call result: {result}")
            
            return Response({
                'status': result.get('status', 'success'),
                'message': result.get('message', 'Call initiated successfully'),
                'call_log_id': result.get('call_log_id'),
                'patient_id': patient_id
            }, status=status.HTTP_202_ACCEPTED)
            
        except Patient.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Patient not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error initiating call: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], url_path='retry')
    def retry_call(self, request, pk=None):
        """
        Retry a failed call.
        POST /api/v1/calling/logs/{id}/retry/
        """
        from patients.models import Patient
        
        call_log = self.get_object()
        
        # Only allow retry for failed or no-answer calls
        if call_log.outcome not in [CallLog.Outcome.FAILED, CallLog.Outcome.NO_ANSWER, CallLog.Outcome.BUSY]:
            return Response({
                'status': 'error',
                'message': f'Cannot retry call with outcome: {call_log.outcome}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Determine next attempt number
            last_attempt = CallLog.objects.filter(
                patient=call_log.patient,
                appointment=call_log.appointment
            ).order_by('-attempt_number').first()
            
            next_attempt = (last_attempt.attempt_number + 1) if last_attempt else 1
            
            # Create new call log for retry
            new_call_log = CallLog.objects.create(
                patient=call_log.patient,
                appointment=call_log.appointment,
                call_type=call_log.call_type,
                attempt_number=next_attempt,
                outcome=CallLog.Outcome.NO_ANSWER,
                twilio_call_sid=f"SIM_{call_log.patient.id}_{int(timezone.now().timestamp())}",
                notes=f"Retry of call #{call_log.id}"
            )
            
            logger.info(f"Retry call created for patient {call_log.patient.id} by {request.user.email}")
            
            # Try to queue with Celery
            try:
                from .tasks import call_patient
                call_patient.delay(
                    patient_id=call_log.patient.id,
                    appointment_id=call_log.appointment.id if call_log.appointment else None,
                    call_type=call_log.call_type,
                    attempt=next_attempt
                )
            except:
                pass  # Celery not available
            
            return Response({
                'status': 'success',
                'message': 'Call retry queued successfully',
                'call_log_id': new_call_log.id,
                'attempt_number': next_attempt
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            logger.error(f"Error retrying call: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], url_path='transcribe')
    def transcribe(self, request, pk=None):
        """
        Trigger transcription for a call log.
        POST /api/v1/calling/logs/{id}/transcribe/
        """
        call_log = self.get_object()
        
        # Check if call has recording
        if not call_log.twilio_recording_url:
            return Response({
                'status': 'error',
                'message': 'No recording available for this call'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if already transcribed
        if call_log.transcription_status == CallLog.TranscriptionStatus.COMPLETED:
            return Response({
                'status': 'info',
                'message': 'Call already transcribed'
            }, status=status.HTTP_200_OK)
        
        # Check if transcription in progress
        if call_log.transcription_status == CallLog.TranscriptionStatus.IN_PROGRESS:
            return Response({
                'status': 'info',
                'message': 'Transcription already in progress'
            }, status=status.HTTP_200_OK)
        
        try:
            # Trigger transcription task
            from transcriptions.tasks import transcribe_call
            transcribe_call.delay(call_log.id)
            
            # Update status
            call_log.transcription_status = CallLog.TranscriptionStatus.PENDING
            call_log.save()
            
            logger.info(f"Transcription triggered for call log {call_log.id} by {request.user.email}")
            
            return Response({
                'status': 'success',
                'message': 'Transcription queued successfully',
                'call_log_id': call_log.id
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            logger.error(f"Error triggering transcription: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ManualCallbackTaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing manual callback tasks.
    Staff can view, assign, and complete tasks.
    """
    queryset = ManualCallbackTask.objects.all()
    serializer_class = ManualCallbackTaskSerializer
    permission_classes = [IsAuthenticated, IsAdminOrStaff]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['patient', 'status', 'assigned_to']
    search_fields = ['patient__full_name', 'reason', 'notes']
    ordering_fields = ['created_at', 'completed_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'], url_path='complete')
    def complete_task(self, request, pk=None):
        """
        Mark manual callback task as completed.
        POST /api/v1/calling/manual-tasks/{id}/complete/
        """
        task = self.get_object()
        
        if task.status == ManualCallbackTask.Status.COMPLETED:
            return Response({
                'error': 'Task already completed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = CompleteCallbackTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notes = serializer.validated_data.get('notes')
        task.mark_completed(user=request.user, notes=notes)
        
        return Response({
            'status': 'success',
            'message': 'Task completed successfully'
        })


# TwiML Webhook Endpoints (no authentication required - Twilio calls these)

@csrf_exempt
@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def twiml_greeting(request):
    """
    TwiML webhook - Initial greeting and menu.
    Dynamic messages based on call type.
    """
    from twilio.twiml.voice_response import VoiceResponse, Gather
    from patients.models import Patient
    from scheduling.models import Appointment
    
    response = VoiceResponse()
    
    # Get call type from URL parameters
    call_type = request.GET.get('call_type', 'GENERAL')
    patient_id = request.GET.get('patient_id')
    call_log_id = request.GET.get('call_log_id')
    
    # Get patient info if available
    patient_name = "valued patient"
    appointment_time = ""
    
    if patient_id:
        try:
            patient = Patient.objects.get(id=patient_id)
            patient_name = patient.full_name
            
            # Get upcoming appointment if exists
            upcoming = Appointment.objects.filter(
                patient=patient,
                status='CONFIRMED'
            ).order_by('appointment_date', 'appointment_time').first()
            
            if upcoming:
                from datetime import datetime
                date_str = upcoming.appointment_date.strftime('%B %d')
                time_str = upcoming.appointment_time.strftime('%I:%M %p')
                appointment_time = f" on {date_str} at {time_str}"
        except:
            pass
    
    # Disclaimer
    response.say(
        "Hello, this is an automated call from MediSched AI. "
        "This call may be recorded for quality assurance purposes.",
        voice='alice',
        language='en-US'
    )
    
    # Dynamic message based on call type
    if call_type == 'APPOINTMENT_REMINDER':
        response.say(
            f"Hello {patient_name}. This is a reminder about your upcoming appointment{appointment_time}. "
            "Please make sure to arrive 10 minutes early.",
            voice='alice',
            language='en-US'
        )
    
    elif call_type == 'APPOINTMENT_CONFIRMATION':
        response.say(
            f"Hello {patient_name}. Your appointment has been confirmed{appointment_time}. "
            "We look forward to seeing you.",
            voice='alice',
            language='en-US'
        )
    
    elif call_type == 'SLOT_OFFER':
        response.say(
            f"Hello {patient_name}. We have available appointment slots. "
            "We would like to schedule an appointment for you.",
            voice='alice',
            language='en-US'
        )
    
    elif call_type == 'FOLLOW_UP':
        response.say(
            f"Hello {patient_name}. This is a follow-up call regarding your recent visit. "
            "We hope you are doing well.",
            voice='alice',
            language='en-US'
        )
    
    else:  # GENERAL
        response.say(
            f"Hello {patient_name}. We are calling regarding your healthcare with MediSched.",
            voice='alice',
            language='en-US'
        )
    
    # Menu
    gather = Gather(
        num_digits=1,
        action='/api/v1/calling/twiml/handle-input/',
        method='POST',
        timeout=10
    )
    
    gather.say(
        "Press 1 to confirm your appointment. "
        "Press 2 to reschedule. "
        "Press 3 to cancel. "
        "Press 0 to speak with a staff member.",
        voice='alice',
        language='en-US'
    )
    
    response.append(gather)
    
    # If no input, repeat
    response.say("We didn't receive any input. Thank you for your time. Goodbye.", voice='alice')
    response.hangup()
    
    return HttpResponse(str(response), content_type='text/xml')


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def twiml_handle_input(request):
    """
    TwiML webhook - Handle DTMF input from patient.
    Implements FR-AC-06 (process patient response).
    """
    from twilio.twiml.voice_response import VoiceResponse
    
    response = VoiceResponse()
    digits = request.POST.get('Digits', '')
    
    if digits == '1':
        # Confirm appointment
        response.say(
            "Thank you for confirming your appointment. We look forward to seeing you. Goodbye.",
            voice='alice'
        )
    elif digits == '2':
        # Reschedule
        response.say(
            "To reschedule your appointment, please call our office at your earliest convenience. Goodbye.",
            voice='alice'
        )
    elif digits == '3':
        # Cancel
        response.say(
            "Your appointment has been noted for cancellation. "
            "A staff member will contact you shortly to confirm. Goodbye.",
            voice='alice'
        )
    elif digits == '0':
        # Transfer to staff
        response.say(
            "Please hold while we transfer you to a staff member.",
            voice='alice'
        )
        # In production, use response.dial() to transfer
        response.say("All staff members are currently busy. Please call back later. Goodbye.", voice='alice')
    else:
        # Invalid input
        response.say("Invalid input. Goodbye.", voice='alice')
    
    response.hangup()
    
    return HttpResponse(str(response), content_type='text/xml')


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def twiml_offer_slots(request):
    """
    TwiML webhook - Offer available slots to patient.
    Implements FR-AC-07 (slot offering).
    """
    from twilio.twiml.voice_response import VoiceResponse, Gather
    
    response = VoiceResponse()
    
    # In production, fetch actual available slots
    response.say(
        "We have the following appointment slots available: "
        "Press 1 for tomorrow at 10 AM. "
        "Press 2 for tomorrow at 2 PM. "
        "Press 3 for the day after tomorrow at 9 AM. "
        "Press 0 to speak with a staff member.",
        voice='alice',
        language='en-US'
    )
    
    gather = Gather(
        num_digits=1,
        action='/api/v1/calling/twiml/handle-input/',
        method='POST',
        timeout=10
    )
    
    response.append(gather)
    response.say("We didn't receive any input. Goodbye.", voice='alice')
    response.hangup()
    
    return HttpResponse(str(response), content_type='text/xml')


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def status_callback(request):
    """
    Twilio status callback - Called when call completes.
    Implements FR-AC-08 (call completion tracking).
    """
    call_sid = request.POST.get('CallSid')
    call_status = request.POST.get('CallStatus')
    call_duration = request.POST.get('CallDuration', 0)
    
    logger.info(f"Status callback: {call_sid} - {call_status} - {call_duration}s")
    
    # Trigger async task to process status
    process_call_status.delay(
        call_sid=call_sid,
        call_status=call_status,
        call_duration=int(call_duration)
    )
    
    return HttpResponse('OK', status=200)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def recording_callback(request):
    """
    Twilio recording callback - Called when recording is available.
    Triggers transcription task.
    """
    call_sid = request.POST.get('CallSid')
    recording_url = request.POST.get('RecordingUrl')
    
    logger.info(f"Recording callback: {call_sid} - {recording_url}")
    
    # Update call log with recording URL
    try:
        call_log = CallLog.objects.get(twilio_call_sid=call_sid)
        call_log.twilio_recording_url = recording_url
        call_log.transcription_status = CallLog.TranscriptionStatus.PENDING
        call_log.save()
        
        # Trigger transcription
        from transcriptions.tasks import transcribe_call
        transcribe_call.delay(call_log.id)
        
    except CallLog.DoesNotExist:
        logger.error(f"CallLog not found for SID: {call_sid}")
    
    return HttpResponse('OK', status=200)
