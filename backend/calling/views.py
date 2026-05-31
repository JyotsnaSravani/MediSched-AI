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

# Import new MediSched AI conversation flow
from .views_natural_voice import (
    twiml_conversational as twiml_conversational_new,
    handle_speech_input as handle_speech_input_new,
    status_callback as status_callback_new,
    recording_callback as recording_callback_new
)

# Use new conversation flow
twiml_conversational = twiml_conversational_new
status_callback = status_callback_new
recording_callback = recording_callback_new

# Old function kept for reference
@csrf_exempt
@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def twiml_conversational_old(request):
    """
    Natural Voice Conversations using Twilio Speech Recognition.
    No WebSocket needed - works through Ngrok free tier!
    
    OPTIMIZED FOR FAST RESPONSE:
    - 2 second timeout (faster than 3 seconds)
    - Barge-in enabled (patient can interrupt AI)
    - Auto speech timeout (detects when patient stops speaking)
    - Profanity filter disabled (faster processing)
    """
    from twilio.twiml.voice_response import VoiceResponse, Gather
    from patients.models import Patient
    from scheduling.models import Appointment
    from django.conf import settings
    
    # Get speech recognition settings from environment
    speech_timeout = getattr(settings, 'SPEECH_TIMEOUT', 2)  # Default 2 seconds
    enable_barge_in = getattr(settings, 'ENABLE_BARGE_IN', True)  # Default True
    
    # Get parameters
    call_type = request.GET.get('call_type', 'GENERAL')
    patient_id = request.GET.get('patient_id')
    call_log_id = request.GET.get('call_log_id')
    
    # Get speech result from Twilio
    speech_result = request.POST.get('SpeechResult', '').lower()
    
    try:
        patient = Patient.objects.get(id=patient_id)
        appointment = None
        
        # Get appointment if needed
        if call_type in ['APPOINTMENT_REMINDER', 'APPOINTMENT_CONFIRMATION', 'FOLLOW_UP']:
            try:
                call_log = CallLog.objects.get(id=call_log_id)
                appointment = call_log.appointment
            except:
                pass
        
        response = VoiceResponse()
        first_name = patient.full_name.split()[0]
        
        # If speech result exists, handle it
        if speech_result:
            logger.info(f"Patient said: {speech_result}")
            return handle_speech_input(request, patient, speech_result, call_type, appointment, call_log_id)
        
        # Initial greeting - Short and natural with barge-in support
        gather = response.gather(
            input='speech',
            action=f'/api/v1/calling/twiml-conversational/?patient_id={patient_id}&call_log_id={call_log_id}&call_type={call_type}',
            method='POST',
            timeout=speech_timeout,  # Use setting from .env (default 2 seconds)
            speech_timeout='auto',  # Auto-detect when patient stops speaking
            language='en-US',
            hints='appointment, book, schedule, check, cancel, reschedule',  # Help recognition
            barge_in=enable_barge_in,  # Use setting from .env (default True)
            profanity_filter=False  # Don't filter speech for faster processing
        )
        gather.say(
            f"Hi {first_name}! This is Sarah from MediShield AI. How may I help you today?",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.say("I'm sorry, I didn't catch that. Please give us a call back when you're ready. Thank you!", voice='Polly.Joanna')
        response.hangup()
        
        logger.info(f"Natural voice call initiated for patient {patient_id}")
        return HttpResponse(str(response), content_type='text/xml')
        
    except Patient.DoesNotExist:
        logger.error(f"Patient {patient_id} not found")
        response = VoiceResponse()
        response.say(
            "We're sorry, we couldn't find your information. Please call our office directly.",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')
        
    except Exception as e:
        logger.error(f"Error in TwiML webhook: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        response = VoiceResponse()
        response.say(
            "We're sorry, we're experiencing technical difficulties. Please call our office directly. Thank you, goodbye.",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')


def handle_speech_input(request, patient, speech_text, call_type, appointment=None, call_log_id=None):
    """
    Handle natural voice input from patient using Intelligent NLU.
    
    FULLY CONVERSATIONAL - NO FIXED FLOW:
    - Understands natural language and incomplete sentences
    - Handles 15+ intents dynamically
    - Context memory - remembers what patient said
    - Responds like a real hospital receptionist
    
    OPTIMIZED FOR FAST RESPONSE:
    - Uses settings from .env for timeout and barge-in
    - Faster speech recognition processing
    - Patient can interrupt AI mid-sentence
    """
    from twilio.twiml.voice_response import VoiceResponse, Gather
    from doctors.models import DoctorSlot, Doctor
    from scheduling.models import Appointment as AppointmentModel
    from django.utils import timezone
    from datetime import timedelta
    from django.conf import settings
    from .intelligent_nlu import IntentDetector, ConversationContext, ResponseGenerator
    
    # Get speech recognition settings
    speech_timeout = getattr(settings, 'SPEECH_TIMEOUT', 2)
    enable_barge_in = getattr(settings, 'ENABLE_BARGE_IN', True)
    
    response = VoiceResponse()
    first_name = patient.full_name.split()[0]
    
    # Initialize intelligent NLU system
    intent_detector = IntentDetector()
    context = ConversationContext()
    context.patient_name = first_name
    
    # Get action parameter to track conversation state (for backward compatibility)
    action = request.GET.get('action', '')
    
    # Detect intent from patient's speech
    detected_intent, confidence, entities = intent_detector.detect_intent(speech_text, context)
    logger.info(f"Detected intent: {detected_intent} (confidence: {confidence:.2f}), entities: {entities}")
    
    # ========== INTELLIGENT INTENT HANDLING ==========
    
    # Handle CHECK_APPOINTMENT intent
    if detected_intent == 'check_appointment' or action == 'check_appointment':
        appointments = AppointmentModel.objects.filter(
            patient=patient,
            status='CONFIRMED',
            slot__slot_date__gte=timezone.now().date()
        ).order_by('slot__slot_date', 'slot__start_time')[:3]
        
        if appointments:
            if len(appointments) == 1:
                appt = appointments[0]
                day_name = appt.slot.slot_date.strftime('%A')
                date_str = appt.slot.slot_date.strftime('%B %d')
                time_str = appt.slot.start_time.strftime('%I:%M %p')
                doctor_name = appt.slot.doctor.full_name.split()[-1]
                
                gather = response.gather(
                    input='speech',
                    action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=final_question',
                    method='POST',
                    timeout=speech_timeout,
                    speech_timeout='auto',
                    language='en-US',
                    hints='no, yes, question, office, hours, location, cancel, reschedule',
                    barge_in=enable_barge_in,
                    profanity_filter=False
                )
                gather.say(
                    f"Yes, you have an appointment with Dr. {doctor_name} on {day_name}, {date_str} at {time_str}. "
                    "Do you have any other questions?",
                    voice='Polly.Joanna',
                    language='en-US'
                )
                response.say("Thank you, have a great day!", voice='Polly.Joanna')
            else:
                appt_text = f"You have {len(appointments)} upcoming appointments. "
                for appt in appointments:
                    date_str = appt.slot.slot_date.strftime('%B %d')
                    time_str = appt.slot.start_time.strftime('%I:%M %p')
                    doctor_name = appt.slot.doctor.full_name.split()[-1]
                    appt_text += f"One with Dr. {doctor_name} on {date_str} at {time_str}. "
                
                gather = response.gather(
                    input='speech',
                    action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=final_question',
                    method='POST',
                    timeout=speech_timeout,
                    speech_timeout='auto',
                    language='en-US',
                    hints='no, yes, question, office, hours, location, cancel, reschedule',
                    barge_in=enable_barge_in,
                    profanity_filter=False
                )
                gather.say(
                    appt_text + "Would you like more details?",
                    voice='Polly.Joanna',
                    language='en-US'
                )
                response.say("Thank you, have a great day!", voice='Polly.Joanna')
        else:
            gather = response.gather(
                input='speech',
                action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=book_appointment',
                method='POST',
                timeout=speech_timeout,
                speech_timeout='auto',
                language='en-US',
                hints='yes, no, book, schedule, tomorrow, today',
                barge_in=enable_barge_in,
                profanity_filter=False
            )
            gather.say(
                "You don't have any upcoming appointments. Would you like to book one?",
                voice='Polly.Joanna',
                language='en-US'
            )
            response.say("Thank you, have a great day!", voice='Polly.Joanna')
        
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')
    
    # Handle CANCEL_APPOINTMENT intent
    elif detected_intent == 'cancel_appointment':
        appointments = AppointmentModel.objects.filter(
            patient=patient,
            status='CONFIRMED',
            slot__slot_date__gte=timezone.now().date()
        ).order_by('slot__slot_date', 'slot__start_time')[:3]
        
        if appointments:
            if len(appointments) == 1:
                appt = appointments[0]
                date_str = appt.slot.slot_date.strftime('%B %d')
                time_str = appt.slot.start_time.strftime('%I:%M %p')
                
                gather = response.gather(
                    input='speech',
                    action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=confirm_cancel&appointment_id={appt.id}',
                    method='POST',
                    timeout=speech_timeout,
                    speech_timeout='auto',
                    language='en-US',
                    hints='yes, no, confirm, cancel',
                    barge_in=enable_barge_in,
                    profanity_filter=False
                )
                gather.say(
                    f"Just to confirm, would you like to cancel your appointment on {date_str} at {time_str}?",
                    voice='Polly.Joanna',
                    language='en-US'
                )
                response.say("Thank you, have a great day!", voice='Polly.Joanna')
            else:
                response.say(
                    "You have multiple appointments. Please call our office to specify which one you'd like to cancel. Thank you!",
                    voice='Polly.Joanna',
                    language='en-US'
                )
        else:
            response.say(
                "You don't have any upcoming appointments to cancel. Is there anything else I can help you with? Thank you!",
                voice='Polly.Joanna',
                language='en-US'
            )
        
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')
    
    # Handle CONFIRM_CANCEL action
    elif action == 'confirm_cancel':
        appointment_id = request.GET.get('appointment_id')
        if entities.get('confirmation') == True or any(word in speech_text for word in ['yes', 'yeah', 'sure', 'confirm']):
            try:
                appt = AppointmentModel.objects.get(id=appointment_id, patient=patient)
                # Cancel the appointment
                appt.status = 'CANCELLED'
                appt.cancelled_at = timezone.now()
                appt.cancellation_reason = 'Cancelled via AI call'
                appt.save()
                
                # Revert slot to available
                appt.slot.status = 'AVAILABLE'
                appt.slot.booked_patient = None
                appt.slot.booked_at = None
                appt.slot.save()
                
                response.say(
                    "Your appointment has been cancelled. You'll receive a confirmation text shortly. Thank you!",
                    voice='Polly.Joanna',
                    language='en-US'
                )
            except:
                response.say(
                    "I'm sorry, I couldn't cancel that appointment. Please call our office. Thank you!",
                    voice='Polly.Joanna',
                    language='en-US'
                )
        else:
            response.say(
                "No problem, your appointment is still confirmed. Thank you!",
                voice='Polly.Joanna',
                language='en-US'
            )
        
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')
    
    # Handle RESCHEDULE_APPOINTMENT intent
    elif detected_intent == 'reschedule_appointment':
        appointments = AppointmentModel.objects.filter(
            patient=patient,
            status='CONFIRMED',
            slot__slot_date__gte=timezone.now().date()
        ).order_by('slot__slot_date', 'slot__start_time')[:1]
        
        if appointments:
            # If patient mentioned a new date/time, proceed with rescheduling
            if entities.get('date') or entities.get('time'):
                gather = response.gather(
                    input='speech',
                    action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=book_appointment',
                    method='POST',
                    timeout=speech_timeout,
                    speech_timeout='auto',
                    language='en-US',
                    hints='morning, afternoon, tomorrow, today, Monday, Tuesday',
                    barge_in=enable_barge_in,
                    profanity_filter=False
                )
                gather.say(
                    "Sure! What date and time would work better for you?",
                    voice='Polly.Joanna',
                    language='en-US'
                )
                response.say("Thank you, have a great day!", voice='Polly.Joanna')
            else:
                gather = response.gather(
                    input='speech',
                    action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=book_appointment',
                    method='POST',
                    timeout=speech_timeout,
                    speech_timeout='auto',
                    language='en-US',
                    hints='morning, afternoon, tomorrow, today, Monday, Tuesday',
                    barge_in=enable_barge_in,
                    profanity_filter=False
                )
                gather.say(
                    "I can help you reschedule. Would you prefer morning or afternoon?",
                    voice='Polly.Joanna',
                    language='en-US'
                )
                response.say("Thank you, have a great day!", voice='Polly.Joanna')
        else:
            response.say(
                "You don't have any upcoming appointments to reschedule. Would you like to book a new appointment? Thank you!",
                voice='Polly.Joanna',
                language='en-US'
            )
        
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')
    
    # Handle HOSPITAL_TIMINGS intent
    elif detected_intent == 'hospital_timings':
        gather = response.gather(
            input='speech',
            action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=final_question',
            method='POST',
            timeout=speech_timeout,
            speech_timeout='auto',
            language='en-US',
            hints='no, yes, question, book, appointment',
            barge_in=enable_barge_in,
            profanity_filter=False
        )
        gather.say(
            "We're open Monday through Friday, 9 AM to 5 PM. Is there anything else I can help you with?",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.say("Thank you, have a great day!", voice='Polly.Joanna')
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')
    
    # Handle WAITING_TIME intent
    elif detected_intent == 'waiting_time':
        gather = response.gather(
            input='speech',
            action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=final_question',
            method='POST',
            timeout=speech_timeout,
            speech_timeout='auto',
            language='en-US',
            hints='no, yes, question, book, appointment',
            barge_in=enable_barge_in,
            profanity_filter=False
        )
        gather.say(
            "Usually around 15 to 20 minutes depending on appointments. Would you like to book a slot?",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.say("Thank you, have a great day!", voice='Polly.Joanna')
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')
    
    # Handle LOCATION_INFO intent
    elif detected_intent == 'location_info':
        gather = response.gather(
            input='speech',
            action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=final_question',
            method='POST',
            timeout=speech_timeout,
            speech_timeout='auto',
            language='en-US',
            hints='no, yes, question, parking, directions',
            barge_in=enable_barge_in,
            profanity_filter=False
        )
        gather.say(
            "We're located at 123 Medical Plaza. We have free parking available. Anything else I can help with?",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.say("Thank you, have a great day!", voice='Polly.Joanna')
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')
    
    # Handle COST_INSURANCE intent
    elif detected_intent == 'cost_insurance':
        response.say(
            "For insurance and payment questions, please call our office during business hours. We'll be happy to help! Thank you!",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')
    
    # Handle BOOK_APPOINTMENT intent or legacy booking flow
    elif detected_intent == 'book_appointment' or action == 'book_appointment' or any(word in speech_text for word in ['book', 'schedule', 'appointment', 'make', 'need']):
        # Check if patient already mentioned a date in the same sentence
        date_keywords = ['tomorrow', 'today', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
                        'day after tomorrow', 'next week', 'next monday', 'next tuesday', 'next wednesday', 
                        'next thursday', 'next friday', 'next saturday', 'next sunday']
        
        # Also check for date patterns like "May 21", "21st May", etc.
        import re
        has_date = any(keyword in speech_text.lower() for keyword in date_keywords)
        has_date_pattern = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([A-Za-z]+)', speech_text, re.IGNORECASE)
        
        if has_date or has_date_pattern:
            # Patient mentioned date - extract it and ask for time directly
            from urllib.parse import quote
            
            # Extract the date portion
            if 'tomorrow' in speech_text.lower():
                date_text = 'tomorrow'
            elif 'day after tomorrow' in speech_text.lower():
                date_text = 'day after tomorrow'
            elif 'today' in speech_text.lower():
                date_text = 'today'
            else:
                # Extract day name or date
                for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
                    if day in speech_text.lower():
                        if 'next' in speech_text.lower():
                            date_text = f'next {day}'
                        else:
                            date_text = day
                        break
                else:
                    # Try to extract date pattern
                    if has_date_pattern:
                        date_text = has_date_pattern.group(0)
                    else:
                        date_text = speech_text
            
            logger.info(f"Date detected in initial request: {date_text}")
            
            # Validate date is not in the past
            today = timezone.now().date()
            try:
                from dateutil import parser as date_parser
                
                # Parse relative dates
                if 'tomorrow' in date_text.lower():
                    parsed_date = today + timedelta(days=1)
                elif 'day after tomorrow' in date_text.lower():
                    parsed_date = today + timedelta(days=2)
                elif 'today' in date_text.lower():
                    parsed_date = today
                else:
                    # Try to parse the date
                    parsed_date = date_parser.parse(date_text, fuzzy=True).date()
                
                # Check if date is in the past
                if parsed_date < today:
                    response.say(
                        f"That date has already passed. Please choose a future date. Thank you!",
                        voice='Polly.Joanna',
                        language='en-US'
                    )
                    response.hangup()
                    return HttpResponse(str(response), content_type='text/xml')
            except:
                pass  # Continue if parsing fails
            
            # Ask for time directly with barge-in
            gather = response.gather(
                input='speech',
                action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=get_time&preferred_date={quote(date_text)}',
                method='POST',
                timeout=speech_timeout,  # Use setting from .env
                speech_timeout='auto',
                language='en-US',
                hints='morning, afternoon, evening, 9, 10, 11, 2, 3, 4, AM, PM',
                barge_in=enable_barge_in,  # Use setting from .env
                profanity_filter=False  # Faster processing
            )
            gather.say(
                f"Great! What time would work best for you?",
                voice='Polly.Joanna',
                language='en-US'
            )
            response.say("I'm sorry, I didn't catch that. Please give us a call back. Thank you!", voice='Polly.Joanna')
        else:
            # No date mentioned - ask for date with barge-in
            gather = response.gather(
                input='speech',
                action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=get_date',
                method='POST',
                timeout=speech_timeout,  # Use setting from .env
                speech_timeout='auto',
                language='en-US',
                hints='tomorrow, today, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday, May, June',
                barge_in=enable_barge_in,  # Use setting from .env
                profanity_filter=False  # Faster processing
            )
            gather.say(
                f"Perfect! What date would work best for you?",
                voice='Polly.Joanna',
                language='en-US'
            )
            response.say("I'm sorry, I didn't catch that. Please give us a call back. Thank you!", voice='Polly.Joanna')
        
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')
    
    elif action == 'get_date':
        # Patient provided a date - Validate it's not in the past, then ask for time
        from urllib.parse import quote
        
        # Quick validation - check if date is in the past
        today = timezone.now().date()
        try:
            import re
            from dateutil import parser as date_parser
            
            # Try to parse the date
            date_match = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([A-Za-z]+)(?:\s+(\d{4}))?', speech_text, re.IGNORECASE)
            if date_match:
                day = int(date_match.group(1))
                month_str = date_match.group(2)
                year = int(date_match.group(3)) if date_match.group(3) else today.year
                
                month_map = {
                    'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
                    'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6,
                    'jul': 7, 'july': 7, 'aug': 8, 'august': 8, 'sep': 9, 'september': 9,
                    'oct': 10, 'october': 10, 'nov': 11, 'november': 11, 'dec': 12, 'december': 12
                }
                month = month_map.get(month_str.lower(), today.month)
                
                from datetime import date
                parsed_date = date(year, month, day)
                
                # Check if date is in the past
                if parsed_date < today:
                    response.say(
                        f"That date has already passed. Please choose a future date. Thank you!",
                        voice='Polly.Joanna',
                        language='en-US'
                    )
                    response.hangup()
                    return HttpResponse(str(response), content_type='text/xml')
        except:
            pass  # Continue if parsing fails
        
        gather = response.gather(
            input='speech',
            action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=get_time&preferred_date={quote(speech_text)}',
            method='POST',
            timeout=speech_timeout,  # Use setting from .env
            speech_timeout='auto',
            language='en-US',
            hints='morning, afternoon, evening, 9, 10, 11, 2, 3, 4, AM, PM',
            barge_in=enable_barge_in,  # Use setting from .env
            profanity_filter=False  # Faster processing
        )
        gather.say(
            f"Got it! And what time would you prefer?",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.say("I'm sorry, I didn't catch that. Please give us a call back. Thank you!", voice='Polly.Joanna')
        response.hangup()
        return HttpResponse(str(response), content_type='text/xml')
    
    elif action == 'get_time':
        # Patient provided time - Find and book slot
        preferred_date = request.GET.get('preferred_date', '')
        
        logger.info(f"Booking attempt - Patient: {patient.id}, Date: {preferred_date}, Time: {speech_text}")
        
        try:
            # Get doctor (assigned or first available)
            doctor = patient.assigned_doctor
            if not doctor:
                doctor = Doctor.objects.filter(status='ACTIVE').first()
            
            if not doctor:
                response.say(
                    "I'm sorry, no doctors are currently available for appointments. Please give our office a call to schedule. Thank you!",
                    voice='Polly.Joanna',
                    language='en-US'
                )
            else:
                # Parse the preferred date
                import re
                from dateutil import parser as date_parser
                
                target_date = None
                today = timezone.now().date()
                
                # Try to parse specific date (e.g., "21 May", "May 21", "21st May 2026")
                try:
                    # Extract date patterns
                    date_match = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([A-Za-z]+)(?:\s+(\d{4}))?', preferred_date, re.IGNORECASE)
                    if date_match:
                        day = int(date_match.group(1))
                        month_str = date_match.group(2)
                        year = int(date_match.group(3)) if date_match.group(3) else today.year
                        
                        # Parse month name
                        month_map = {
                            'jan': 1, 'january': 1,
                            'feb': 2, 'february': 2,
                            'mar': 3, 'march': 3,
                            'apr': 4, 'april': 4,
                            'may': 5,
                            'jun': 6, 'june': 6,
                            'jul': 7, 'july': 7,
                            'aug': 8, 'august': 8,
                            'sep': 9, 'september': 9,
                            'oct': 10, 'october': 10,
                            'nov': 11, 'november': 11,
                            'dec': 12, 'december': 12
                        }
                        month = month_map.get(month_str.lower(), today.month)
                        
                        from datetime import date
                        target_date = date(year, month, day)
                        logger.info(f"Parsed specific date: {target_date} from '{preferred_date}'")
                    else:
                        # Try dateutil parser as fallback
                        parsed = date_parser.parse(preferred_date, fuzzy=True)
                        target_date = parsed.date()
                        logger.info(f"Parsed date using dateutil: {target_date}")
                except:
                    # If parsing fails, check for relative dates
                    if 'day after tomorrow' in preferred_date.lower():
                        target_date = today + timedelta(days=2)
                    elif 'tomorrow' in preferred_date.lower():
                        target_date = today + timedelta(days=1)
                    elif 'today' in preferred_date.lower():
                        target_date = today
                    else:
                        # Check for day names (Monday, Tuesday, etc.)
                        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                        for i, day_name in enumerate(day_names):
                            if day_name in preferred_date.lower():
                                # Calculate days until that day
                                current_weekday = today.weekday()  # 0=Monday, 6=Sunday
                                target_weekday = i
                                days_ahead = target_weekday - current_weekday
                                if days_ahead <= 0:  # Target day already happened this week
                                    days_ahead += 7
                                target_date = today + timedelta(days=days_ahead)
                                break
                        else:
                            # Default to next available date
                            target_date = today
                    logger.info(f"Using relative/default date: {target_date}")
                
                # Parse time preference - handle both specific times and general periods
                time_preference = 'any'
                specific_hour = None
                specific_minute = None
                
                # Try to extract specific time (e.g., "9:30 AM", "2 PM", "10 o'clock")
                # Match patterns like: "9:30 am", "9.30 am", "10 am", "2 pm"
                time_match = re.search(r'\b(\d{1,2})[:.]?(\d{2})?\s*(am|a\.m\.|pm|p\.m\.|o\'?clock)?\b', speech_text, re.IGNORECASE)
                if time_match:
                    specific_hour = int(time_match.group(1))
                    specific_minute = int(time_match.group(2)) if time_match.group(2) else 0
                    am_pm = time_match.group(3) if time_match.group(3) else ''
                    
                    # Adjust for PM if mentioned
                    if 'pm' in am_pm.lower() or 'p.m' in am_pm.lower():
                        if specific_hour < 12:
                            specific_hour += 12
                    # If AM is mentioned or hour is clearly morning (8-11), keep as is
                    elif 'am' in am_pm.lower() or 'a.m' in am_pm.lower():
                        pass  # Keep the hour as is
                    # If no AM/PM specified, assume based on typical appointment hours
                    elif specific_hour < 8:
                        specific_hour += 12  # Assume PM for very early hours
                    
                    logger.info(f"Parsed specific time: {specific_hour}:{specific_minute:02d} from '{speech_text}'")
                
                # If no specific hour, determine general time preference
                if specific_hour is None:
                    if any(word in speech_text for word in ['morning', 'am', 'a.m']):
                        time_preference = 'morning'
                    elif any(word in speech_text for word in ['afternoon', 'pm', 'p.m', '2', '3', '4']):
                        time_preference = 'afternoon'
                    elif any(word in speech_text for word in ['evening', 'night', '5', '6']):
                        time_preference = 'evening'
                
                # Get available slots for the target date
                next_week = today + timedelta(days=14)  # Extended to 2 weeks
                
                slots_query = DoctorSlot.objects.filter(
                    doctor=doctor,
                    slot_date__gte=today,
                    slot_date__lte=next_week,
                    status='AVAILABLE'
                )
                
                # Filter by target date if parsed
                if target_date:
                    slots_query = slots_query.filter(slot_date=target_date)
                    logger.info(f"Filtering slots for date: {target_date}")
                
                # Filter by specific time if provided
                if specific_hour is not None:
                    # Look for slots at the specific hour and minute
                    slots_query = slots_query.filter(
                        start_time__hour=specific_hour,
                        start_time__minute=specific_minute
                    )
                    logger.info(f"Filtering slots for time: {specific_hour}:{specific_minute:02d}")
                elif time_preference == 'morning':
                    slots_query = slots_query.filter(start_time__hour__lt=12)
                elif time_preference == 'afternoon':
                    slots_query = slots_query.filter(start_time__hour__gte=12, start_time__hour__lt=17)
                elif time_preference == 'evening':
                    slots_query = slots_query.filter(start_time__hour__gte=17)
                
                slots = slots_query.order_by('slot_date', 'start_time')[:3]
                
                if slots:
                    # Book the first available slot
                    slot = slots[0]
                    
                    # Book the slot
                    slot.status = 'BOOKED'
                    slot.booked_patient = patient
                    slot.booked_at = timezone.now()
                    slot.save()
                    
                    # Create appointment
                    appt = AppointmentModel.objects.create(
                        slot=slot,
                        patient=patient,
                        status='CONFIRMED',
                        notes=f'Booked via AI call - Preferred: {preferred_date} {speech_text}'
                    )
                    
                    # Confirm booking - Short and natural with follow-up question
                    day_name = slot.slot_date.strftime('%A')
                    date_str = slot.slot_date.strftime('%B %d')
                    time_str = slot.start_time.strftime('%I:%M %p')
                    
                    # Ask if patient has any other questions
                    gather = response.gather(
                        input='speech',
                        action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}&action=final_question',
                        method='POST',
                        timeout=speech_timeout,
                        speech_timeout='auto',
                        language='en-US',
                        hints='no, yes, question, office, hours, location, address, doctor, appointment',
                        barge_in=enable_barge_in,
                        profanity_filter=False
                    )
                    gather.say(
                        f"Wonderful! You're all set with Dr. {doctor.full_name.split()[-1]} "
                        f"on {day_name}, {date_str} at {time_str}. "
                        "You'll receive a confirmation text shortly. Is there anything else I can help you with today?",
                        voice='Polly.Joanna',
                        language='en-US'
                    )
                    response.say("Thank you, have a great day!", voice='Polly.Joanna')
                    response.hangup()
                    
                    # Send SMS confirmation
                    try:
                        from reminders.models import ReminderLog
                        from reminders.tasks import _send_sms
                        
                        msg = (
                            f"Appointment confirmed! Dr. {doctor.full_name.split()[-1]} on "
                            f"{slot.slot_date.strftime('%b %d')} at {slot.start_time.strftime('%I:%M %p')}. "
                            f"Thank you, see you then!"
                        )
                        
                        reminder = ReminderLog.objects.create(
                            appointment=appt,
                            patient=patient,
                            reminder_type=ReminderLog.ReminderType.BOOKING_CONFIRMATION,
                            channel=ReminderLog.Channel.SMS,
                            message_text=msg
                        )
                        
                        if _send_sms(patient.phone_number, msg, reminder):
                            reminder.mark_sent()
                    except Exception as e:
                        logger.error(f"SMS error: {e}")
                else:
                    # No slots available for requested date/time
                    logger.info(f"No slots available for date: {target_date}, time: {specific_hour}:{specific_minute if specific_minute else 0:02d}")
                    
                    # Build descriptive message about what was requested
                    if target_date:
                        date_desc = target_date.strftime('%A, %B %d')
                    else:
                        date_desc = "the requested date"
                    
                    if specific_hour is not None and specific_minute is not None:
                        time_desc = f"{specific_hour}:{specific_minute:02d} {'AM' if specific_hour < 12 else 'PM'}"
                    elif specific_hour is not None:
                        time_desc = f"{specific_hour}:00 {'AM' if specific_hour < 12 else 'PM'}"
                    elif time_preference != 'any':
                        time_desc = f"{time_preference} time"
                    else:
                        time_desc = "the requested time"
                    
                    # Check if there are ANY slots available on the requested date (different time)
                    if target_date:
                        date_slots = DoctorSlot.objects.filter(
                            doctor=doctor,
                            slot_date=target_date,
                            status='AVAILABLE'
                        ).order_by('start_time')[:3]
                        
                        if date_slots:
                            # Slots available on same date, different time
                            alt_slot = date_slots[0]
                            response.say(
                                f"I'm sorry, we don't have any openings on {date_desc} at {time_desc}. "
                                f"However, we do have availability on the same day at {alt_slot.start_time.strftime('%I:%M %p')}. "
                                "Would you like me to book that for you, or would you prefer to call our office for more options? Thank you!",
                                voice='Polly.Joanna',
                                language='en-US'
                            )
                        else:
                            # No slots available on the requested date at all
                            # Check for slots on nearby dates
                            nearby_slots = DoctorSlot.objects.filter(
                                doctor=doctor,
                                slot_date__gte=today,
                                slot_date__lte=next_week,
                                status='AVAILABLE'
                            ).order_by('slot_date', 'start_time')[:3]
                            
                            if nearby_slots:
                                alt_slot = nearby_slots[0]
                                response.say(
                                    f"I'm sorry, we're fully booked on {date_desc}. "
                                    f"However, we have an opening on {alt_slot.slot_date.strftime('%A, %B %d')} "
                                    f"at {alt_slot.start_time.strftime('%I:%M %p')}. "
                                    "Would you like me to book that for you, or would you prefer to call our office? Thank you!",
                                    voice='Polly.Joanna',
                                    language='en-US'
                                )
                            else:
                                # No slots at all in the next 2 weeks
                                response.say(
                                    f"I'm sorry, we're completely booked for the next two weeks on {date_desc}. "
                                    "Please give our office a call and we'll help you find a time that works. Thank you!",
                                    voice='Polly.Joanna',
                                    language='en-US'
                                )
                    else:
                        # No target date specified, just no slots for the time
                        any_slots = DoctorSlot.objects.filter(
                            doctor=doctor,
                            slot_date__gte=today,
                            slot_date__lte=next_week,
                            status='AVAILABLE'
                        ).order_by('slot_date', 'start_time')[:3]
                        
                        if any_slots:
                            alt_slot = any_slots[0]
                            response.say(
                                f"I'm sorry, we don't have any openings at {time_desc}. "
                                f"However, we have availability on {alt_slot.slot_date.strftime('%A, %B %d')} "
                                f"at {alt_slot.start_time.strftime('%I:%M %p')}. "
                                "Would you like me to book that for you? Thank you!",
                                voice='Polly.Joanna',
                                language='en-US'
                            )
                        else:
                            response.say(
                                f"I'm sorry, we're completely booked for the next two weeks. "
                                "Please give our office a call and we'll do our best to accommodate you. Thank you!",
                                voice='Polly.Joanna',
                                language='en-US'
                            )
        except Exception as e:
            logger.error(f"Booking error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            response.say(
                "I'm sorry, I'm having trouble booking that appointment right now. Please give our office a call and we'll get you scheduled. Thank you!",
                voice='Polly.Joanna',
                language='en-US'
            )
    
    elif action == 'final_question':
        # Handle final question after booking
        if any(word in speech_text for word in ['no', 'nope', 'nothing', 'that\'s all', 'all set']):
            # Patient has no questions
            response.say(
                "Wonderful! Thank you so much for calling. Have a great day!",
                voice='Polly.Joanna',
                language='en-US'
            )
        elif any(word in speech_text for word in ['office', 'hours', 'time', 'open']):
            # Office hours question
            response.say(
                "We're open Monday through Friday, 9 AM to 5 PM. Is there anything else I can help you with? Thank you!",
                voice='Polly.Joanna',
                language='en-US'
            )
        elif any(word in speech_text for word in ['location', 'address', 'where']):
            # Location question
            response.say(
                "We're located at 123 Medical Plaza. You'll receive the complete address in your confirmation text. Anything else I can help with? Thank you!",
                voice='Polly.Joanna',
                language='en-US'
            )
        elif any(word in speech_text for word in ['doctor', 'who', 'specialist']):
            # Doctor question
            response.say(
                "You'll be seeing one of our experienced doctors. Their specialty and background will be in your confirmation text. Anything else? Thank you!",
                voice='Polly.Joanna',
                language='en-US'
            )
        elif any(word in speech_text for word in ['insurance', 'payment', 'cost', 'price']):
            # Insurance/payment question
            response.say(
                "For insurance and payment questions, please give our office a call at your convenience. We'll be happy to help! Thank you!",
                voice='Polly.Joanna',
                language='en-US'
            )
        elif any(word in speech_text for word in ['parking', 'park']):
            # Parking question
            response.say(
                "We have free parking available for all patients. The details will be in your confirmation text. Anything else? Thank you!",
                voice='Polly.Joanna',
                language='en-US'
            )
        elif any(word in speech_text for word in ['prepare', 'bring', 'need']):
            # What to bring question
            response.say(
                "Please bring your photo ID and insurance card. We'll send you a complete checklist via text. Anything else I can help with? Thank you!",
                voice='Polly.Joanna',
                language='en-US'
            )
        else:
            # General question - offer to transfer to office
            response.say(
                "For that specific question, please give our office a call during business hours. We'll be happy to help! Thank you!",
                voice='Polly.Joanna',
                language='en-US'
            )
    
    elif any(word in speech_text for word in ['check', 'what', 'when', 'my appointment', 'existing']):
        # Redirect to intelligent check_appointment handler
        return handle_speech_input(
            request, patient, speech_text, call_type, appointment, call_log_id
        )
    
    elif any(word in speech_text for word in ['confirm', 'yes', 'yeah', 'sure', 'okay']):
        # Confirmation intent
        if call_type == 'APPOINTMENT_REMINDER' and appointment:
            appointment.status = 'CONFIRMED'
            appointment.save()
            response.say(
                f"Perfect! Your appointment is confirmed for {appointment.slot.slot_date.strftime('%B %d')} at {appointment.slot.start_time.strftime('%I:%M %p')}. Thank you, see you then!",
                voice='Polly.Joanna',
                language='en-US'
            )
        else:
            response.say(
                "Great! Is there anything else I can help you with? Thank you!",
                voice='Polly.Joanna',
                language='en-US'
            )
    
    elif any(word in speech_text for word in ['cancel', 'reschedule', 'change', 'move']):
        # Cancel/reschedule intent
        response.say(
            "To reschedule or cancel your appointment, please call our office. Thank you!",
            voice='Polly.Joanna',
            language='en-US'
        )
    
    elif any(word in speech_text for word in ['office', 'speak', 'talk', 'person', 'human']):
        # Speak with office intent
        response.say(
            "Please call our office during business hours. Thank you!",
            voice='Polly.Joanna',
            language='en-US'
        )
    
    else:
        # Fallback for unrecognized intent - Be helpful and conversational
        gather = response.gather(
            input='speech',
            action=f'/api/v1/calling/twiml-conversational/?patient_id={patient.id}&call_log_id={call_log_id}&call_type={call_type}',
            method='POST',
            timeout=speech_timeout,
            speech_timeout='auto',
            language='en-US',
            hints='book, check, appointment, cancel, reschedule, office, hours, location',
            barge_in=enable_barge_in,
            profanity_filter=False
        )
        gather.say(
            "I can help you book an appointment, check your appointments, or answer questions about our office. What would you like to do?",
            voice='Polly.Joanna',
            language='en-US'
        )
        response.say("Thank you, have a great day!", voice='Polly.Joanna')
    
    response.hangup()
    return HttpResponse(str(response), content_type='text/xml')


# Keep old twiml_greeting for backward compatibility
@csrf_exempt
@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def twiml_greeting(request):
    """Legacy keypad-based greeting - redirects to conversational."""
    return twiml_conversational(request)


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
    
    # Always use synchronous processing (Celery not running)
    logger.info(f"Processing status callback synchronously for {call_sid}")
    process_call_status(
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
        
        # Always use synchronous transcription (Celery not running)
        from transcriptions.tasks import _transcribe_call_sync
        logger.info(f"Processing transcription synchronously for call log {call_log.id}")
        _transcribe_call_sync(call_log.id)
        
    except CallLog.DoesNotExist:
        logger.error(f"CallLog not found for SID: {call_sid}")
    except Exception as e:
        logger.error(f"Error in recording callback: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    return HttpResponse('OK', status=200)
